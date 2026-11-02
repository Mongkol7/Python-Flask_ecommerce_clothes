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
    balance_applied = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default="pending")  # pending, confirmed, processing, shipped, delivered, cancelled
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)

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

    def get_paid_at(self):
        """Returns the confirmed payment datetime (or created_at if pre-paid)."""
        return self.paid_at or self.created_at

    def get_cancelled_at(self):
        """Returns the cancellation datetime, falling back to wallet transaction or created_at."""
        if self.cancelled_at:
            return self.cancelled_at
        if self.status == "cancelled":
            if hasattr(self, "wallet_transactions") and self.wallet_transactions:
                for tx in self.wallet_transactions:
                    if tx.tx_type == "refund_credit" and tx.created_at:
                        return tx.created_at
            return self.created_at
        return None

    def parse_notes(self):
        """Parses the structured/concatenated order notes into clean distinct components."""
        raw = self.notes or ""
        customer_lines = []
        gateway = (self.payment_method or "").replace("_", " ").title()
        md5_hash = ""
        bill_ref = ""
        audit_note = ""

        if not raw.strip():
            return {
                "customer_note": "",
                "gateway": gateway,
                "md5": "",
                "bill": bill_ref,
                "audit": "",
                "raw": "",
            }

        lines = [line.strip() for line in raw.split("\n") if line.strip()]
        for line in lines:
            if "Payment Gateway:" in line or "Bill:" in line or "MD5:" in line:
                parts = [p.strip() for p in line.split("|")]
                for p in parts:
                    if p.startswith("Payment Gateway:"):
                        gw_val = p.replace("Payment Gateway:", "").strip()
                        if gw_val:
                            gateway = gw_val
                    elif p.startswith("Bill:"):
                        bill_ref = p.replace("Bill:", "").strip()
                    elif p.startswith("MD5:"):
                        md5_hash = p.replace("MD5:", "").strip()
            elif line.startswith("Customer Note:"):
                val = line.replace("Customer Note:", "").strip()
                if val:
                    customer_lines.append(val)
            elif line.startswith("[Confirmed]:") or line.startswith("[Verification]:"):
                audit_note = line
            else:
                customer_lines.append(line)

        return {
            "customer_note": "\n".join(customer_lines).strip(),
            "gateway": gateway,
            "md5": md5_hash,
            "bill": bill_ref,
            "audit": audit_note,
            "raw": raw,
        }

    def to_dict(self):
        from datetime import timedelta
        paid_dt = self.get_paid_at()
        cancelled_dt = self.get_cancelled_at()
        cam_tz = timedelta(hours=7)

        created_pp = (self.created_at + cam_tz).strftime("%Y-%m-%d %I:%M:%S %p") if self.created_at else None
        paid_pp = (paid_dt + cam_tz).strftime("%Y-%m-%d %I:%M:%S %p") if paid_dt else None
        cancelled_pp = (cancelled_dt + cam_tz).strftime("%Y-%m-%d %I:%M:%S %p") if cancelled_dt else None

        bal_applied = float(getattr(self, "balance_applied", 0.0) or 0.0)
        tot = float(self.total or 0.0)
        rem_due = max(0.0, tot - bal_applied)

        parsed = self.parse_notes()

        items_data = []
        for item in self.items:
            item_d = item.to_dict()
            if item.product:
                item_d["current_stock"] = item.product.stock
            else:
                item_d["current_stock"] = 0
            items_data.append(item_d)

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
            "balance_applied": bal_applied,
            "remaining_due": rem_due,
            "status": self.status,
            "notes": self.notes,
            "customer_note": parsed["customer_note"],
            "gateway_name": parsed["gateway"],
            "bill_ref": parsed["bill"] or self.order_number,
            "khqr_md5": parsed["md5"],
            "audit_note": parsed["audit"],
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "created_at_pp": created_pp,
            "paid_at_pp": paid_pp,
            "cancelled_at": cancelled_dt.strftime("%Y-%m-%d %H:%M:%S") if cancelled_dt else None,
            "cancelled_at_pp": cancelled_pp,
            "items": items_data,
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
