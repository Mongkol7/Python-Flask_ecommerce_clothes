import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import html
#RUN: python app.py --debug
from flask import Flask, abort, make_response, redirect, render_template, request, url_for
from markupsafe import Markup, escape

from product import (
    get_cart_items,
    get_product_by_id,
    get_products_by_category,
    get_related_products,
    products,
    search_products,
)


app = Flask(__name__)

CART_COOKIE_NAME = "cart"
TELEGRAM_BOT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID_ENV = "TELEGRAM_CHAT_ID"
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""


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


def load_cart():
    cart_cookie = request.cookies.get(CART_COOKIE_NAME, "[]")

    try:
        cart = json.loads(cart_cookie)
    except json.JSONDecodeError:
        return []

    if not isinstance(cart, list):
        return []

    clean_cart = []
    for item in cart:
        if not isinstance(item, dict):
            continue

        try:
            product_id = int(item.get("id"))
            qty = int(item.get("qty", 1))
        except (TypeError, ValueError):
            continue

        if qty > 0:
            clean_cart.append({"id": product_id, "qty": qty})

    return clean_cart


def save_cart(response, cart):
    response.set_cookie(
        CART_COOKIE_NAME,
        json.dumps(cart),
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        samesite="Lax",
    )
    return response


def add_to_cart(cart, product_id):
    for item in cart:
        if item["id"] == product_id:
            item["qty"] += 1
            return cart

    cart.append({"id": product_id, "qty": 1})
    return cart


def update_cart_item(cart, product_id, action):
    updated_cart = []

    for item in cart:
        if item["id"] != product_id:
            updated_cart.append(item)
            continue

        if action == "plus":
            item["qty"] += 1
            updated_cart.append(item)
        elif action == "minus" and item["qty"] > 1:
            item["qty"] -= 1
            updated_cart.append(item)
        elif action == "remove":
            continue

    return updated_cart


def format_order_for_telegram(order_info):
    shipping = order_info["shipping"]
    lines = [
        "<b>New MK7 Order</b>",
        "",
        "<b>Customer</b>",
        f"Name: {html.escape(shipping['full_name'])}",
        f"Phone: {html.escape(shipping['phone'])}",
        f"Email: {html.escape(shipping['email'])}",
        "",
        "<b>Shipping</b>",
        f"Address: {html.escape(shipping['address'])}",
        f"City: {html.escape(shipping['city'])}",
        f"Zip: {html.escape(shipping['zip_code'])}",
    ]

    if shipping["note"]:
        lines.append(f"Note: {html.escape(shipping['note'])}")

    lines.extend(
        [
            "",
            "<b>Payment</b>",
            f"Method: {html.escape(order_info['payment_method'])}",
            "",
            "<b>Items</b>",
        ]
    )

    for item in order_info["items"]:
        title = html.escape(item["title"])
        lines.append(
            f"- {title} x {item['qty']} | "
            f"${item['price']:.2f} each | ${item['subtotal']:.2f}"
        )

    lines.extend(
        [
            "",
            f"<b>Total: ${order_info['total']:.2f}</b>",
        ]
    )

    return "\n".join(lines)


def send_order_to_telegram(order_info):
    configured_bot_token = TELEGRAM_BOT_TOKEN.strip()
    if not configured_bot_token and ":" in TELEGRAM_BOT_TOKEN_ENV:
        configured_bot_token = TELEGRAM_BOT_TOKEN_ENV.strip()

    bot_token = (
        os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        or os.environ.get(TELEGRAM_BOT_TOKEN_ENV, "").strip()
        or configured_bot_token
    )
    chat_id = (
        os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        or os.environ.get(TELEGRAM_CHAT_ID_ENV, "").strip()
        or TELEGRAM_CHAT_ID.strip()
    )

    if not bot_token:
        return False, "Missing Telegram bot token."

    if not chat_id:
        return False, "Missing Telegram chat ID."

    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": format_order_for_telegram(order_info),
            "parse_mode": "HTML",
        }
    ).encode("utf-8")
    request_data = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=payload,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request_data, timeout=10) as response:
            response_body = response.read().decode("utf-8")
            telegram_response = json.loads(response_body)

            if telegram_response.get("ok"):
                return True, ""

            description = telegram_response.get("description", "Unknown Telegram error.")
            return False, description
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")

        try:
            error_data = json.loads(error_body)
            description = error_data.get("description", error_body)
        except json.JSONDecodeError:
            description = error_body

        return False, f"Telegram HTTP {error.code}: {description}"
    except urllib.error.URLError as error:
        return False, f"Telegram network error: {error.reason}"
    except TimeoutError:
        return False, "Telegram request timed out."


