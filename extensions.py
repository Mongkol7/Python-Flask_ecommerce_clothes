from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,#by defaul, indentify visitor by thier IP address,
    default_limits=["100 per minute", "10000 per day"]
)
cors = CORS()
csrf = CSRFProtect()
