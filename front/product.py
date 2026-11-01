from flask import abort, redirect, render_template, request, url_for
from product import (
    get_product_by_id,
    get_products_by_category,
    get_related_products,
    products,
    search_products,
)
from . import front_bp


@front_bp.route("/product")
def product_list():
    selected_category = request.args.get("category", "").strip().lower()
    return render_template(
        "front/product.html",
        products=products,
        category_sections=get_products_by_category(),
        selected_category=selected_category,
    )


@front_bp.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect(url_for("front_bp.product_list"))

    matched_products = search_products(query)
    return render_template(
        "front/search.html",
        query=query,
        products=matched_products,
    )


@front_bp.route("/product/<int:product_id>")#int for accept only integer ID
def product_detail(product_id):
    product = get_product_by_id(product_id)
    if product is None:
        abort(404)

    related_products = get_related_products(product_id)
    return render_template(
        "front/product-detail.html",
        product=product,
        related_products=related_products,
    )


@front_bp.route("/product-detail/<int:product_id>")
def old_product_detail(product_id):
    return product_detail(product_id)