@app.context_processor
def inject_cart_count():
    cart_count = len({item["id"] for item in load_cart()})
    return {"cart_count": cart_count}


@app.route("/")
def home():
    return render_template(
        "home.html",
        products=products[:4],
        featured_products=products[4:8],
    )


@app.route("/product")
def product_list():
    return render_template(
        "product.html",
        products=products,
        category_sections=get_products_by_category(),
    )


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()

    if not query:
        return redirect(url_for("product_list"))

    matched_products = search_products(query)

    return render_template(
        "search.html",
        query=query,
        products=matched_products,
    )


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = get_product_by_id(product_id)

    if product is None:
        abort(404)

    related_products = get_related_products(product_id)
    return render_template(
        "product-detail.html",
        product=product,
        related_products=related_products,
    )


@app.route("/product-detail/<int:product_id>")
def old_product_detail(product_id):
    return product_detail(product_id)


@app.route("/cart")
def cart():
    cart_data = load_cart()
    product_id = request.args.get("product_id", type=int)

    if product_id is not None:
        product = get_product_by_id(product_id)
        if product is None:
            abort(404)

        cart_data = add_to_cart(cart_data, product_id)
        response = make_response(redirect(url_for("cart")))
        return save_cart(response, cart_data)

    cart_items = get_cart_items(cart_data)
    total = sum(item["price"] * item["qty"] for item in cart_items)

    return render_template("cart.html", cart_items=cart_items, total=total)


@app.route("/cart/update", methods=["POST"])
def cart_update():
    product_id = request.form.get("product_id", type=int)
    action = request.form.get("action")

    if product_id is None or action not in {"plus", "minus", "remove"}:
        abort(400)

    cart_data = load_cart()
    cart_data = update_cart_item(cart_data, product_id, action)

    response = make_response(redirect(url_for("cart")))
    return save_cart(response, cart_data)


@app.route("/checkout")
def checkout():
    cart_items = get_cart_items(load_cart())
    total = sum(item["price"] * item["qty"] for item in cart_items)
    return render_template(
        "checkout.html",
        cart_items=cart_items,
        subtotal=total,
        total=total,
    )


@app.post("/payment")
def payment():
    cart_data = load_cart()
    cart_items = get_cart_items(cart_data)

    if not cart_items:
        return redirect(url_for("cart"))

    subtotal = sum(item["price"] * item["qty"] for item in cart_items)
    shipping_info = {
        "full_name": request.form.get("full_name", "").strip(),
        "phone": request.form.get("phone", "").strip(),
        "email": request.form.get("email", "").strip(),
        "address": request.form.get("address", "").strip(),
        "city": request.form.get("city", "").strip(),
        "zip_code": request.form.get("zip_code", "").strip(),
        "note": request.form.get("note", "").strip(),
    }
    order_info = {
        "shipping": shipping_info,
        "payment_method": request.form.get("payment_method", "qr_payment"),
        "cart_cookie": cart_data,
        "items": cart_items,
        "subtotal": subtotal,
        "total": subtotal,
    }
    telegram_sent, telegram_error = send_order_to_telegram(order_info)

    response = make_response(
        render_template(
            "checkout.html",
            cart_items=cart_items,
            subtotal=subtotal,
            total=subtotal,
            checkout_success=True,
            order_info=order_info,
            telegram_sent=telegram_sent,
            telegram_error=telegram_error,
        )
    )
    response.delete_cookie(CART_COOKIE_NAME)
    return response


if __name__ == "__main__":
    app.run(debug=True)
