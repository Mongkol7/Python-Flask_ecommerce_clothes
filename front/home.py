from flask import render_template
from product import products
from . import front_bp

@front_bp.route("/")
def home():
    return render_template(
        "front/home.html",
        products=products[:4],
        featured_products=products[4:8],
    )
