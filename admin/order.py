from datetime import datetime, timedelta
from flask import abort, jsonify, redirect, render_template, request, url_for, flash
from extensions import db, limiter
from models.order import Order, OrderItem
from models.product import Product
from models.users import User
from helpers import login_required, admin_user_id_key, log_activity
from . import admin_bp


@admin_bp.route("/orders")
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def orders():
    module = "orders"
    search_query = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip().lower()

    # 1. AUTO-CONFIRM EXPIRED PENDING ORDERS:
    # If customer order is past 4 hours, transition status from 'pending' to 'confirmed'
    now = datetime.utcnow()
    expired_pending = Order.query.filter(
        Order.status == "pending",
        Order.created_at != None,
        Order.created_at <= now - timedelta(hours=4)
    ).all()

    if expired_pending:
        for exp_order in expired_pending:
            exp_order.status = "confirmed"
            try:
                log_activity(
                    action="order_status_auto_confirmed",
                    module="orders",
                    description=f"Order #{exp_order.order_number} auto-confirmed after exceeding 4-hour cancellation window.",
                    record_id=exp_order.id,
                )
            except Exception:
                pass
        db.session.commit()

    query = Order.query

    if search_query:
        term = f"%{search_query}%"
        query = query.filter(
            (Order.order_number.ilike(term))
            | (Order.customer_name.ilike(term))
            | (Order.customer_email.ilike(term))
            | (Order.customer_phone.ilike(term))
        )

    if status_filter and status_filter != "all":
        query = query.filter(Order.status == status_filter)

    all_orders = query.order_by(Order.id.desc()).all()

    # Metrics
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status="pending").count()
    completed_orders = Order.query.filter(Order.status.in_(["delivered", "confirmed"])).count()
    total_revenue = sum(o.total for o in Order.query.filter(Order.status != "cancelled").all())

    return render_template(
        "admin/order/index.html",
        module=module,
        orders=all_orders,
        search_query=search_query,
        selected_status=status_filter,
        total_orders=total_orders,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        total_revenue=total_revenue,
    )


@admin_bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    """Returns order details JSON for dynamic modal inspection."""
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"success": False, "message": "Order not found."}), 404

    # Auto-confirm if past 4 hours
    now = datetime.utcnow()
    if order.status == "pending" and order.created_at and (now - order.created_at) >= timedelta(hours=4):
        order.status = "confirmed"
        db.session.commit()

    return jsonify({"success": True, "order": order.to_dict()})


