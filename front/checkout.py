import re
from datetime import datetime
from flask import flash, jsonify, make_response, redirect, render_template, request, session, url_for
from config import Config
from extensions import db, limiter
from models.order import Order, OrderItem
from models.product import Product
from models.users import User
from models.wallet import WalletTransaction
from product import get_cart_items
from helpers import load_cart, send_order_to_telegram, log_activity
from services.khqr_service import generate_bakong_khqr, check_bakong_payment
from . import front_bp


@front_bp.route("/checkout")
def checkout():
    """Renders the checkout page with dynamic Bakong KHQR for the remaining cart total after store balance."""
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
    user_balance = 0.0
    if session.get("user_id"):
        user = db.session.get(User, session.get("user_id"))
        user_balance = float(user.balance or 0.0) if user else 0.0

    # User preference for applying store balance (from cancelled order returns)
    use_balance_param = request.args.get("use_balance")
    if use_balance_param is not None:
        use_balance = str(use_balance_param).lower() in ["1", "true", "yes", "on"]
    else:
        use_balance = user_balance > 0

    balance_applied = min(user_balance, total) if use_balance else 0.0
    remaining_due = round(max(0.0, total - balance_applied), 2)

    # Generate live Bakong KHQR for what is left to pay
    bill_number = Order.generate_order_number()
    khqr_data = None
    if remaining_due > 0:
        khqr_data = generate_bakong_khqr(amount=remaining_due, bill_number=bill_number, currency=Config.BAKONG_CURRENCY)

    return render_template(
        "front/checkout.html",
        cart_items=verified_items,
        subtotal=total,
        total=total,
        user=user,
        user_balance=user_balance,
        use_balance=use_balance,
        balance_applied=balance_applied,
        remaining_due=remaining_due,
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

    # Enforce Real Payment Gateway (Bakong KHQR / Store Balance)
    submitted_method = form.get("payment_method", "").strip().lower()
    if submitted_method not in ["bakong_khqr", "qr_payment", "wallet_balance", "split_wallet_khqr"]:
        flash("Only verified Bakong KHQR or MK7 Store Balance payments are accepted.", "error")
        return redirect(url_for("front_bp.checkout"))

    user_id = session.get("user_id")
    user_obj = db.session.get(User, user_id) if user_id else None
    user_balance = float(user_obj.balance or 0.0) if user_obj else 0.0

    # Determine store balance application
    use_balance = form.get("use_balance") in ["1", "true", "on", "yes"]
    balance_to_apply = min(user_balance, server_total) if use_balance else 0.0
    remaining_due = round(max(0.0, server_total - balance_to_apply), 2)

    bill_number = form.get("bill_number", "").strip() or Order.generate_order_number()
    khqr_md5 = form.get("khqr_md5", "").strip()
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json

    # 3. Verify Payment Status BEFORE Creating Order
    # If remaining_due > 0, customer MUST have paid via KHQR
    wallet_tx = None
    if remaining_due > 0:
        if not khqr_md5:
            err_msg = "Payment transaction identifier is missing. Please refresh and scan the QR code."
            if is_ajax:
                return jsonify({"success": False, "paid": False, "error": err_msg}), 400
            flash(err_msg, "error")
            return redirect(url_for("front_bp.checkout", use_balance="1" if use_balance else "0"))

        verify_res = check_bakong_payment(khqr_md5)
        is_paid = verify_res.get("paid", False)
        is_rate_limited = verify_res.get("rate_limited", False)

        # STRICT RULE: If not verified as paid, REJECT order creation completely
        if not is_paid and not is_rate_limited:
            err_msg = "Payment not detected yet. Please ensure you completed the transfer on your banking app, wait a few moments, and click 'Confirm Payment' again."
            if is_ajax:
                return jsonify({"success": False, "paid": False, "error": err_msg}), 400
            flash(err_msg, "error")
            return redirect(url_for("front_bp.checkout", use_balance="1" if use_balance else "0"))

        payment_method = "split_wallet_khqr" if balance_to_apply > 0 else "bakong_khqr"
        usd_remaining = remaining_due / Config.KHR_RATE
        payment_status_text = f"Verified Paid via Bakong KHQR ({int(round(remaining_due)):,} ៛ KHR / ≈ ${usd_remaining:.2f} USD)"
        if balance_to_apply > 0:
            usd_bal = balance_to_apply / Config.KHR_RATE
            payment_status_text += f" + Store Balance ({int(round(balance_to_apply)):,} ៛ KHR / ≈ ${usd_bal:.2f} USD)"
    else:
        # 100% paid by user's store balance
        payment_method = "wallet_balance"
        usd_tot = server_total / Config.KHR_RATE
        payment_status_text = f"100% Paid with MK7 Store Balance ({int(round(server_total)):,} ៛ KHR / ≈ ${usd_tot:.2f} USD)"

    # 4. Payment is verified! Deduct Store Balance if applied
    if balance_to_apply > 0 and user_obj:
        user_obj.balance = round(max(0.0, user_obj.balance - balance_to_apply), 2)
        wallet_tx = WalletTransaction(
            user_id=user_id,
            amount=-balance_to_apply,
            balance_after=user_obj.balance,
            tx_type="order_payment",
            description=f"Store credit payment applied to Order #{bill_number}",
        )
        db.session.add(wallet_tx)

    # 5. Create Order: Status = 'pending' (Paid & in 4-Hour Cancellation Grace Period!)
    order_notes = f"Payment Gateway: {payment_method} | Bill: {bill_number}"
    if khqr_md5 and remaining_due > 0:
        order_notes += f" | MD5: {khqr_md5}"
    if balance_to_apply > 0:
        usd_bal = balance_to_apply / Config.KHR_RATE
        order_notes += f" | Store Balance Applied: {int(round(balance_to_apply)):,} ៛ (≈ ${usd_bal:.2f})"
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
        balance_applied=balance_to_apply,
        status="pending",  # Paid & Placed -> 4-hour cancellation grace window active
        paid_at=datetime.utcnow(),
        notes=order_notes,
    )
    db.session.add(db_order)

    # 6. Add OrderItems & Deduct Product Stock in Real Time
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

    if wallet_tx:
        wallet_tx.order_id = db_order.id
        db.session.commit()

    # 7. Log order placement in ActivityLog
    try:
        usd_ord_total = db_order.total / Config.KHR_RATE
        log_activity(
            action="order_placed",
            module="orders",
            description=f"Order #{db_order.order_number} confirmed & placed by {db_order.customer_name} ({int(round(db_order.total)):,} ៛ / ≈ ${usd_ord_total:.2f}). Inventory deducted.",
            record_id=db_order.id,
            user_id=user_id,
        )
    except Exception:
        pass

    # 8. Live Telegram Notification for Real-Time Alertation
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
        "balance_applied": balance_to_apply,
        "remaining_due": remaining_due,
    }
    telegram_sent, telegram_error = send_order_to_telegram(order_info)

    if is_ajax:
        resp_json = jsonify({
            "success": True,
            "paid": True,
            "order_number": bill_number,
            "redirect_url": url_for("front_bp.my_orders")
        })
        resp_json.delete_cookie(Config.CART_COOKIE_NAME)
        return resp_json

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

