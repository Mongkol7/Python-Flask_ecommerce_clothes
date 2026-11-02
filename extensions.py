from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()


def get_limiter_client_ip():
    """Extracts client IP accurately across Cloudflare, Nginx reverse proxy, and direct connections."""
    try:
        from flask import request
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip and cf_ip.strip():
            return cf_ip.strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip and real_ip.strip():
            return real_ip.strip()
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
            if client_ip:
                return client_ip
        if request.remote_addr:
            return request.remote_addr
    except Exception:
        pass
    return get_remote_address()


limiter = Limiter(
    key_func=get_limiter_client_ip,
    default_limits=["100 per minute", "10000 per day"]
)
cors = CORS()
csrf = CSRFProtect()
