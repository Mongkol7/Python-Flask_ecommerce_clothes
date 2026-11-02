import os
import re
from flask import Flask, session, request, render_template, abort, url_for as flask_url_for
from markupsafe import Markup, escape
from sqlalchemy import text
from config import Config
from extensions import db, migrate, limiter, cors, csrf
from flask_wtf.csrf import CSRFError
from helpers import (
    load_cart,
    get_client_public_ip,
    send_telegram_alert,
    record_login_ban,
    is_ip_login_banned,
    record_signup_ban,
    is_ip_signup_banned,
    log_activity,
)
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException
from front import front_bp
from admin import admin_bp
from api import api_bp

app = Flask(__name__)
app.config.from_object(Config)

# Support reverse proxy headers (Nginx X-Forwarded-For)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Ensure upload folders exist
os.makedirs(app.config["UPLOAD_USER_FOLDER"], exist_ok=True)
os.makedirs(app.config["UPLOAD_PRODUCT_FOLDER"], exist_ok=True)
os.makedirs(app.config["UPLOAD_BRAND_FOLDER"], exist_ok=True)
os.makedirs(app.config["UPLOAD_CATEGORY_FOLDER"], exist_ok=True)
os.makedirs(app.config["UPLOAD_CAROUSEL_FOLDER"], exist_ok=True)

# Initialize extensions
db.init_app(app)
migrate.init_app(app, db)
limiter.init_app(app)

# Ensure database tables and initial catalog seeds exist
with app.app_context():
    from models.seed import seed_database
    seed_database()

# Configure Flask-CORS for testing from Angular (http://localhost:4200) and other frontends
cors.init_app(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:4200",
                "http://127.0.0.1:4200",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
        }
    },
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
    supports_credentials=True,
)

csrf.init_app(app)

# Exempt API blueprint from CSRF so cross-origin/external API clients can interact via CORS
csrf.exempt(api_bp)

# Register Blueprints
app.register_blueprint(front_bp, url_prefix="/")
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(api_bp, url_prefix="/api")


# Smart url_for template global: seamlessly supports both 'home' and 'front_bp.home'
@app.template_global("url_for")
def smart_url_for(endpoint, **values):
    try:
        return flask_url_for(endpoint, **values)
    except Exception:
        pass
    for prefix in ["front_bp", "admin_bp", "api_bp"]:
        try:
            return flask_url_for(f"{prefix}.{endpoint}", **values)
        except Exception:
            pass
    return flask_url_for(endpoint, **values)


# Template Filters
@app.template_filter("highlight_query")
def highlight_query(value, query):
    value = str(value)
    query = str(query).strip()

    if not query:
        return escape(value)

    pattern = re.compile(f"({re.escape(query)})", re.IGNORECASE)
    parts = pattern.split(value)

    highlighted_parts = []
    for part in parts:
        if part.lower() == query.lower():
            highlighted_parts.append(
                f'<mark class="search-highlight">{escape(part)}</mark>'
            )
        else:
            highlighted_parts.append(str(escape(part)))

    return Markup("".join(highlighted_parts))


@app.template_filter("profile_url")
def profile_url(profile, user_id=None, version="thum"):
    if not profile:
        return ""
    if user_id:
        version_filename = f"{user_id}_{version}_{profile}"
        return flask_url_for("static", filename=f"image/user/{version_filename}")
    return flask_url_for("static", filename=f"image/user/{profile}")


@app.template_filter("khr_format")
def khr_format(value):
    """Formats a price value as Cambodian Riel: e.g. 200 ៛"""
    try:
        val = float(value or 0)
        return f"{int(round(val)):,} ៛"
    except (ValueError, TypeError):
        return f"{value} ៛"


@app.template_filter("usd_format")
def usd_format(value, rate=None):
    """Converts a KHR price value to estimated USD: e.g. ≈ $0.05"""
    try:
        if rate is None:
            rate = getattr(Config, "KHR_RATE", 4000.0)
        val = float(value or 0) / float(rate)
        return f"≈ ${val:.2f}"
    except (ValueError, TypeError):
        return "$0.00"


