from datetime import datetime
import uuid
from extensions import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(60), nullable=True)
    shipping_address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(80), nullable=True)
    zip_code = db.Column(db.String(30), nullable=True)
    payment_method = db.Column(db.String(50), default="qr_payment")
    subtotal = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default="pending")  # pending, confirmed, processing, shipped, delivered, cancelled
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("orders", lazy=True))
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def generate_order_number():
        """Generate human-readable order number: e.g. ORD-20261024-A1B2"""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        rand_suffix = uuid.uuid4().hex[:5].upper()
        return f"ORD-{date_str}-{rand_suffix}"

    def to_dict(self):
        return {
            "id": self.id,
            "order_number": self.order_number,
            "user_id": self.user_id,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "customer_phone": self.customer_phone,
            "shipping_address": self.shipping_address,
            "city": self.city,
            "zip_code": self.zip_code,
            "payment_method": self.payment_method,
            "subtotal": self.subtotal,
            "total": self.total,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "items": [item.to_dict() for item in self.items],
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=True)
    product_title = db.Column(db.String(255), nullable=False)
    product_price = db.Column(db.Float, default=0.0)
    product_image = db.Column(db.String(255), nullable=True)
    quantity = db.Column(db.Integer, default=1)
    subtotal = db.Column(db.Float, default=0.0)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_title": self.product_title,
            "product_price": self.product_price,
            "product_image": self.product_image,
            "quantity": self.quantity,
            "subtotal": self.subtotal,
        }
