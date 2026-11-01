from flask import abort, redirect, render_template, request, session, url_for
from sqlalchemy import text
from werkzeug.security import generate_password_hash
from config import Config
from extensions import db, limiter
from models import User
from helpers import login_required, save_user_image, admin_user_id_key
from . import admin_bp


@admin_bp.route("/users")
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def users():
    module = "users"
    sql = text("SELECT * FROM user")
    result = db.session.execute(sql)
    rows = [dict(row._mapping) for row in result]
    return render_template("admin/user/user.html", module=module, users=rows)


@admin_bp.route("/users/add", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def user_add():
    module = "users"
    if request.method == "POST":
        username = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        hashed_password = generate_password_hash(password)
        role = request.form.get("role", "user").strip()
        image = request.files.get("image")

        # 1. Insert user first (flushed to obtain user ID)
        u = User(username=username, email=email, password=hashed_password, role=role, profile=None)
        db.session.add(u)
        db.session.flush()  # flush to get the user id immediately

        # 2. Save user image in 2 versions ({id}_org_{filename} and {id}_thum_{filename})
        if image and image.filename:
            saved = save_user_image(
                image,
                user_id=u.id,
                upload_folder=Config.UPLOAD_USER_FOLDER,
                allowed_extensions=Config.ALLOWED_EXTENSIONS,
                scale=0.8,
            )
            if saved:
                u.profile = saved["filename"]

        db.session.commit()
        return redirect(url_for("admin_bp.users"))
    return render_template("admin/user/add.html", module=module)


@admin_bp.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def user_edit(user_id):
    module = "users"
    sql = text("SELECT * FROM user WHERE id = :id")
    result = db.session.execute(sql, {"id": user_id})
    row = result.fetchone()
    if row is None:
        abort(404)
    user = dict(row._mapping)

    if request.method == "POST":
        user_obj = db.session.get(User, user_id)
        if user_obj:
            old_data = {"id": user_obj.id, "username": user_obj.username, "email": user_obj.email, "role": user_obj.role}

            user_obj.username = request.form.get("name", "").strip()
            user_obj.email = request.form.get("email", "").strip()
            user_obj.role = request.form.get("role", "user").strip()
            password = request.form.get("password", "").strip()
            if password:
                user_obj.password = generate_password_hash(password)

            image = request.files.get("image")
            if image and image.filename:
                saved = save_user_image(
                    image,
                    user_id=user_obj.id,
                    upload_folder=Config.UPLOAD_USER_FOLDER,
                    allowed_extensions=Config.ALLOWED_EXTENSIONS,
                    scale=0.8,
                )
                if saved:
                    user_obj.profile = saved["filename"]

            db.session.commit()

            # If current logged in admin edited their own profile, sync session
            if session.get("user_id") == user_obj.id:
                session["username"] = user_obj.username
                session["role"] = user_obj.role
                session["profile"] = user_obj.profile
        return redirect(url_for("admin_bp.users"))
    return render_template("admin/user/edit.html", module=module, user=user)


@admin_bp.post("/users/delete/<int:user_id>")
@login_required
def user_delete(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return {"success": False, "message": "User not found."}, 404
    db.session.delete(user)
    db.session.commit()
    return {"success": True, "message": f"User {user_id} deleted."}
