from flask import abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy import text
from werkzeug.security import check_password_hash
from extensions import db, limiter
from helpers import is_failed_login, is_ip_login_banned
from . import admin_bp


@admin_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["GET"])
@limiter.limit("5 per minute", methods=["POST"], deduct_when=is_failed_login)
def admin_login():
    ban_remaining = is_ip_login_banned()
    if ban_remaining > 0:
        abort(429, description=f"Too many login attempts. You are temporarily blocked. Please wait {ban_remaining} seconds before trying again.")

    module = "login"
    if request.method == "POST":
        form = request.form
        username = (form.get("username") or form.get("identifier") or "").strip()
        password = form.get("password", "")

        # Query user by username or email using raw SQL
        sql = text("SELECT * FROM user WHERE username = :username OR email = :username")
        user = db.session.execute(sql, {"username": username}).fetchone()

        if user:
            # Verify password with check_password_hash
            if check_password_hash(user.password, password):
                # Ensure only admins can log into the Admin portal
                if user.role != "admin":
                    flash("Access denied. This portal is for administrators only.", "error")
                    res = redirect(url_for("admin_bp.admin_login", next=request.args.get("next")))
                    res.is_failed_login = True
                    return res

                session["is_login"] = True
                session["user_id"] = user.id
                session["username"] = user.username
                session["role"] = user.role
                session["profile"] = user.profile
                session.permanent = True

                raw_next = request.args.get("next") or request.form.get("next")
                if not raw_next or str(raw_next).strip().lower() in ["none", "null", "", "undefined"] or not str(raw_next).startswith("/"):
                    next_url = url_for("admin_bp.dashboard")
                else:
                    next_url = raw_next
                return redirect(next_url)
            else:
                flash("Invalid username or password.", "error")
                res = redirect(url_for("admin_bp.admin_login", next=request.args.get("next")))
                res.is_failed_login = True
                return res
        else:
            flash("Invalid username or password.", "error")
            res = redirect(url_for("admin_bp.admin_login", next=request.args.get("next")))
            res.is_failed_login = True
            return res

    if session.get("is_login"):
        if session.get("role") == "admin":
            return redirect(url_for("admin_bp.dashboard"))
        else:
            return redirect(url_for("front_bp.home"))

    return render_template(
        "admin/login.html",
        module=module,
        user_type="admin",
        title="Admin Login",
        kicker="Secure Admin Portal",
        portal_name="Admin",
        subtitle="Sign in to manage products, orders, and users",
        btn_text="Sign In to Dashboard",
    )


@admin_bp.route("/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("front_bp.home"))
