from flask import Blueprint

admin_bp = Blueprint("admin_bp", __name__, template_folder="templates")

from . import auth
from . import dashboard
from . import user
from . import activity_log
from . import category
from . import brand
from . import product
from . import order
