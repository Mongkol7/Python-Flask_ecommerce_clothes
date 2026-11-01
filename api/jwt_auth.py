import jwt
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import current_app, request, g, jsonify
from models.users import User


def get_jwt_secret():
    """Returns the secret key used for JWT signing."""
    return current_app.config.get("JWT_SECRET_KEY") or current_app.config.get(
        "SECRET_KEY", "mk7-fashion-secret-key-2026"
    )


def create_access_token(user, expires_in_days=1):
    """
    Generates a signed JWT token containing user identity and role claims.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "profile": user.profile,
        "iat": now,
        "exp": now + timedelta(days=expires_in_days),
    }
    token = jwt.encode(payload, get_jwt_secret(), algorithm="HS256")
    return token


def decode_access_token(token):
    """
    Decodes and verifies a JWT token. Returns payload dict or error dict.
    """
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired", "code": "TOKEN_EXPIRED"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token", "code": "INVALID_TOKEN"}
    except Exception as e:
        return {"error": f"Token verification failed: {str(e)}", "code": "TOKEN_ERROR"}


def get_token_from_header():
    """Extracts bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header:
        # Fallback query param for testing if needed
        return request.args.get("token")
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    if len(parts) == 1:
        return parts[0]
    return None


def jwt_required(fn):
    """
    Decorator to protect API routes with JWT authentication.
    Requires 'Authorization: Bearer <token>' header.
    Injects decoded user payload into g.jwt_user and request.jwt_user.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = get_token_from_header()
        if not token:
            return jsonify({
                "success": False,
                "error": "Unauthorized",
                "message": "Authentication required. Missing Bearer token in 'Authorization: Bearer <token>' header.",
            }), 401

        decoded = decode_access_token(token)
        if "error" in decoded:
            return jsonify({
                "success": False,
                "error": "Unauthorized",
                "message": decoded["error"],
                "code": decoded.get("code"),
            }), 401

        g.jwt_user = decoded
        user_id = decoded.get("user_id")
        g.current_user = User.query.get(user_id) if user_id else None
        request.jwt_user = decoded
        return fn(*args, **kwargs)

    return wrapper


def jwt_admin_required(fn):
    """
    Decorator to protect API routes with JWT authentication AND admin role enforcement.
    Requires 'Authorization: Bearer <token>' header where role == 'admin'.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = get_token_from_header()
        if not token:
            return jsonify({
                "success": False,
                "error": "Unauthorized",
                "message": "Authentication required. Missing Bearer token in 'Authorization: Bearer <token>' header.",
            }), 401

        decoded = decode_access_token(token)
        if "error" in decoded:
            return jsonify({
                "success": False,
                "error": "Unauthorized",
                "message": decoded["error"],
                "code": decoded.get("code"),
            }), 401

        if decoded.get("role") != "admin":
            return jsonify({
                "success": False,
                "error": "Forbidden",
                "message": "Admin privileges required to perform this action.",
            }), 403

        g.jwt_user = decoded
        user_id = decoded.get("user_id")
        g.current_user = User.query.get(user_id) if user_id else None
        request.jwt_user = decoded
        return fn(*args, **kwargs)

    return wrapper
