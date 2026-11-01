from datetime import datetime, timezone, timedelta
import json
from extensions import db

# Phnom Penh, Cambodia Timezone (UTC+7)
CAMBODIA_TZ = timezone(timedelta(hours=7))

def get_cambodia_now():
    """Returns current timestamp in Phnom Penh, Cambodia (UTC+7)."""
    return datetime.now(CAMBODIA_TZ).replace(tzinfo=None)


class ActivityLog(db.Model):
    __tablename__ = "activity_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=True)
    username = db.Column(db.String(100), nullable=True, default="Anonymous")
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    action = db.Column(db.String(50), nullable=False)  # RATE_LIMIT, LOGIN_FAILED, LOGIN_SUCCESS, CREATE, UPDATE, DELETE
    module = db.Column(db.String(50), nullable=False)  # RateLimit, Auth, User, Lab, Product
    record_id = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    old_data = db.Column(db.Text, nullable=True)  # JSON text
    new_data = db.Column(db.Text, nullable=True)  # JSON text
    created_at = db.Column(db.DateTime, default=get_cambodia_now, nullable=False)

    def __init__(
        self,
        action,
        module,
        user_id=None,
        username=None,
        ip_address=None,
        user_agent=None,
        record_id=None,
        description=None,
        old_data=None,
        new_data=None,
        created_at=None,
    ):
        self.action = action
        self.module = module
        self.user_id = user_id
        self.username = username or "Anonymous"
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.record_id = str(record_id) if record_id is not None else None
        self.description = description
        self.old_data = json.dumps(old_data, indent=2) if isinstance(old_data, (dict, list)) else old_data
        self.new_data = json.dumps(new_data, indent=2) if isinstance(new_data, (dict, list)) else new_data
        self.created_at = created_at or get_cambodia_now()

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "action": self.action,
            "module": self.module,
            "record_id": self.record_id,
            "description": self.description,
            "old_data": self.old_data,
            "new_data": self.new_data,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