@app.template_filter("cambodia_time")
def cambodia_time_filter(value, fmt="%Y-%m-%d %I:%M %p"):
    """Converts a UTC datetime object or ISO string into Phnom Penh, Cambodia (UTC+7) time."""
    if not value:
        return "—"
    try:
        from datetime import datetime, timedelta
        dt = value
        if isinstance(value, str):
            for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                try:
                    dt = datetime.strptime(value, pattern)
                    break
                except ValueError:
                    pass
        if hasattr(dt, "strftime"):
            pp_dt = dt + timedelta(hours=7)
            return pp_dt.strftime(fmt)
        return str(value)
    except Exception:
        return str(value)


# Context Processors
@app.context_processor
def inject_currency_helpers():
    return {
        "khr_rate": getattr(Config, "KHR_RATE", 4000.0),
        "khr_format": khr_format,
        "usd_format": usd_format,
        "cambodia_time": cambodia_time_filter,
    }
@app.context_processor
def inject_cart_count():
    cart_count = len({item["id"] for item in load_cart()})
    return {"cart_count": cart_count}


@app.context_processor
def inject_current_user():
    current_admin = None
    if session.get("is_login") and session.get("user_id"):
        try:
            sql = text("SELECT id, username, email, role, profile FROM user WHERE id = :id")
            res = db.session.execute(sql, {"id": session.get("user_id")}).fetchone()
            if res:
                current_admin = dict(res._mapping)
        except Exception:
            current_admin = None
    return dict(current_admin=current_admin, current_user=current_admin)


# Test Routes for HTTP 500, HTTP 429 & HTTP 400 using real errors
@app.route("/test500")
def test_500():
    # Real Python runtime error: ZeroDivisionError (division by zero)
    raise ZeroDivisionError("division by zero")


@app.route("/api/test500")
def api_test_500():
    # Real Python runtime error: ZeroDivisionError (division by zero)
    raise ZeroDivisionError("division by zero")


@app.route("/test429")
def test_429():
    from flask import abort
    abort(429, description="Too many requests. Rate limit enforcement active for your IP address.")


@app.route("/api/test429")
def api_test_429():
    from flask import abort
    abort(429, description="Too many requests. Rate limit enforcement active for your IP address.")


@app.route("/test400")
def test_400():
    # Real client error: Accessing missing required query parameter raises BadRequestKeyError (HTTP 400)
    return request.args["missing_param"]


@app.route("/api/test400")
def api_test_400():
    # Real client error: Accessing missing required query parameter raises BadRequestKeyError (HTTP 400)
    return request.args["missing_param"]


# Error Handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    try:
        is_login_route = (
            request.path in ("/login", "/user/login", "/admin/login")
            or (request.endpoint and "login" in request.endpoint)
        )
        is_signup_route = (
            request.path in ("/register", "/signup", "/user/register", "/user/signup")
            or (request.endpoint and ("register" in request.endpoint or "signup" in request.endpoint))
        )

        # Record separated temporary bans with timer preservation
        if is_login_route:
            record_login_ban(60)
        elif is_signup_route:
            record_signup_ban(60)
    except Exception:
        pass

    try:
        send_telegram_alert(e)
    except Exception as ex:
        print(f"[Telegram Alert Error]: {ex}")

    client_ip = get_client_public_ip()
    err_msg = str(e.description if hasattr(e, "description") else e)

    try:
        if is_login_route:
            rem_ban = is_ip_login_banned()
        elif is_signup_route:
            rem_ban = is_ip_signup_banned()
        else:
            rem_ban = max(is_ip_login_banned(), is_ip_signup_banned())
    except Exception:
        rem_ban = 60

    retry_after = rem_ban if rem_ban > 0 else 60

    # Save Rate Limit Log into database
    try:
        user_id = session.get("user_id") if session else None
        username = session.get("username") if session else None
        role = session.get("role") if session else None

        if user_id:
            action_name = "USER_RATE_LIMIT"
            module_name = "UserRateLimit"
            desc = f"User '{username}' (ID: {user_id}, Role: {role}) exceeded activity rate limit on {request.method} {request.path}: {err_msg}"
        else:
            action_name = "IP_RATE_LIMIT"
            module_name = "IpRateLimit"
            desc = f"IP '{client_ip}' exceeded rate limit on {request.method} {request.path}: {err_msg}"

        rate_limit_err_json = {
            "status": 429,
            "error": "Rate limit exceeded",
            "limit_type": "user_id" if user_id else "ip",
            "user_id": user_id,
            "username": username,
            "role": role,
            "description": err_msg,
            "ip": client_ip,
            "endpoint": request.endpoint,
            "path": request.path,
            "method": request.method,
            "retry_after": retry_after,
        }
        log_activity(
            action=action_name,
            module=module_name,
            description=desc,
            user_id=user_id,
            username=username or "Anonymous",
            record_id=user_id,
            new_data=rate_limit_err_json,
        )
    except Exception as db_err:
        print(f"[ActivityLog Error in 429 handler]: {db_err}")

    if request.path.startswith("/api/"):
        return {
            "status": 429,
            "message": "Too many requests",
            "ip": client_ip,
            "error": err_msg,
            "retry_after": retry_after,
        }, 429
    return (
        render_template(
            "429.html",
            ip=client_ip,
            error=err_msg,
            retry_after=retry_after,
        ),
        429,
    )


