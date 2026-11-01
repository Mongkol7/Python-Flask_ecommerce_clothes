import os
from flask import abort, redirect, render_template, request, url_for, flash
from config import Config
from extensions import db, limiter
from models.product import Product
from models.category import Category
from models.brand import Brand
from helpers import login_required, admin_user_id_key, log_activity
from upload_service import save_uploaded_image
from . import admin_bp


@admin_bp.route("/products")
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def products():
    module = "products"
    search_query = request.args.get("search", "").strip()
    category_id = request.args.get("category", "").strip()
    brand_id = request.args.get("brand", "").strip()
    gender = request.args.get("gender", "").strip()

    query = Product.query

    if search_query:
        term = f"%{search_query}%"
        query = query.filter((Product.title.ilike(term)) | (Product.description.ilike(term)))

    if category_id and category_id.isdigit():
        query = query.filter(Product.category_id == int(category_id))

    if brand_id and brand_id.isdigit():
        query = query.filter(Product.brand_id == int(brand_id))

    if gender:
        query = query.filter(Product.gender == gender)

    all_products = query.order_by(Product.id.desc()).all()
    all_categories = Category.query.order_by(Category.name.asc()).all()
    all_brands = Brand.query.order_by(Brand.name.asc()).all()

    return render_template(
        "admin/product/index.html",
        module=module,
        products=all_products,
        categories=all_categories,
        brands=all_brands,
        search_query=search_query,
        selected_category=category_id,
        selected_brand=brand_id,
        selected_gender=gender,
    )


@admin_bp.route("/products/add", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def product_add():
    module = "products"
    all_categories = Category.query.order_by(Category.name.asc()).all()
    all_brands = Brand.query.order_by(Brand.name.asc()).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        price_val = request.form.get("price", "").strip()
        description = request.form.get("description", "").strip()
        category_id = request.form.get("category_id")
        brand_id = request.form.get("brand_id")
        stock = request.form.get("stock", "50").strip()
        gender = request.form.get("gender", "woman").strip()
        is_featured = bool(request.form.get("is_featured"))

        if not title or not price_val:
            flash("Product title and price are required.", "error")
            return render_template(
                "admin/product/add.html",
                module=module,
                categories=all_categories,
                brands=all_brands,
            )

        try:
            price = float(price_val)
        except ValueError:
            flash("Invalid price value.", "error")
            return render_template(
                "admin/product/add.html",
                module=module,
                categories=all_categories,
                brands=all_brands,
            )

        main_image_file = request.files.get("image")
        image_path = "/static/image/product/Man_Brown01.jpg"

        if main_image_file and main_image_file.filename:
            saved_filename = save_uploaded_image(
                main_image_file,
                upload_folder=Config.UPLOAD_PRODUCT_FOLDER,
                allowed_extensions=Config.ALLOWED_EXTENSIONS,
                prefix="prod",
            )
            if saved_filename:
                image_path = f"/static/image/product/{saved_filename}"

        # Sub images
        sub_images = []
        for key in ["sub_image_1", "sub_image_2"]:
            sub_file = request.files.get(key)
            if sub_file and sub_file.filename:
                saved_sub = save_uploaded_image(
                    sub_file,
                    upload_folder=Config.UPLOAD_PRODUCT_FOLDER,
                    allowed_extensions=Config.ALLOWED_EXTENSIONS,
                    prefix="sub",
                )
                if saved_sub:
                    sub_images.append(f"/static/image/product/{saved_sub}")

        cat_id_int = int(category_id) if category_id and category_id.isdigit() else None
        brand_id_int = int(brand_id) if brand_id and brand_id.isdigit() else None
        stock_int = int(stock) if stock and stock.isdigit() else 50

        p = Product(
            title=title,
            price=price,
            description=description,
            category_id=cat_id_int,
            brand_id=brand_id_int,
            image=image_path,
            sub_images=sub_images,
            stock=stock_int,
            gender=gender,
            is_featured=is_featured,
        )
        db.session.add(p)
        db.session.commit()

        flash(f"Product '{p.title}' created successfully.", "success")
        return redirect(url_for("admin_bp.products"))

    return render_template(
        "admin/product/add.html",
        module=module,
        categories=all_categories,
        brands=all_brands,
    )


@admin_bp.route("/products/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])
def product_edit(product_id):
    module = "products"
    p = Product.query.get(product_id)
    if not p:
        abort(404)

    all_categories = Category.query.order_by(Category.name.asc()).all()
    all_brands = Brand.query.order_by(Brand.name.asc()).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        price_val = request.form.get("price", "").strip()
        description = request.form.get("description", "").strip()
        category_id = request.form.get("category_id")
        brand_id = request.form.get("brand_id")
        stock = request.form.get("stock", "50").strip()
        gender = request.form.get("gender", "woman").strip()
        is_featured = bool(request.form.get("is_featured"))

        if not title or not price_val:
            flash("Product title and price are required.", "error")
            return render_template(
                "admin/product/edit.html",
                module=module,
                product=p,
                categories=all_categories,
                brands=all_brands,
            )

        try:
            p.price = float(price_val)
        except ValueError:
            flash("Invalid price value.", "error")
            return render_template(
                "admin/product/edit.html",
                module=module,
                product=p,
                categories=all_categories,
                brands=all_brands,
            )

        p.title = title
        p.description = description
        p.category_id = int(category_id) if category_id and category_id.isdigit() else None
        p.brand_id = int(brand_id) if brand_id and brand_id.isdigit() else None
        p.stock = int(stock) if stock and stock.isdigit() else p.stock
        p.gender = gender
        p.is_featured = is_featured

        # Main image upload
        main_image_file = request.files.get("image")
        if main_image_file and main_image_file.filename:
            saved_filename = save_uploaded_image(
                main_image_file,
                upload_folder=Config.UPLOAD_PRODUCT_FOLDER,
                allowed_extensions=Config.ALLOWED_EXTENSIONS,
                prefix="prod",
            )
            if saved_filename:
                p.image = f"/static/image/product/{saved_filename}"

        # Additional sub images
        new_subs = p.get_sub_images()
        for idx, key in enumerate(["sub_image_1", "sub_image_2"]):
            sub_file = request.files.get(key)
            if sub_file and sub_file.filename:
                saved_sub = save_uploaded_image(
                    sub_file,
                    upload_folder=Config.UPLOAD_PRODUCT_FOLDER,
                    allowed_extensions=Config.ALLOWED_EXTENSIONS,
                    prefix=f"sub{idx+1}",
                )
                if saved_sub:
                    sub_url = f"/static/image/product/{saved_sub}"
                    if idx < len(new_subs):
                        new_subs[idx] = sub_url
                    else:
                        new_subs.append(sub_url)

        p.set_sub_images(new_subs)
        db.session.commit()

        flash(f"Product '{p.title}' updated successfully.", "success")
        return redirect(url_for("admin_bp.products"))

    return render_template(
        "admin/product/edit.html",
        module=module,
        product=p,
        categories=all_categories,
        brands=all_brands,
    )


@admin_bp.post("/products/delete/<int:product_id>")
@login_required
def product_delete(product_id):
    p = Product.query.get(product_id)
    if not p:
        return {"success": False, "message": "Product not found."}, 404

    prod_title = p.title
    db.session.delete(p)
    db.session.commit()
    return {"success": True, "message": f"Product '{prod_title}' deleted successfully."}
