import os
from flask import abort, redirect, render_template, request, url_for, flash
from config import Config
from extensions import db, limiter
from models.category import Category
from helpers import login_required, admin_user_id_key, log_activity
from upload_service import save_uploaded_image
from . import admin_bp


@admin_bp.route("/categories")
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def categories():
    module = "categories"
    search_query = request.args.get("search", "").strip()
    query = Category.query

    if search_query:
        term = f"%{search_query}%"
        query = query.filter((Category.name.ilike(term)) | (Category.description.ilike(term)))

    all_categories = query.order_by(Category.name.asc()).all()
    return render_template(
        "admin/category/index.html",
        module=module,
        categories=all_categories,
        search_query=search_query,
    )


@admin_bp.route("/categories/add", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def category_add():
    module = "categories"
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip() or name.lower().replace(" ", "-")
        description = request.form.get("description", "").strip()
        image_file = request.files.get("image")

        if not name:
            flash("Category name is required.", "error")
            return render_template("admin/category/add.html", module=module)

        # Check unique
        if Category.query.filter((Category.name == name) | (Category.slug == slug)).first():
            flash("Category with this name or slug already exists.", "error")
            return render_template("admin/category/add.html", module=module)

        image_path = None
        if image_file and image_file.filename:
            saved_filename = save_uploaded_image(
                image_file,
                upload_folder=Config.UPLOAD_CATEGORY_FOLDER,
                allowed_extensions=Config.ALLOWED_EXTENSIONS,
                prefix="cat",
            )
            if saved_filename:
                image_path = f"/static/image/category/{saved_filename}"

        cat = Category(name=name, slug=slug, description=description, image=image_path)
        db.session.add(cat)
        db.session.commit()

        flash(f"Category '{cat.name}' created successfully.", "success")
        return redirect(url_for("admin_bp.categories"))

    return render_template("admin/category/add.html", module=module)


@admin_bp.route("/categories/edit/<int:cat_id>", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def category_edit(cat_id):
    module = "categories"
    cat = Category.query.get(cat_id)
    if not cat:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip() or name.lower().replace(" ", "-")
        description = request.form.get("description", "").strip()
        image_file = request.files.get("image")

        if not name:
            flash("Category name is required.", "error")
            return render_template("admin/category/edit.html", module=module, category=cat)

        cat.name = name
        cat.slug = slug
        cat.description = description

        if image_file and image_file.filename:
            saved_filename = save_uploaded_image(
                image_file,
                upload_folder=Config.UPLOAD_CATEGORY_FOLDER,
                allowed_extensions=Config.ALLOWED_EXTENSIONS,
                prefix="cat",
            )
            if saved_filename:
                cat.image = f"/static/image/category/{saved_filename}"

        db.session.commit()
        flash(f"Category '{cat.name}' updated successfully.", "success")
        return redirect(url_for("admin_bp.categories"))

    return render_template("admin/category/edit.html", module=module, category=cat)


@admin_bp.post("/categories/delete/<int:cat_id>")
@login_required
def category_delete(cat_id):
    cat = Category.query.get(cat_id)
    if not cat:
        return {"success": False, "message": "Category not found."}, 404

    cat_name = cat.name
    db.session.delete(cat)
    db.session.commit()
    return {"success": True, "message": f"Category '{cat_name}' deleted successfully."}
