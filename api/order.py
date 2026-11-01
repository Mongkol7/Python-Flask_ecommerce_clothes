from flask import jsonify, request, g
from extensions import db
from models.order import Order, OrderItem
from models.product import Product
from . import api_bp
from .jwt_auth import jwt_required, jwt_admin_required


@api_bp.route("/orders", methods=["GET"])
@jwt_required
def get_orders():
    """
    List orders. Admins see all orders; regular shoppers see only their own orders.
    """
    current_user = g.current_user
    if current_user.role == "admin":
        orders_list = Order.query.order_by(Order.id.desc()).all()
    else:
        orders_list = Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all()

    return jsonify([o.to_dict() for o in orders_list]), 200


@api_bp.route("/orders/<int:order_id>", methods=["GET"])
@jwt_required
def get_order_detail(order_id):
    """Retrieve details of a single order."""
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"success": False, "error": "Order not found"}), 404

    current_user = g.current_user
    if current_user.role != "admin" and order.user_id != current_user.id:
        return jsonify({"success": False, "error": "Forbidden"}), 403

    return jsonify({"success": True, "order": order.to_dict()}), 200


@api_bp.route("/orders", methods=["POST"])
@jwt_required
def create_order():
    """
    Place a new order via API.
    Interacts with product stock in real time, deducting available quantities.
    JSON payload: {
        "customer_name": "...",
        "customer_email": "...",
        "customer_phone": "...",
        "shipping_address": "...",
        "city": "...",
        "zip_code": "...",
        "payment_method": "qr_payment",
        "items": [{"product_id": 1, "quantity": 2}, ...]
    }
    """
    data = request.get_json(silent=True) or {}
    items_data = data.get("items", [])

    if not items_data:
        return jsonify({"success": False, "error": "At least one item is required."}), 400

    current_user = g.current_user
    customer_name = data.get("customer_name") or current_user.username
    customer_email = data.get("customer_email") or current_user.email
    customer_phone = data.get("customer_phone", "")
    shipping_address = data.get("shipping_address", "")
    city = data.get("city", "Phnom Penh")
    zip_code = data.get("zip_code", "12000")
    payment_method = data.get("payment_method", "qr_payment")
    notes = data.get("notes", "")

    # Validate all items and stock before committing
    order_items_to_save = []
    subtotal = 0.0

    for it in items_data:
        p_id = it.get("product_id")
        qty = it.get("quantity", 1)

        try:
            qty = int(qty)
        except (ValueError, TypeError):
            continue

        if qty <= 0:
            continue

        prod = Product.query.get(p_id)
        if not prod:
            return jsonify({"success": False, "error": f"Product #{p_id} not found."}), 404

        if prod.stock < qty:
            return jsonify({
                "success": False,
                "error": f"Insufficient stock for '{prod.title}'. Available: {prod.stock}, requested: {qty}."
            }), 400

        item_subtotal = round(prod.price * qty, 2)
        subtotal += item_subtotal

        order_items_to_save.append({
            "product": prod,
            "quantity": qty,
            "subtotal": item_subtotal,
        })

    if not order_items_to_save:
        return jsonify({"success": False, "error": "No valid product items in order."}), 400

    # Create Order
    new_order = Order(
        order_number=Order.generate_order_number(),
        user_id=current_user.id,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        shipping_address=shipping_address,
        city=city,
        zip_code=zip_code,
        payment_method=payment_method,
        subtotal=subtotal,
        total=subtotal,
        status="confirmed",
        notes=notes,
    )
    db.session.add(new_order)

    # Save Items and DEDUCT INVENTORY IN REAL TIME
    for entry in order_items_to_save:
        p = entry["product"]
        q = entry["quantity"]
        order_item = OrderItem(
            order=new_order,
            product_id=p.id,
            product_title=p.title,
            product_price=p.price,
            product_image=p.image,
            quantity=q,
            subtotal=entry["subtotal"],
        )
        db.session.add(order_item)

        # Real-time stock reduction
        p.stock = max(0, p.stock - q)

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Order #{new_order.order_number} created and inventory deducted.",
        "order": new_order.to_dict(),
    }), 201


@api_bp.route("/orders/<int:order_id>/status", methods=["PUT", "PATCH"])
@jwt_admin_required
def update_order_status_api(order_id):
    """Update order status via API with automated stock sync."""
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"success": False, "error": "Order not found"}), 404

    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").strip().lower()
    valid_statuses = {"pending", "confirmed", "processing", "shipped", "delivered", "cancelled"}

    if new_status not in valid_statuses:
        return jsonify({"success": False, "error": "Invalid status value."}), 400

    old_status = order.status
    if old_status == new_status:
        return jsonify({"success": True, "message": "Status unchanged.", "order": order.to_dict()}), 200

    # Restock or re-deduct
    if old_status != "cancelled" and new_status == "cancelled":
        for item in order.items:
            if item.product_id:
                p = Product.query.get(item.product_id)
                if p:
                    p.stock += item.quantity
    elif old_status == "cancelled" and new_status != "cancelled":
        for item in order.items:
            if item.product_id:
                p = Product.query.get(item.product_id)
                if p:
                    p.stock = max(0, p.stock - item.quantity)

    order.status = new_status
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Order status updated to '{new_status}'.",
        "order": order.to_dict(),
    }), 200
