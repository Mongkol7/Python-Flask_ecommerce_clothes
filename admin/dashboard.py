from datetime import datetime, timedelta
from flask import render_template
from sqlalchemy import func
from extensions import db, limiter
from helpers import login_required, admin_user_id_key
from models import User, Product, Category, Brand, Order, OrderItem, ActivityLog
from . import admin_bp


@admin_bp.route("/dashboard")
@login_required
@limiter.limit("60 per minute", key_func=admin_user_id_key, methods=["GET"])
def dashboard():
    module = "dashboard"

    # 1. User Metrics
    total_users = User.query.count()
    admin_users = User.query.filter_by(role="admin").count()
    customer_users = max(0, total_users - admin_users)
    recent_users = User.query.order_by(User.id.desc()).limit(5).all()

    # 2. Product & Inventory Metrics
    total_products = Product.query.count()
    total_stock = db.session.query(func.sum(Product.stock)).scalar() or 0
    low_stock_products = Product.query.filter(Product.stock <= 15).order_by(Product.stock.asc()).limit(5).all()
    out_of_stock_count = Product.query.filter(Product.stock <= 0).count()

    # 3. Category & Brand Metrics
    categories = Category.query.order_by(Category.id.asc()).all()
    category_stats = []
    for cat in categories:
        count = len(cat.products) if cat.products else 0
        pct = round((count / total_products * 100), 1) if total_products > 0 else 0
        category_stats.append({
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "count": count,
            "percentage": pct,
        })
    total_brands = Brand.query.count()

    # 4. Order & Revenue Metrics
    now = datetime.utcnow()
    expired_pending = Order.query.filter(
        Order.status == "pending",
        Order.created_at != None,
        Order.created_at <= now - timedelta(hours=4)
    ).all()
    if expired_pending:
        for exp_order in expired_pending:
            exp_order.status = "confirmed"
        db.session.commit()

    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status="pending").count()
    confirmed_orders = Order.query.filter_by(status="confirmed").count()
    delivered_orders = Order.query.filter_by(status="delivered").count()
    cancelled_orders = Order.query.filter_by(status="cancelled").count()

    # Financial & Accounting Calculations: Gross Sales, Net Realized Revenue, Cancelled Loss, Customer Store Credit Liability
    gross_sales = db.session.query(func.sum(Order.total)).scalar() or 0.0
    cancelled_loss = db.session.query(func.sum(Order.total)).filter(Order.status == "cancelled").scalar() or 0.0
    net_revenue = db.session.query(func.sum(Order.total)).filter(Order.status != "cancelled").scalar() or 0.0
    cancellation_rate = round((cancelled_orders / total_orders * 100), 1) if total_orders > 0 else 0.0
    total_store_balance_liability = db.session.query(func.sum(User.balance)).scalar() or 0.0

    recent_orders = Order.query.order_by(Order.id.desc()).limit(6).all()

    # 5. Real Chart Timeline: Past 7 Days (Net Sales vs. Cancelled Loss)
    today = datetime.utcnow().date()
    date_labels = []
    daily_revenue = []
    daily_cancelled = []
    daily_orders_count = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        display_label = day.strftime("%b %d")
        date_labels.append(display_label)

        day_orders = [o for o in Order.query.all() if o.created_at and o.created_at.date() == day]
        day_rev = sum(o.total for o in day_orders if o.status != "cancelled")
        day_canc = sum(o.total for o in day_orders if o.status == "cancelled")
        daily_revenue.append(round(float(day_rev), 2))
        daily_cancelled.append(round(float(day_canc), 2))
        daily_orders_count.append(len(day_orders))

    # 6. Recent Activity & Security Logs
    recent_logs = ActivityLog.query.order_by(ActivityLog.id.desc()).limit(5).all()

    stats = {
        "total_revenue": net_revenue,
        "gross_sales": gross_sales,
        "cancelled_loss": cancelled_loss,
        "cancellation_rate": cancellation_rate,
        "store_balance_liability": total_store_balance_liability,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "confirmed_orders": confirmed_orders,
        "delivered_orders": delivered_orders,
        "cancelled_orders": cancelled_orders,
        "total_products": total_products,
        "total_stock": total_stock,
        "out_of_stock_count": out_of_stock_count,
        "low_stock_count": len(low_stock_products),
        "total_users": total_users,
        "admin_users": admin_users,
        "customer_users": customer_users,
        "total_categories": len(categories),
        "total_brands": total_brands,
        "chart_dates": date_labels,
        "chart_revenue": daily_revenue,
        "chart_cancelled": daily_cancelled,
        "chart_orders": daily_orders_count,
        "khr_rate": getattr(Config, "KHR_RATE", 4000.0),
    }

    return render_template(
        "admin/dashboard.html",
        module=module,
        stats=stats,
        recent_orders=recent_orders,
        low_stock_products=low_stock_products,
        category_stats=category_stats,
        recent_logs=recent_logs,
        recent_users=recent_users,
    )
