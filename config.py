import os
from datetime import timedelta

# Load local .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Database Configuration: SQLite default, supports PostgreSQL if DATABASE_URL is set
    raw_db_url = os.environ.get("DATABASE_URL", "sqlite:///mydb.sqlite3")
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security & Session Configuration
    SECRET_KEY = os.environ.get("SECRET_KEY", "mk7-fashion-secret-key-2026")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "mk7-luxury-fashion-jwt-auth-secret-key-2026-secure-32bytes")
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=1440)  # 24 hours

    # Upload Folders Configuration
    UPLOAD_USER_FOLDER = os.path.join(BASE_DIR, "static", "image", "user")
    UPLOAD_PRODUCT_FOLDER = os.path.join(BASE_DIR, "static", "image", "product")
    UPLOAD_BRAND_FOLDER = os.path.join(BASE_DIR, "static", "image", "brand")
    UPLOAD_CATEGORY_FOLDER = os.path.join(BASE_DIR, "static", "image", "category")
    UPLOAD_CAROUSEL_FOLDER = os.path.join(BASE_DIR, "static", "image", "carousel")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

    # Bakong KHQR Payment Configuration (National Bank of Cambodia)
    BAKONG_TOKEN = os.environ.get(
        "BAKONG_TOKEN",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiNDBiYmExZTVjOGFiNDY4MiJ9LCJpYXQiOjE3OTMyNjU3NzgsImV4cCI6MTgwMTA0MTc3OH0.iPElLtB2AStldmPmhYtkW8DlVe50n8g0IWrqdNOyUQ8"
    )
    BAKONG_ACCOUNT_ID = os.environ.get("BAKONG_ACCOUNT_ID", "thoeung_sereymongkol@bkrt")
    BAKONG_MERCHANT_NAME = os.environ.get("BAKONG_MERCHANT_NAME", "MK7 LUXURY STORE")
    BAKONG_MERCHANT_CITY = os.environ.get("BAKONG_MERCHANT_CITY", "Phnom Penh")
    BAKONG_CURRENCY = os.environ.get("BAKONG_CURRENCY", "KHR")
    BAKONG_PHONE_NUMBER = os.environ.get("BAKONG_PHONE_NUMBER", "017420051")
    BAKONG_STORE_LABEL = os.environ.get("BAKONG_STORE_LABEL", "Cashier-01")
    BAKONG_TERMINAL_LABEL = os.environ.get("BAKONG_TERMINAL_LABEL", "POS-01")
    KHR_RATE = float(os.environ.get("KHR_RATE", "4000"))  # 1 USD = 4,000 KHR

    # Telegram Order & Security Alert Integration
    CART_COOKIE_NAME = "cart"
    TELEGRAM_BOT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
    TELEGRAM_CHAT_ID_ENV = "TELEGRAM_CHAT_ID"
    TELEGRAM_BOT_TOKEN = "8731861019:AAGvUklnjOPIN2E0cfF8k5mLJvxpJfwg1aY"
    TELEGRAM_CHAT_ID = "@SV26_Shop"
