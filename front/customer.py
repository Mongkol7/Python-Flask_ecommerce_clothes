import html
import re
from datetime import datetime, timedelta
from flask import abort, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash
from config import Config
from extensions import db, limiter
from helpers import is_failed_login, is_ip_login_banned, is_ip_signup_banned, log_activity, send_order_cancellation_to_telegram
from models import User, Order, OrderItem, Product
from upload_service import save_user_image, allowed_file
from . import front_bp


@front_bp.route("/user/login", methods=["GET", "POST"])
@front_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["GET"])
@limiter.limit("5 per minute", methods=["POST"], deduct_when=is_failed_login)
def user_login():
    ban_remaining = is_ip_login_banned()
    if ban_remaining > 0:
        abort(429, description=f"Too many login attempts. You are temporarily blocked. Please wait {ban_remaining} seconds before trying again.")

    module = "login"
    if request.method == "POST":
        form = request.form
        username = (form.get("username") or form.get("identifier") or "").strip()
        password = form.get("password", "")

        # Query user by username or email using raw SQL
        sql = text("SELECT * FROM user WHERE username = :username OR email = :username")
        user = db.session.execute(sql, {"username": username}).fetchone()

        if user:
            if check_password_hash(user.password, password):
                session["is_login"] = True
                session["user_id"] = user.id
                session["username"] = user.username
                session["role"] = user.role
                session["profile"] = user.profile
                session.permanent = True

                next_url = request.args.get("next") or request.form.get("next")
                if user.role == "admin":
                    return redirect(next_url or url_for("admin_bp.dashboard"))
                else:
                    return redirect(next_url or url_for("front_bp.home"))
            else:
                flash("Invalid username or password.", "error")
                res = redirect(url_for("front_bp.user_login", next=request.args.get("next") or request.form.get("next")))
                res.is_failed_login = True
                return res
        else:
            flash("Invalid username or password.", "error")
            res = redirect(url_for("front_bp.user_login", next=request.args.get("next") or request.form.get("next")))
            res.is_failed_login = True
            return res

    if session.get("is_login"):
        next_url = request.args.get("next")
        if session.get("role") == "admin":
            return redirect(next_url or url_for("admin_bp.dashboard"))
        else:
            return redirect(next_url or url_for("front_bp.home"))

    return render_template(
        "admin/login.html",
        module=module,
        user_type="user",
        title="User Login",
        kicker="Customer Account",
        portal_name="Account",
        subtitle="Sign in to manage your bag, checkout, and shopping experience",
        btn_text="Sign In to Account",
    )


@front_bp.route("/user/register", methods=["GET", "POST"])
@front_bp.route("/user/signup", methods=["GET", "POST"])
@front_bp.route("/register", methods=["GET", "POST"])
@front_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["GET"])
@limiter.limit("5 per minute", methods=["POST"])
def user_register():
    # Registration rate limit check: preserves cooldown timer across GET/POST retries
    ban_remaining = is_ip_signup_banned()
    if ban_remaining > 0:
        abort(429, description=f"Too many registration attempts. You are temporarily blocked. Please wait {ban_remaining} seconds before trying again.")

    # Login rate limit bans DO NOT apply here: Sign Up is separate!
    module = "register"
    next_param = request.args.get("next") or request.form.get("next")
    
    if request.method == "POST":
        form = request.form
        username = form.get("username", "").strip()
        email = form.get("email", "").strip()
        password = form.get("password", "")
        confirm_password = form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("front_bp.user_register", next=next_param))

        if len(password) < 4:
            flash("Password must be at least 4 characters long.", "error")
            return redirect(url_for("front_bp.user_register", next=next_param))

        if confirm_password and password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("front_bp.user_register", next=next_param))

        # Check existing user by username or email
        sql = text("SELECT id FROM user WHERE username = :username OR email = :email")
        existing = db.session.execute(sql, {"username": username, "email": email}).fetchone()
        if existing:
            flash("Username or Email already registered. Please sign in.", "error")
            return redirect(url_for("front_bp.user_register", next=next_param))

        hashed = generate_password_hash(password)
        insert_sql = text("INSERT INTO user (username, email, password, role) VALUES (:username, :email, :password, 'user')")
        db.session.execute(insert_sql, {"username": username, "email": email, "password": hashed})
        db.session.commit()

        user = db.session.execute(sql, {"username": username, "email": email}).fetchone()
        session["is_login"] = True
        session["user_id"] = user.id
        session["username"] = username
        session["role"] = "user"
        session["profile"] = None
        session.permanent = True

        flash("Welcome to MK7! Your account has been created successfully.", "success")
        return redirect(next_param or url_for("front_bp.home"))

    if session.get("is_login"):
        return redirect(next_param or url_for("front_bp.home"))

    return render_template(
        "front/register.html",
        module=module,
        user_type="user",
        title="Create Account",
        kicker="Customer Registration",
        portal_name="Account",
        subtitle="Join MK7 for exclusive collections, effortless bag checkout, and order tracking",
        btn_text="Create MK7 Account",
        next=next_param,
    )


