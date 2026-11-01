import re
from flask import flash, jsonify, make_response, redirect, render_template, request, session, url_for
from config import Config
from extensions import db, limiter
from models.order import Order, OrderItem
from models.product import Product
from models.users import User
from product import get_cart_items
from helpers import load_cart, send_order_to_telegram, log_activity
from services.khqr_service import generate_bakong_khqr, check_bakong_payment
from . import front_bp


@front_bp.route("/checkout")
def checkout():
    """Renders the checkout page with dynamically generated Bakong KHQR for the cart total."""
    if not session.get("is_login"):
        flash("Please sign in or create an account to proceed to checkout.", "warning")
        return redirect(url_for("front_bp.user_login", next=url_for("front_bp.checkout")))

    cart_items = get_cart_items(load_cart())
    if not cart_items:
        return redirect(url_for("front_bp.cart"))

    # Security: strictly verify product existence & calculate total from DB
    verified_items = []
    total = 0.0
    for item in cart_items:
        prod = db.session.get(Product, item["id"])
        if prod:
            clean_item = dict(item)
            clean_item["price"] = prod.price
            clean_item["subtotal"] = prod.price * item["qty"]
            clean_item["title"] = prod.title
            clean_item["image"] = prod.image
            total += clean_item["subtotal"]
            verified_items.append(clean_item)

    if not verified_items or total <= 0:
        return redirect(url_for("front_bp.cart"))

    user = None
    if session.get("user_id"):
        user = db.session.get(User, session.get("user_id"))

    # Generate live Bakong KHQR (National Bank of Cambodia)
    bill_number = Order.generate_order_number()
    khqr_data = generate_bakong_khqr(amount=total, bill_number=bill_number, currency=Config.BAKONG_CURRENCY)

    return render_template(
        "front/checkout.html",
        cart_items=verified_items,
        subtotal=total,
        total=total,
        user=user,
        khqr=khqr_data,
        bill_number=bill_number,
    )