@app.route("/api/data", methods=["GET"])
def api_data():
    """Test endpoint for cross-origin frontend testing (CORS)."""
    return {"message": "CORS enabled", "status": "allowed"}


@app.errorhandler(404)
def not_found_handler(e):
    client_ip = get_client_public_ip()
    err_msg = str(e.description if hasattr(e, "description") else e)
    if request.path.startswith("/api/"):
        return {
            "status": 404,
            "message": "Not found",
            "ip": client_ip,
            "error": err_msg,
        }, 404
    return (
        render_template(
            "404.html",
            ip=client_ip,
            error=err_msg,
        ),
        404,
    )


@app.errorhandler(500)
@app.errorhandler(Exception)
def internal_error_handler(e):
    # Pass through standard HTTP errors so Exception doesn't swallow 429, 404, 400, etc.
    if isinstance(e, HTTPException):
        if e.code == 429:
            return ratelimit_handler(e)
        if e.code == 404:
            return not_found_handler(e)
        if e.code == 400:
            return bad_request_handler(e)
        if e.code != 500:
            return e

    # Roll back any aborted database transactions from the failed request
    try:
        db.session.rollback()
    except Exception:
        pass

    try:
        send_telegram_alert(e)
    except Exception as ex:
        print(f"[Telegram Alert Error in 500 handler]: {ex}")

    client_ip = get_client_public_ip()
    err_msg = str(e.description if hasattr(e, "description") else e)

    # Save 500 error into database activity_log (User requirement: activity logs just for rate limit and 500)
    try:
        user_id = session.get("user_id") if session else None
        username = session.get("username") if session else None
        role = session.get("role") if session else None
        err_type = type(e).__name__

        err_500_json = {
            "status": 500,
            "error_type": err_type,
            "message": err_msg,
            "path": request.path,
            "method": request.method,
            "ip": client_ip,
            "user_id": user_id,
            "username": username,
            "role": role,
        }
        log_activity(
            action="500_INTERNAL_ERROR",
            module="Error500",
            description=f"HTTP 500 {err_type} on {request.method} {request.path}: {err_msg}",
            user_id=user_id,
            username=username or "Anonymous",
            record_id=user_id,
            new_data=err_500_json,
        )
    except Exception as db_err:
        print(f"[ActivityLog Error in 500 handler]: {db_err}")

    if request.path.startswith("/api/"):
        return {
            "status": 500,
            "message": "Internal server error",
            "ip": client_ip,
            "error": err_msg,
        }, 500
    return (
        render_template(
            "500.html",
            ip=client_ip,
            error=err_msg,
        ),
        500,
    )