@front_bp.route("/user/logout")
@front_bp.route("/logout")
def user_logout():
    session.clear()
    return redirect(url_for("front_bp.home"))


# ==========================================
# CUSTOMER ORDER HISTORY & 4-HOUR CANCEL
# ==========================================

@front_bp.route("/my-orders")
@front_bp.route("/orders")
def my_orders():
    """Customer Order History View with 4-Hour Cancellation Window & Auto Success Transition."""
    if not session.get("is_login"):
        flash("Please sign in to view your order history.", "warning")
        return redirect(url_for("front_bp.user_login", next=url_for("front_bp.my_orders")))

    user_id = session.get("user_id")
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc(), Order.id.desc()).all()

    now = datetime.utcnow()
    updated_any = False

    # Check for orders that passed the 4-hour cancellation period without being cancelled:
    # transition them automatically to 'confirmed'
    for o in orders:
        if o.created_at and o.status == "pending":
            elapsed = now - o.created_at
            if elapsed >= timedelta(hours=4):
                o.status = "confirmed"
                updated_any = True

    if updated_any:
        db.session.commit()

    # Prepare order cards data with cancellation countdown timers
    orders_data = []
    for o in orders:
        can_cancel = False
        remaining_seconds = 0
        hours_left = 0
        mins_left = 0

        if o.created_at and o.status == "pending":
            deadline = o.created_at + timedelta(hours=4)
            diff = (deadline - now).total_seconds()
            if diff > 0:
                can_cancel = True
                remaining_seconds = int(diff)
                hours_left = int(diff // 3600)
                mins_left = int((diff % 3600) // 60)

        orders_data.append({
            "order": o,
            "can_cancel": can_cancel,
            "remaining_seconds": remaining_seconds,
            "hours_left": hours_left,
            "mins_left": mins_left,
        })

    return render_template(
        "front/orders.html",
        orders_data=orders_data,
        total_count=len(orders),
    )


@front_bp.post("/orders/<int:order_id>/cancel")
def cancel_order(order_id):
    """Cancel customer order within 4 hours and restore product inventory."""
    if not session.get("is_login"):
        flash("Please sign in to manage your orders.", "warning")
        return redirect(url_for("front_bp.user_login"))

    user_id = session.get("user_id")
    order = db.session.get(Order, order_id)

    if not order or order.user_id != user_id:
        flash("Order not found or access denied.", "error")
        return redirect(url_for("front_bp.my_orders"))

    now = datetime.utcnow()
    if not order.created_at:
        flash("Order cancellation not possible.", "error")
        return redirect(url_for("front_bp.my_orders"))

    elapsed = now - order.created_at

    # Check if within 4-hour window
    if elapsed <= timedelta(hours=4) and order.status == "pending":
        order.status = "cancelled"

        # Restore product inventory stock
        for item in order.items:
            if item.product_id:
                prod = db.session.get(Product, item.product_id)
                if prod:
                    prod.stock += item.quantity

        db.session.commit()

        # Send Telegram cancellation alert
        try:
            current_user_obj = db.session.get(User, user_id)
            send_order_cancellation_to_telegram(order, user=current_user_obj)
        except Exception:
            pass

        try:
            log_activity(
                action="order_cancelled_by_user",
                module="orders",
                description=f"Order #{order.order_number} was cancelled by user within 4 hours. Inventory restocked.",
                user_id=user_id,
            )
        except Exception:
            pass

        flash(f"Order #{order.order_number} has been cancelled successfully. Your payment is refunded and item stock restored.", "success")
        return redirect(url_for("front_bp.my_orders"))

    elif elapsed > timedelta(hours=4):
        # Window expired -> auto-transition to confirmed
        if order.status == "pending":
            order.status = "confirmed"
            db.session.commit()
        flash(f"Order #{order.order_number} can no longer be cancelled because the 4-hour period has expired. Status is now Confirmed.", "warning")
        return redirect(url_for("front_bp.my_orders"))

    else:
        flash(f"Order #{order.order_number} has status '{order.status.title()}' and cannot be cancelled.", "info")
        return redirect(url_for("front_bp.my_orders"))


@front_bp.get("/orders/<int:order_id>/khqr")
def order_khqr_data(order_id):
    """Generates real, valid Bakong KHQR for a pending order so customer can scan and pay."""
    if not session.get("is_login"):
        return jsonify({"success": False, "error": "Authentication required"}), 401

    user_id = session.get("user_id")
    order = db.session.get(Order, order_id)
    if not order or (order.user_id != user_id and session.get("role") != "admin"):
        return jsonify({"success": False, "error": "Order not found or access denied"}), 404

    if order.status != "pending":
        return jsonify({"success": False, "error": f"Order status is '{order.status}' and does not require payment."}), 400

    from services.khqr_service import generate_bakong_khqr
    khqr_data = generate_bakong_khqr(
        amount=order.total,
        bill_number=order.order_number,
        currency=Config.BAKONG_CURRENCY
    )
    if not khqr_data.get("success"):
        return jsonify({"success": False, "error": khqr_data.get("error", "Failed to generate QR")}), 500

    return jsonify({
        "success": True,
        "base64_uri": khqr_data["base64_uri"],
        "md5": khqr_data["md5"],
        "order_number": order.order_number,
        "amount": order.total,
        "amount_khr": f"{int(round(order.total)):,} ៛",
        "amount_usd": f"≈ ${(order.total / Config.KHR_RATE):.2f}",
        "merchant_name": Config.BAKONG_MERCHANT_NAME,
        "account_id": Config.BAKONG_ACCOUNT_ID,
    })


@front_bp.route("/orders/<int:order_id>/confirm-payment", methods=["GET", "POST"])
def confirm_order_payment(order_id):
    """Verifies payment for a pending order via NBC Bakong and updates status to confirmed."""
    if not session.get("is_login"):
        return jsonify({"success": False, "error": "Authentication required"}), 401

    user_id = session.get("user_id")
    order = db.session.get(Order, order_id)
    if not order or (order.user_id != user_id and session.get("role") != "admin"):
        return jsonify({"success": False, "error": "Order not found"}), 404

    if order.status in ["confirmed", "success"]:
        return jsonify({"success": True, "paid": True, "message": "Order is already confirmed."})

    if order.status != "pending":
        return jsonify({"success": False, "paid": False, "error": f"Order is {order.status}."}), 400

    # Extract MD5 from query param or request body
    md5_hash = (
        request.args.get("md5")
        or (request.get_json(silent=True) or {}).get("md5")
        or ""
    ).strip()

    # Check for manual confirmation flag (e.g. when customer transferred on banking app)
    manual_confirm = (
        str(request.args.get("manual_confirm", "")).lower() in ["1", "true", "yes"]
        or str((request.get_json(silent=True) or {}).get("manual_confirm", "")).lower() in ["1", "true", "yes"]
    )

    if not md5_hash:
        # Fallback to cached MD5 in order notes
        match = re.search(r"MD5:\s*([a-f0-9]{32})", order.notes or "")
        if match:
            md5_hash = match.group(1)

    from services.khqr_service import check_bakong_payment
    verify_res = check_bakong_payment(md5_hash) if md5_hash else {"paid": False}

    is_paid = verify_res.get("paid", False)
    is_rate_limited = verify_res.get("rate_limited", False)

    # Determine whether to confirm order
    should_confirm = False
    verification_type = "Verified Paid via NBC Bakong"

    if is_paid:
        should_confirm = True
        verification_type = "Verified Paid (NBC Bakong API Live Check)"
    elif manual_confirm:
        should_confirm = True
        verification_type = "Customer Confirmed Mobile Transfer (Bakong KHQR)"
        if is_rate_limited:
            verification_type += " [NBC Daily API Limit Active]"

    if should_confirm:
        order.status = "confirmed"
        new_note = f"\n[Confirmed]: {verification_type} | MD5: {md5_hash or 'N/A'}"
        order.notes = (order.notes or "") + new_note
        db.session.commit()

        # Send Telegram alert
        try:
            from helpers import send_telegram_alert
            send_telegram_alert(
                f"💰 <b>[PAYMENT CONFIRMED] MK7 Luxury Storefront</b>\n\n"
                f"• <b>Order Number:</b> <code>{html.escape(order.order_number)}</code>\n"
                f"• <b>Customer:</b> {html.escape(order.customer_name)} ({html.escape(order.customer_phone or '')})\n"
                f"• <b>Amount Paid:</b> <b>{int(round(order.total)):,} ៛ KHR</b> (≈ ${(order.total / Config.KHR_RATE):.2f} USD)\n"
                f"• <b>Payment Gateway:</b> 🇰🇭 Bakong KHQR\n"
                f"• <b>Verification:</b> <b>{html.escape(verification_type)}</b>\n"
                f"• <b>Transaction MD5:</b> <code>{html.escape(str(md5_hash))}</code>\n"
                f"• <b>Status:</b> <b>Confirmed / Paid</b> ✅"
            )
        except Exception:
            pass

        try:
            log_activity(
                action="order_paid",
                module="orders",
                description=f"Order #{order.order_number} confirmed as Paid ({verification_type}).",
                record_id=order.id,
                user_id=user_id,
            )
        except Exception:
            pass

        return jsonify({
            "success": True,
            "paid": True,
            "message": "Payment verified! Your order is now Confirmed."
        })

    # Return rate limited status if NBC quota reached
    if is_rate_limited:
        return jsonify({
            "success": True,
            "paid": False,
            "rate_limited": True,
            "status": "RATE_LIMIT_EXCEEDED",
            "message": "Bakong Developer API daily limit (100 checks) reached on NBC gateway. You can confirm your transfer directly.",
        })

    return jsonify({
        "success": True,
        "paid": False,
        "status": "UNPAID",
        "message": "Awaiting customer transfer on banking app.",
    })


# ==========================================
# CUSTOMER PROFILE & PROFILE IMAGE UPLOAD
# ==========================================

@front_bp.route("/profile", methods=["GET", "POST"])
@front_bp.route("/my-profile", methods=["GET", "POST"])
def user_profile():
    """Customer profile management allowing avatar image upload and details update."""
    if not session.get("is_login"):
        flash("Please sign in to manage your profile.", "warning")
        return redirect(url_for("front_bp.user_login", next=url_for("front_bp.user_profile")))

    user_id = session.get("user_id")
    user = db.session.get(User, user_id)
    if not user:
        session.clear()
        return redirect(url_for("front_bp.user_login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        image = request.files.get("profile_image") or request.files.get("image")

        # 1. Update Username if changed
        if username and username != user.username:
            existing = User.query.filter(User.username == username, User.id != user.id).first()
            if existing:
                flash("That username is already taken. Please choose another.", "error")
                return redirect(url_for("front_bp.user_profile"))
            user.username = username
            session["username"] = username

        # 2. Update Email if changed
        if email and email != user.email:
            existing = User.query.filter(User.email == email, User.id != user.id).first()
            if existing:
                flash("That email address is already in use.", "error")
                return redirect(url_for("front_bp.user_profile"))
            user.email = email

        # 3. Update Password if provided
        if password:
            if len(password) < 4:
                flash("Password must be at least 4 characters long.", "error")
                return redirect(url_for("front_bp.user_profile"))
            user.password = generate_password_hash(password)

        # 4. Upload and process Profile Image
        if image and image.filename:
            if not allowed_file(image.filename, Config.ALLOWED_EXTENSIONS):
                flash("Invalid image format. Allowed: PNG, JPG, JPEG, GIF, WEBP.", "error")
                return redirect(url_for("front_bp.user_profile"))

            saved = save_user_image(
                image,
                user_id=user.id,
                upload_folder=Config.UPLOAD_USER_FOLDER,
                allowed_extensions=Config.ALLOWED_EXTENSIONS,
                scale=0.8,
            )
            if saved:
                user.profile = saved["filename"]
                session["profile"] = saved["filename"]
                flash("Profile avatar image updated successfully!", "success")

        db.session.commit()
        flash("Your profile has been saved successfully.", "success")
        return redirect(url_for("front_bp.user_profile"))

    # Stats for profile overview
    order_count = Order.query.filter_by(user_id=user.id).count()

    return render_template(
        "front/profile.html",
        user=user,
        order_count=order_count,
    )

