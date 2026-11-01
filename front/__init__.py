from flask import Blueprint

front_bp = Blueprint("front_bp", __name__)

from . import home, product, cart, checkout, customer
