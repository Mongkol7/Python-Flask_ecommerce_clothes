from flask import abort, jsonify, make_response, redirect, render_template, request, url_for
from product import get_cart_items, get_product_by_id
from helpers import add_to_cart, load_cart, save_cart, update_cart_item
from extensions import csrf
from . import front_bp


@front_bp.route("/cart")
def cart():
    cart_data = load_cart()
    product_id = request.args.get("product_id", type=int)

    if product_id is not None:
        product = get_product_by_id(product_id)
        if product is None:
            abort(404)

        current_in_cart = sum(item["qty"] for item in cart_data if item["id"] == product_id)
        available_stock = product.get("stock", 50)

        # Only add if available stock allows
        if current_in_cart < available_stock:
            cart_data = add_to_cart(cart_data, product_id)

        response = make_response(redirect(url_for("front_bp.cart")))
        return save_cart(response, cart_data)

    cart_items = get_cart_items(cart_data)
    total = sum(item["price"] * item["qty"] for item in cart_items)

    return render_template("front/cart.html", cart_items=cart_items, total=total)


@front_bp.post("/cart/add-ajax")
@csrf.exempt
def cart_add_ajax():
    """
    Real-time AJAX endpoint called when customer clicks add to cart.
    Validates inventory stock and returns updated remaining stock and cart count.
    """
    payload = request.get_json(silent=True) or request.form
    product_id = payload.get("product_id")

    if not product_id:
        return jsonify({"success": False, "message": "Product ID is required."}), 400

    try:
        product_id = int(product_id)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid Product ID."}), 400

    product = get_product_by_id(product_id)
    if not product:
        return jsonify({"success": False, "message": "Product not found."}), 404

    cart_data = load_cart()
    current_in_cart = sum(item["qty"] for item in cart_data if item["id"] == product_id)
    stock = product.get("stock", 0)

    if current_in_cart >= stock:
        return jsonify({
            "success": False,
            "message": f"Cannot add more. Only {stock} units in stock.",
            "remaining_stock": max(0, stock - current_in_cart),
            "stock": stock,
        }), 400

    cart_data = add_to_cart(cart_data, product_id)
    new_in_cart = current_in_cart + 1
    remaining_stock = max(0, stock - new_in_cart)
    total_cart_count = len({item["id"] for item in cart_data})

    response = make_response(jsonify({
        "success": True,
        "message": f"Added '{product['title']}' to your bag.",
        "product_id": product_id,
        "title": product["title"],
        "stock": stock,
        "remaining_stock": remaining_stock,
        "in_cart": new_in_cart,
        "cart_count": total_cart_count,
    }))

    return save_cart(response, cart_data)


@front_bp.route("/cart/update", methods=["POST"])
def cart_update():
    product_id = request.form.get("product_id", type=int)
    action = request.form.get("action")

    if product_id is None or action not in {"plus", "minus", "remove"}:
        abort(400)

    cart_data = load_cart()
    product = get_product_by_id(product_id)
    stock = product.get("stock", 50) if product else 50
    current_in_cart = sum(item["qty"] for item in cart_data if item["id"] == product_id)

    # Check stock before incrementing
    if action == "plus" and current_in_cart >= stock:
        response = make_response(redirect(url_for("front_bp.cart")))
        return response

    cart_data = update_cart_item(cart_data, product_id, action)

    response = make_response(redirect(url_for("front_bp.cart")))
    return save_cart(response, cart_data)