@app.errorhandler(CSRFError)
def csrf_error_handler(e):
    client_ip = get_client_public_ip()
    err_msg = str(e.description if hasattr(e, "description") else e)
    if (
        request.path.startswith("/api/")
        or request.is_json
        or request.headers.get("Accept") == "application/json"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        return {
            "status": 400,
            "message": "CSRF validation failed",
            "ip": client_ip,
            "error": err_msg,
        }, 400
    return (
        render_template(
            "400.html",
            ip=client_ip,
            error=err_msg,
        ),
        400,
    )


@app.errorhandler(400)
def bad_request_handler(e):
    client_ip = get_client_public_ip()
    err_msg = str(e.description if hasattr(e, "description") else e)
    if (
        request.path.startswith("/api/")
        or request.is_json
        or request.headers.get("Accept") == "application/json"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        return {
            "status": 400,
            "message": "Bad request",
            "ip": client_ip,
            "error": err_msg,
        }, 400
    return (
        render_template(
            "400.html",
            ip=client_ip,
            error=err_msg,
        ),
        400,
    )


# Load models and ensure database tables exist
import models

with app.app_context():
    db.create_all()
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        user_cols = [c["name"] for c in inspector.get_columns("user")]
        if "balance" not in user_cols:
            db.session.execute(text("ALTER TABLE user ADD COLUMN balance FLOAT DEFAULT 0.0"))
            db.session.commit()
        order_cols = [c["name"] for c in inspector.get_columns("orders")]
        if "balance_applied" not in order_cols:
            db.session.execute(text("ALTER TABLE orders ADD COLUMN balance_applied FLOAT DEFAULT 0.0"))
            db.session.commit()
        if "cancelled_at" not in order_cols:
            db.session.execute(text("ALTER TABLE orders ADD COLUMN cancelled_at TIMESTAMP NULL"))
            db.session.commit()
        if "paid_at" not in order_cols:
            db.session.execute(text("ALTER TABLE orders ADD COLUMN paid_at TIMESTAMP NULL"))
            db.session.commit()
    except Exception as e:
        print(f"[Schema Migration Note]: {e}")
    try:
        from models import ActivityLog
        if ActivityLog.query.count() == 0:
            sample_logs = [
                ActivityLog(
                    action="USER_RATE_LIMIT",
                    module="UserRateLimit",
                    user_id=1,
                    username="admin",
                    ip_address="127.0.0.1",
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                    record_id="1",
                    description="User 'admin' (ID: 1, Role: admin) exceeded activity rate limit on GET /admin/dashboard: 10 per 1 minute",
                    new_data={
                        "status": 429,
                        "error": "Rate limit exceeded",
                        "limit_type": "user_id",
                        "user_id": 1,
                        "username": "admin",
                        "role": "admin",
                        "description": "10 per 1 minute",
                        "ip": "127.0.0.1",
                        "path": "/admin/dashboard",
                        "method": "GET",
                        "retry_after": 60
                    }
                ),
                ActivityLog(
                    action="IP_RATE_LIMIT",
                    module="IpRateLimit",
                    user_id=None,
                    username="Anonymous",
                    ip_address="127.0.0.1",
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                    record_id=None,
                    description="IP '127.0.0.1' exceeded rate limit on POST /admin/login: 5 per 1 minute",
                    new_data={
                        "status": 429,
                        "error": "Rate limit exceeded",
                        "limit_type": "ip",
                        "user_id": None,
                        "username": "Anonymous",
                        "description": "5 per 1 minute",
                        "ip": "127.0.0.1",
                        "path": "/admin/login",
                        "method": "POST",
                        "retry_after": 60
                    }
                ),
                ActivityLog(
                    action="500_INTERNAL_ERROR",
                    module="Error500",
                    user_id=None,
                    username="Anonymous",
                    ip_address="127.0.0.1",
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    record_id=None,
                    description="HTTP 500 ZeroDivisionError on GET /test500: division by zero",
                    new_data={
                        "status": 500,
                        "error_type": "ZeroDivisionError",
                        "message": "division by zero",
                        "path": "/test500",
                        "method": "GET",
                        "ip": "127.0.0.1",
                        "user_id": None,
                        "username": "Anonymous",
                        "role": None
                    }
                ),
            ]
            for item in sample_logs:
                db.session.add(item)
            db.session.commit()
    except Exception:
        db.session.rollback()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(debug=True, host="0.0.0.0", port=port)
