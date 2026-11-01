from datetime import datetime
from extensions import db


class WalletTransaction(db.Model):
    __tablename__ = "wallet_transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    amount = db.Column(db.Float, nullable=False)  # positive for refund/credit, negative for payment deduction
    balance_after = db.Column(db.Float, nullable=False, default=0.0)
    tx_type = db.Column(db.String(50), nullable=False)  # 'refund_credit', 'order_payment', 'admin_adjustment'
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("wallet_transactions", lazy=True, order_by="desc(WalletTransaction.id)"))
    order = db.relationship("Order", backref=db.backref("wallet_transactions", lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "order_id": self.order_id,
            "amount": self.amount,
            "balance_after": self.balance_after,
            "tx_type": self.tx_type,
            "description": self.description,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default="refund")  # 'refund', 'order', 'system'
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("notifications", lazy=True, order_by="desc(Notification.id)"))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "category": self.category,
            "link": self.link,
            "is_read": self.is_read,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }

