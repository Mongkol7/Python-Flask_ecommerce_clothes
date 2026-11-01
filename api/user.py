from sqlalchemy import text
from extensions import db
from . import api_bp
from .jwt_auth import jwt_required


@api_bp.route("/user", methods=["GET"])
@api_bp.route("/users", methods=["GET"])
def user():
    """
    Returns user directory for authorized API clients.
    """
    sql = text("SELECT id, username, email, role, profile FROM user")
    result = db.session.execute(sql)
    rows = [dict(row._mapping) for row in result]
    return rows
