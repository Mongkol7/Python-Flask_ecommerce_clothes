from flask import request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import db
from models.users import User
from . import api_bp
from .jwt_auth import create_access_token, jwt_required, g


@api_bp.route("/auth/login", methods=["POST"])
@api_bp.route("/login", methods=["POST"])
def api_login():
    """
    Authenticate user and issue a JWT access token for API access.
    Accepts JSON: {"username": "admin", "password": "password123"} or {"email": "..."}
    """
    data = request.get_json(silent=True) or {}
    identifier = (data.get("username") or data.get("email") or data.get("identifier") or "").strip()
    password = data.get("password", "")

    if not identifier or not password:
        return jsonify({
            "success": False,
            "error": "Bad Request",
            "message": "Username/email and password are required.",
        }), 400

    # Query user by username or email
    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({
            "success": False,
            "error": "Unauthorized",
            "message": "Invalid username or password.",
        }), 401

    token = create_access_token(user, expires_in_days=1)

    return jsonify({
        "success": True,
        "message": "Authentication successful.",
        "token": token,
        "access_token": token,
        "token_type": "Bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "profile": user.profile,
        },
    }), 200


@api_bp.route("/auth/register", methods=["POST"])
@api_bp.route("/register", methods=["POST"])
def api_register():
    """
    Register a new customer account via API and return a JWT access token.
    Accepts JSON: {"username": "...", "email": "...", "password": "..."}
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({
            "success": False,
            "error": "Bad Request",
            "message": "Username, email, and password are required.",
        }), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({
            "success": False,
            "error": "Conflict",
            "message": "Username or email is already registered.",
        }), 409

    hashed_pw = generate_password_hash(password)
    new_user = User(
        username=username,
        email=email,
        password=hashed_pw,
        role="user",
    )
    db.session.add(new_user)
    db.session.commit()

    token = create_access_token(new_user, expires_in_days=1)

    return jsonify({
        "success": True,
        "message": "Account created successfully.",
        "token": token,
        "token_type": "Bearer",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role,
            "profile": new_user.profile,
        },
    }), 201


@api_bp.route("/auth/me", methods=["GET"])
@jwt_required
def api_me():
    """
    Returns the currently authenticated user's profile claims from the verified JWT.
    """
    user_id = g.jwt_user.get("user_id")
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "profile": user.profile,
        },
    }), 200