@admin_bp.route("/orders/add", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def order_add():
    """
    Allows Admin to manually create / record a customer order ('add User's orders')
    and interacts with product inventory stock in real time.
    """
    module = "orders"
    all_users = User.query.order_by(User.username.asc()).all()
    all_products = Product.query.order_by(Product.title.asc()).all()

    if request.method == "POST":
        form = request.form
        selected_user_id = form.get("user_id")
        customer_name = form.get("customer_name", "").strip()
        customer_email = form.get("customer_email", "").strip()
        customer_phone = form.get("customer_phone", "").strip()
        shipping_address = form.get("shipping_address", "").strip()
        city = form.get("city", "").strip()
        zip_code = form.get("zip_code", "").strip()
        payment_method = form.get("payment_method", "qr_payment")
        order_status = form.get("status", "confirmed")
        notes = form.get("notes", "").strip()

        # Parse line items
        product_ids = form.getlist("product_id[]")
        quantities = form.getlist("quantity[]")

        if not customer_name or not customer_email:
            flash("Customer name and email are required.", "error")
            return render_template(
                "admin/order/add.html",
                module=module,
                users=all_users,
                products=all_products,
            )

        if not product_ids:
            flash("Please add at least one product item to the order.", "error")
            return render_template(
                "admin/order/add.html",
                module=module,
                users=all_users,
                products=all_products,
            )

        # Validate line items and stock
        items_to_create = []
        subtotal = 0.0

        for p_id_str, qty_str in zip(product_ids, quantities):
            if not p_id_str or not qty_str:
                continue
            try:
                p_id = int(p_id_str)
                qty = int(qty_str)
            except ValueError:
                continue

            if qty <= 0:
                continue

            prod = Product.query.get(p_id)
            if not prod:
                continue

            # STOCK INTERACTION: Check if requested stock is available
            if order_status != "cancelled" and prod.stock < qty:
                flash(
                    f"Insufficient stock for '{prod.title}'. Requested: {qty}, Available: {prod.stock}.",
                    "error",
                )
                return render_template(
                    "admin/order/add.html",
                    module=module,
                    users=all_users,
                    products=all_products,
                )

            item_subtotal = round(prod.price * qty, 2)
            subtotal += item_subtotal

            items_to_create.append({
                "product": prod,
                "quantity": qty,
                "price": prod.price,
                "subtotal": item_subtotal,
            })

        if not items_to_create:
            flash("No valid product line items were selected.", "error")
            return render_template(
                "admin/order/add.html",
                module=module,
                users=all_users,
                products=all_products,
            )

        user_id_int = int(selected_user_id) if selected_user_id and selected_user_id.isdigit() else None

        # Create Order
        new_order = Order(
            order_number=Order.generate_order_number(),
            user_id=user_id_int,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            shipping_address=shipping_address,
            city=city,
            zip_code=zip_code,
            payment_method=payment_method,
            subtotal=subtotal,
            total=subtotal,
            status=order_status,
            notes=notes,
        )
        db.session.add(new_order)

        # Create Items & Deduct Stock
        for it in items_to_create:
            p = it["product"]
            order_item = OrderItem(
                order=new_order,
                product_id=p.id,
                product_title=p.title,
                product_price=p.price,
                product_image=p.image,
                quantity=it["quantity"],
                subtotal=it["subtotal"],
            )
            db.session.add(order_item)

            # STOCK INTERACTION: Deduct stock if order is active
            if order_status != "cancelled":
                p.stock = max(0, p.stock - it["quantity"])

        db.session.commit()

        # Audit log
        try:
            log_activity(
                action="admin_order_create",
                module="orders",
                description=f"Admin created Order #{new_order.order_number} for {customer_name} (${new_order.total:.2f}). Inventory deducted.",
            )
        except Exception:
            pass

        flash(
            f"Order #{new_order.order_number} created successfully and inventory stock deducted.",
            "success",
        )
        return redirect(url_for("admin_bp.orders"))

    return render_template(
        "admin/order/add.html",
        module=module,
        users=all_users,
        products=all_products,
    )


@admin_bp.post("/orders/<int:order_id>/status")
@login_required
def order_update_status(order_id):
    """
    Updates order status and manages bidirectional stock interaction:
    - If status changes to 'cancelled', restocks items.
    - If status restored from 'cancelled' to active, re-deducts items.
    """
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"success": False, "message": "Order not found."}), 404

    data = request.get_json(silent=True) or request.form
    new_status = data.get("status", "").strip().lower()
    valid_statuses = {"pending", "confirmed", "processing", "shipped", "delivered", "cancelled"}

    if new_status not in valid_statuses:
        return jsonify({"success": False, "message": "Invalid status value."}), 400

    old_status = order.status
    if old_status == new_status:
        return jsonify({"success": True, "message": "Status unchanged.", "status": new_status})

    # STOCK INTERACTION
    if old_status != "cancelled" and new_status == "cancelled":
        # RESTOCK: Return items back to product inventory
        for item in order.items:
            if item.product_id:
                p = Product.query.get(item.product_id)
                if p:
                    p.stock += item.quantity
    elif old_status == "cancelled" and new_status != "cancelled":
        # RE-DEDUCT: Take inventory back
        for item in order.items:
            if item.product_id:
                p = Product.query.get(item.product_id)
                if p:
                    p.stock = max(0, p.stock - item.quantity)

    order.status = new_status
    db.session.commit()

    if old_status != "cancelled" and new_status == "cancelled":
        try:
            from helpers import send_order_cancellation_to_telegram
            send_order_cancellation_to_telegram(
                order,
                reason=f"Order status changed to Cancelled by Admin ({session.get('username', 'Admin')}). Inventory was restocked."
            )
        except Exception:
            pass

    try:
        log_activity(
            action="order_status_update",
            module="orders",
            description=f"Order #{order.order_number} status changed from {old_status} to {new_status}.",
        )
    except Exception:
        pass

    return jsonify({
        "success": True,
        "message": f"Order #{order.order_number} status updated to '{new_status.title()}'.",
        "status": new_status,
    })


@admin_bp.post("/orders/<int:order_id>/delete")
@login_required
def order_delete(order_id):
    """Deletes order and restores stock if the order was active."""
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"success": False, "message": "Order not found."}), 404

    order_num = order.order_number

    # Restock inventory if deleted while active
    if order.status != "cancelled":
        for item in order.items:
            if item.product_id:
                p = Product.query.get(item.product_id)
                if p:
                    p.stock += item.quantity

    db.session.delete(order)
    db.session.commit()

    try:
        log_activity(
            action="order_deleted",
            module="orders",
            description=f"Admin deleted Order #{order_num}. Associated inventory restocked.",
        )
    except Exception:
        pass

    return jsonify({"success": True, "message": f"Order #{order_num} deleted successfully."})