@front_bp.post("/payment")
@limiter.limit("5 per minute", methods=["POST"])
def payment():
    """
    Handles payment submission.
    Configured strictly for real Bakong KHQR payments with anti-tampering verification.
    """
    if not session.get("is_login"):
        flash("Please sign in or create an account to place an order.", "warning")
        return redirect(url_for("front_bp.user_login", next=url_for("front_bp.checkout")))

    cart_data = load_cart()
    cart_items = get_cart_items(cart_data)

    if not cart_items:
        return redirect(url_for("front_bp.cart"))

    # 1. Server-side anti-tampering: Re-fetch and re-calculate prices & stock strictly from DB
    verified_items = []
    server_total = 0.0
    for item in cart_items:
        pid = item.get("id")
        qty = int(item.get("qty", 1))
        if qty <= 0:
            continue
        prod = db.session.get(Product, pid)
        if not prod:
            continue

        # Prevent overselling: check inventory stock
        if prod.stock < qty:
            flash(f"Insufficient stock for '{prod.title}'. Only {prod.stock} unit(s) remaining.", "error")
            return redirect(url_for("front_bp.cart"))

        item_subtotal = round(prod.price * qty, 2)
        server_total += item_subtotal
        verified_items.append({
            "id": prod.id,
            "title": prod.title,
            "price": prod.price,
            "image": prod.image,
            "category": getattr(prod, "category_slug", "Fashion"),
            "qty": qty,
            "subtotal": item_subtotal,
        })

    if not verified_items or server_total <= 0:
        flash("Unable to process order. Please verify items in your bag.", "error")
        return redirect(url_for("front_bp.cart"))

    # 2. Strict Input Validation & Sanitization (Defense against prompt/SQL injection)
    form = request.form
    full_name = form.get("full_name", "").strip()[:100]
    phone = form.get("phone", "").strip()[:30]
    email = form.get("email", "").strip()[:100]
    address = form.get("address", "").strip()[:255]
    city = form.get("city", "").strip()[:80]
    zip_code = form.get("zip_code", "").strip()[:20]
    note = form.get("note", "").strip()[:500]

    # Validate essential shipping fields
    if not full_name or not email or not phone or not address:
        flash("All shipping details (Name, Phone, Email, Address) are required.", "error")
        return redirect(url_for("front_bp.checkout"))

    # Simple email pattern check
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("front_bp.checkout"))

    # Enforce Real Payment Gateway Only (Bakong KHQR)
    submitted_method = form.get("payment_method", "").strip().lower()
    if submitted_method not in ["bakong_khqr", "qr_payment"]:
        flash("Only verified Bakong KHQR payments are accepted on this store.", "error")
        return redirect(url_for("front_bp.checkout"))
    payment_method = "bakong_khqr"

    bill_number = form.get("bill_number", "").strip() or Order.generate_order_number()
    khqr_md5 = form.get("khqr_md5", "").strip()
    khqr_string = form.get("khqr_string", "").strip()

    # 3. Verify Payment Status via NBC Bakong API
    payment_status_text = "Pending Customer Transfer"
    initial_order_status = "pending"
    if khqr_md5:
        verify_res = check_bakong_payment(khqr_md5)
        # STRICT RULE: ONLY set to confirmed if payment was actually verified as PAID
        if verify_res.get("paid"):
            initial_order_status = "confirmed"
            payment_status_text = "Verified Paid (Bakong KHQR)"
        else:
            initial_order_status = "pending"
            payment_status_text = "Pending Customer Transfer"

    # 4. Create and persist customer Order in Database
    user_id = session.get("user_id")
    order_notes = f"Payment Gateway: Bakong KHQR (NBC) | Bill: {bill_number}"
    if khqr_md5:
        order_notes += f" | MD5: {khqr_md5}"
    if note:
        order_notes += f"\nCustomer Note: {note}"

    db_order = Order(
        order_number=bill_number,
        user_id=user_id,
        customer_name=full_name or (session.get("username") or "Valued Customer"),
        customer_email=email,
        customer_phone=phone,
        shipping_address=address,
        city=city,
        zip_code=zip_code,
        payment_method=payment_method,
        subtotal=server_total,
        total=server_total,
        status=initial_order_status,
        notes=order_notes,
    )
    db.session.add(db_order)

    # 5. Add OrderItems & Deduct Product Stock in Real Time
    for item in verified_items:
        order_item = OrderItem(
            order=db_order,
            product_id=item["id"],
            product_title=item["title"],
            product_price=item["price"],
            product_image=item["image"],
            quantity=item["qty"],
            subtotal=item["subtotal"],
        )
        db.session.add(order_item)

        # Deduct inventory stock
        prod = db.session.get(Product, item["id"])
        if prod:
            prod.stock = max(0, prod.stock - item["qty"])

    db.session.commit()

    # 6. Log order placement in ActivityLog
    try:
        log_activity(
            action="order_placed",
            module="orders",
            description=f"Order #{db_order.order_number} placed via Bakong KHQR by {db_order.customer_name} (${db_order.total:.2f}). Inventory deducted.",
            record_id=db_order.id,
            user_id=user_id,
        )
    except Exception:
        pass

    # 7. Live Telegram Notification for Real-Time Alertation
    order_info = {
        "order_number": bill_number,
        "bill_number": bill_number,
        "khqr_md5": khqr_md5,
        "payment_status": payment_status_text,
        "shipping": {
            "full_name": full_name,
            "phone": phone,
            "email": email,
            "address": address,
            "city": city,
            "zip_code": zip_code,
            "note": note,
        },
        "payment_method": payment_method,
        "items": verified_items,
        "subtotal": server_total,
        "total": server_total,
    }
    telegram_sent, telegram_error = send_order_to_telegram(order_info)

    response = make_response(
        render_template(
            "front/checkout.html",
            cart_items=verified_items,
            subtotal=server_total,
            total=server_total,
            checkout_success=True,
            order=db_order,
            order_info=order_info,
            telegram_sent=telegram_sent,
            telegram_error=telegram_error,
        )
    )
    # Clear the cart cookie upon successful checkout
    response.delete_cookie(Config.CART_COOKIE_NAME)
    return response


@front_bp.get("/api/payment/check/<md5_hash>")
def api_check_payment_status(md5_hash):
    """Real-time payment check endpoint for frontend AJAX status polling."""
    if not md5_hash:
        return jsonify({"success": False, "status": "INVALID_HASH"}), 400

    clean_md5 = md5_hash.strip()[:64]
    result = check_bakong_payment(clean_md5)
    return jsonify(result)

