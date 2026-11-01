import os
from flask import abort, redirect, render_template, request, url_for, flash
from config import Config
from extensions import db, limiter
from models.brand import Brand
from helpers import login_required, admin_user_id_key, log_activity
from upload_service import save_uploaded_image
from . import admin_bp


@admin_bp.route("/brands")
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def brands():
    module = "brands"
    search_query = request.args.get("search", "").strip()
    query = Brand.query

    if search_query:
        term = f"%{search_query}%"
        query = query.filter((Brand.name.ilike(term)) | (Brand.description.ilike(term)))

    all_brands = query.order_by(Brand.name.asc()).all()
    return render_template(
        "admin/brand/index.html",
        module=module,
        brands=all_brands,
        search_query=search_query,
    )


@admin_bp.route("/brands/add", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def brand_add():
    module = "brands"
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip() or name.lower().replace(" ", "-")
        description = request.form.get("description", "").strip()
        website = request.form.get("website", "").strip()
        logo_file = request.files.get("logo")

        if not name:
            flash("Brand name is required.", "error")
            return render_template("admin/brand/add.html", module=module)

        if Brand.query.filter((Brand.name == name) | (Brand.slug == slug)).first():
            flash("Brand with this name or slug already exists.", "error")
            return render_template("admin/brand/add.html", module=module)

        logo_path = None
        if logo_file and logo_file.filename:
            saved_filename = save_uploaded_image(
                logo_file,
                upload_folder=Config.UPLOAD_BRAND_FOLDER,
                allowed_extensions=Config.ALLOWED_EXTENSIONS,
                prefix="brand",
            )
            if saved_filename:
                logo_path = f"/static/image/brand/{saved_filename}"

        b = Brand(name=name, slug=slug, description=description, logo=logo_path, website=website)
        db.session.add(b)
        db.session.commit()

        flash(f"Brand '{b.name}' created successfully.", "success")
        return redirect(url_for("admin_bp.brands"))

    return render_template("admin/brand/add.html", module=module)


@admin_bp.route("/brands/edit/<int:brand_id>", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def brand_edit(brand_id):
    module = "brands"
    b = Brand.query.get(brand_id)
    if not b:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip() or name.lower().replace(" ", "-")
        description = request.form.get("description", "").strip()
        website = request.form.get("website", "").strip()
        logo_file = request.files.get("logo")

        if not name:
            flash("Brand name is required.", "error")
            return render_template("admin/brand/edit.html", module=module, brand=b)

        b.name = name
        b.slug = slug
        b.description = description
        b.website = website

        if logo_file and logo_file.filename:
            saved_filename = save_uploaded_image(
                logo_file,
                upload_folder=Config.UPLOAD_BRAND_FOLDER,
                allowed_extensions=Config.ALLOWED_EXTENSIONS,
                prefix="brand",
            )
            if saved_filename:
                b.logo = f"/static/image/brand/{saved_filename}"

        db.session.commit()
        flash(f"Brand '{b.name}' updated successfully.", "success")
        return redirect(url_for("admin_bp.brands"))

    return render_template("admin/brand/edit.html", module=module, brand=b)


@admin_bp.post("/brands/delete/<int:brand_id>")
@login_required
def brand_delete(brand_id):
    b = Brand.query.get(brand_id)
    if not b:
        return {"success": False, "message": "Brand not found."}, 404

    brand_name = b.name
    db.session.delete(b)
    db.session.commit()
    return {"success": True, "message": f"Brand '{brand_name}' deleted successfully."}
