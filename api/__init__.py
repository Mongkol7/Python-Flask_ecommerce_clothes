from flask import Blueprint

api_bp = Blueprint("api_bp", __name__)

from . import auth
from . import user
from . import category
from . import brand
from . import product
from . import order
