import os
import time
import json
import re
import html
import urllib.parse
import urllib.request
import urllib.error
from functools import wraps
from flask import session, redirect, url_for, flash, request
from markupsafe import Markup, escape
from werkzeug.utils import secure_filename
from PIL import Image
from config import Config

# Global Upload Variables & Helpers
UPLOAD_DIR = Config.UPLOAD_USER_FOLDER
ALLOWED_EXT = Config.ALLOWED_EXTENSIONS

def allowed(name):
    return "." in name and name.rsplit(".", 1)[-1].lower() in ALLOWED_EXT

def allowed_file(filename, allowed_extensions=None):
    if allowed_extensions is None:
        allowed_extensions = Config.ALLOWED_EXTENSIONS
    return "." in filename and filename.rsplit(".", 1)[-1].lower() in allowed_extensions

def save_user_image(
    file,
    user_id,
    upload_folder=None,
    allowed_extensions=None,
    scale=0.8
):
    """
    Saves user image in two versions within the user folder:
      1. Original: {user_id}_org_{filename}
      2. Compressed: {user_id}_thum_{filename} (80% dimension size by Pillow)
    Returns a dict with versioned filenames and the base filename for DB storage.
    """
    if upload_folder is None:
        upload_folder = Config.UPLOAD_USER_FOLDER
    if allowed_extensions is None:
        allowed_extensions = Config.ALLOWED_EXTENSIONS

    if not file or not file.filename:
        return None
    if not allowed_file(file.filename, allowed_extensions):
        return None

    filename = secure_filename(file.filename)
    os.makedirs(upload_folder, exist_ok=True)

    original_filename = f"{user_id}_org_{filename}"
    thumb_filename = f"{user_id}_thum_{filename}"

    original_path = os.path.join(upload_folder, original_filename)
    thumb_path = os.path.join(upload_folder, thumb_filename)

    # Save original image file
    file.save(original_path)

    # Generate compressed thumbnail (80% size) with Pillow
    with Image.open(original_path) as image:
        new_width = max(1, int(image.width * scale))
        new_height = max(1, int(image.height * scale))
        thumb = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        thumb.save(thumb_path)

    return {
        "original": original_filename,
        "thumbnail": thumb_filename,
        "filename": filename,
    }


# Role-Based Route Protection Decorator
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_login"):
            return redirect(url_for("admin_bp.admin_login", next=request.path))
        if session.get("role") != "admin":
            flash("Access denied. Admin privileges required.", "error")
            return redirect(url_for("front_bp.home"))
        return view(*args, **kwargs)
    return wrapped


# Cart Helper Functions
def load_cart():
    cart_cookie = request.cookies.get(Config.CART_COOKIE_NAME, "[]")
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
        Config.CART_COOKIE_NAME,
        json.dumps(cart),
        max_age=60 * 60 * 24 * 30,  # 30 days
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


# Telegram Order Integration Functions
def format_order_for_telegram(order_info):
    shipping = order_info.get("shipping", {})
    payment_method = str(order_info.get("payment_method", "bakong_khqr"))
    if payment_method in ["bakong_khqr", "qr_payment"]:
        gateway_display = "🇰🇭 Bakong KHQR (National Bank of Cambodia)"
    else:
        gateway_display = payment_method.replace("_", " ").title()

    order_num = order_info.get("order_number", "N/A")
    bill_number = order_info.get("bill_number") or order_num
    khqr_md5 = order_info.get("khqr_md5")
    payment_status = order_info.get("payment_status", "Pending Verification")

    from models.activity_log import get_cambodia_now
    cam_time_str = get_cambodia_now().strftime("%Y-%m-%d %I:%M:%S %p")

    lines = [
        "🛒 <b>[NEW ORDER PLACED] MK7 Luxury Storefront</b>",
        "",
        "📋 <b>Order Details:</b>",
        f"• <b>Order Number:</b> <code>{html.escape(str(order_num))}</code>",
        f"• <b>Payment Gateway:</b> <b>{html.escape(gateway_display)}</b>",
        f"• <b>Merchant:</b> {html.escape(Config.BAKONG_MERCHANT_NAME)} (<code>{html.escape(Config.BAKONG_ACCOUNT_ID)}</code>)",
        f"• <b>Bill Reference:</b> <code>{html.escape(str(bill_number))}</code>",
    ]

    if khqr_md5:
        lines.append(f"• <b>KHQR MD5:</b> <code>{html.escape(str(khqr_md5))}</code>")

    lines.extend([
        f"• <b>Payment Status:</b> <b>{html.escape(str(payment_status))}</b>",
        f"• <b>Order Time (PP):</b> <code>{cam_time_str}</code>",
        "",
        "👤 <b>Customer Information:</b>",
        f"• <b>Name:</b> {html.escape(str(shipping.get('full_name', 'N/A')))}",
        f"• <b>Phone:</b> {html.escape(str(shipping.get('phone', 'N/A')))}",
        f"• <b>Email:</b> {html.escape(str(shipping.get('email', 'N/A')))}",
        f"• <b>Shipping Address:</b> {html.escape(str(shipping.get('address', 'N/A')))}, {html.escape(str(shipping.get('city', '')))} {html.escape(str(shipping.get('zip_code', '')))}",
    ])

    if shipping.get("note"):
        lines.append(f"• <b>Customer Note:</b> <i>{html.escape(shipping['note'])}</i>")

    lines.extend([
        "",
        "📦 <b>Purchased Items:</b>",
    ])

    for item in order_info.get("items", []):
        title = html.escape(str(item.get("title", "Product")))
        qty = item.get("qty", 1)
        price = float(item.get("price", 0.0))
        subtotal = float(item.get("subtotal", price * qty))
        lines.append(f"• {title} &times; {qty} ({int(round(price)):,} ៛ / ≈ ${(price/Config.KHR_RATE):.2f}) &rarr; <b>{int(round(subtotal)):,} ៛</b>")

    total_amount = float(order_info.get("total", 0.0))
    usd_equiv = total_amount / Config.KHR_RATE
    lines.extend([
        "",
        f"💰 <b>Total Paid Amount: {int(round(total_amount)):,} ៛ KHR (≈ ${usd_equiv:.2f} USD)</b>",
        "✅ <i>Inventory stock deducted and synchronized.</i>",
    ])

    return "\n".join(lines)


def send_order_to_telegram(order_info):
    configured_bot_token = Config.TELEGRAM_BOT_TOKEN.strip()
    if not configured_bot_token and ":" in Config.TELEGRAM_BOT_TOKEN_ENV:
        configured_bot_token = Config.TELEGRAM_BOT_TOKEN_ENV.strip()

    bot_token = (
        os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        or os.environ.get(Config.TELEGRAM_BOT_TOKEN_ENV, "").strip()
        or configured_bot_token
    )
    chat_id = (
        os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        or os.environ.get(Config.TELEGRAM_CHAT_ID_ENV, "").strip()
        or Config.TELEGRAM_CHAT_ID.strip()
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


def format_order_cancellation_for_telegram(order, user=None, reason=None):
    """
    Builds a structured, human-readable HTML notification for Telegram
    when an order is cancelled by the customer.
    """
    from models.activity_log import get_cambodia_now
    cam_time_str = get_cambodia_now().strftime("%Y-%m-%d %I:%M:%S %p")

    # Customer info resolution
    cust_name = getattr(order, "customer_name", None)
    cust_email = getattr(order, "customer_email", None)
    cust_phone = getattr(order, "customer_phone", None) or "N/A"
    
    uname = None
    uid = getattr(order, "user_id", None)
    if user:
        if isinstance(user, str):
            uname = user
        elif hasattr(user, "username"):
            uname = user.username
            uid = user.id or uid
            cust_name = cust_name or user.username
            cust_email = cust_email or user.email
    elif hasattr(order, "user") and order.user:
        uname = order.user.username
        uid = order.user.id
        cust_name = cust_name or order.user.username
        cust_email = cust_email or order.user.email

    cust_name = cust_name or "Valued Customer"
    cust_email = cust_email or "N/A"
    payment_method = str(getattr(order, "payment_method", "N/A")).replace("_", " ").title()
    order_num = getattr(order, "order_number", "N/A")
    total_amount = float(getattr(order, "total", 0.0))

    lines = [
        "🚫 <b>[ORDER CANCELLED] Customer Order Cancellation</b>",
        "",
        "📋 <b>Order Details:</b>",
        f"• <b>Order Number:</b> <code>{html.escape(str(order_num))}</code>",
        "• <b>Status:</b> ❌ <b>Cancelled</b>",
        f"• <b>Total Amount:</b> <b>${total_amount:.2f}</b>",
        f"• <b>Payment Method:</b> {html.escape(payment_method)}",
        "",
        "👤 <b>Customer Information:</b>",
        f"• <b>Customer Name:</b> {html.escape(str(cust_name))}",
        f"• <b>Email:</b> {html.escape(str(cust_email))}",
        f"• <b>Phone:</b> {html.escape(str(cust_phone))}",
    ]
    if uname or uid:
        lines.append(f"• <b>Account:</b> {html.escape(str(uname or 'User'))} (ID: <code>{html.escape(str(uid or 'N/A'))}</code>)")

    lines.extend([
        "",
        "📦 <b>Restocked Items (Returned to Stock):</b>",
    ])

    items = getattr(order, "items", [])
    if items:
        for item in items:
            title = html.escape(str(getattr(item, "product_title", "Product")))
            qty = getattr(item, "quantity", 1)
            subtotal = float(getattr(item, "subtotal", 0.0))
            lines.append(f"• {title} &times; {qty} (${subtotal:.2f}) &rarr; <i>Restocked</i>")
    else:
        lines.append("• <i>Inventory stock restored to catalog</i>")

    placed_at_str = order.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if getattr(order, "created_at", None) else "N/A"
    reason_text = reason or "Customer cancelled order within the 4-hour cancellation period. Item inventory has been restored."

    lines.extend([
        "",
        "⏱ <b>Incident Timeline:</b>",
        f"• <b>Placed At:</b> <code>{placed_at_str}</code>",
        f"• <b>Cancelled At (Cambodia):</b> <code>{cam_time_str}</code>",
        f"• <b>Action:</b> {html.escape(reason_text)}",
    ])

    return "\n".join(lines)


def send_order_cancellation_to_telegram(order, user=None, reason=None):
    """
    Sends an alert notification to the configured Telegram group/channel
    when a customer cancels their order.
    """
    configured_bot_token = Config.TELEGRAM_BOT_TOKEN.strip()
    if not configured_bot_token and ":" in Config.TELEGRAM_BOT_TOKEN_ENV:
        configured_bot_token = Config.TELEGRAM_BOT_TOKEN_ENV.strip()

    bot_token = (
        os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        or os.environ.get(Config.TELEGRAM_BOT_TOKEN_ENV, "").strip()
        or configured_bot_token
    )
    chat_id = (
        os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        or os.environ.get(Config.TELEGRAM_CHAT_ID_ENV, "").strip()
        or Config.TELEGRAM_CHAT_ID.strip()
    )

    if not bot_token:
        return False, "Missing Telegram bot token."
    if not chat_id:
        return False, "Missing Telegram chat ID."

    message_text = format_order_cancellation_for_telegram(order, user, reason)

    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": message_text,
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
    except Exception as ex:
        return False, str(ex)


_cached_public_ip = None #global variable for caching IP address.

# Get client public IP address:
def get_client_public_ip():
    global _cached_public_ip #for Python to knows that we want to read and write to the variable defined outside the function.
    #Strategy01: check for Proxies & Cloudflare
    #X-Forwarded-For is a header that is used to identify the originating IP address of a client connecting to a web server through an HTTP proxy or load balancer.
    forwarded = request.headers.get("X-Forwarded-For") 
    if forwarded:
        #Take the first IP in the list (X-Forwarded-For) & remove whitespace
        client_ip = forwarded.split(",")[0].strip()
        #filter out localhost(127.0.0.1 is Proxy's IP)
        if client_ip and client_ip not in ("127.0.0.1", "::1", "localhost"):
            return client_ip #return Client IP
    #Strategy02: Direct connect IP(when not using proxy/cloudflare)
    remote = request.remote_addr
    if remote and remote not in ("127.0.0.1", "::1", "localhost"):
        return remote #return Client IP
    #Strategy03: Localhost Fallback for Local Development 
    if _cached_public_ip:#if cached IP is available, return it (cached for performance)
        return _cached_public_ip #return cached IP
    #Strategy04: external service to get public IP(fallback to ipify.org)
    try:
        #for localhost, use ipify(is a free service that returns the public IP address of the client.)
        req = urllib.request.Request(
            "https://api.ipify.org?format=text",
            headers={"User-Agent": "Mozilla/5.0"} #specify user agent to avoid 403 Forbidden Error
        )
        with urllib.request.urlopen(req, timeout=2) as response: #Set timeout to 2 seconds
            public_ip = response.read().decode("utf-8").strip() #Read and decode the response
            if public_ip:
                _cached_public_ip = public_ip #cache the public IP(so future don't have to make any web calls)
                return public_ip #return public IP
    except Exception:
        #do nothing if any error occurs (e.g. network issue, ipify being down, etc.)
        pass

    #If all else fails, return remote IP or localhost
    return remote or "127.0.0.1" 

#The 3 dictionaries: to temporarily stores information aboutIP addresess that are temporarily banned from logging in or signing up.
# Cache for active 429 rate limit blocks: maps block_key -> reset_at epoch timestamp
_active_429_blocks = {}

# Active login ban registry per IP: maps ip_address -> expires_at epoch timestamp
_login_bans = {}

# Active signup/registration ban registry per IP: maps ip_address -> expires_at epoch timestamp
_signup_bans = {}


def record_login_ban(duration=60):
    """
    Records a temporary ban for the current client IP on login endpoints.
    Blocks both GET and POST requests for the duration.
    Preserves existing timer if a ban is already active (prevents timer reset on 'Try Again').
    """
    now = time.time()
    expires_at = now + duration
    from flask_limiter.util import get_remote_address
    try:
        from flask import request
        ips = {
            get_remote_address(),
            request.remote_addr,
            get_client_public_ip(),
            getattr(request, "environ", {}).get("REMOTE_ADDR"),
        }
        for ip in ips:
            if ip:
                existing_expiry = _login_bans.get(ip)
                # DO NOT reset or extend timer if ban is already active!
                if not existing_expiry or existing_expiry <= now:
                    _login_bans[ip] = expires_at
    except Exception:
        pass


def is_ip_login_banned():
    """
    Checks if the current client IP has an active login ban.
    Returns remaining seconds if banned (> 0), or 0 if not banned.
    Automatically cleans up expired ban records.
    """
    now = time.time()
    #1. Clean up expired bans from memory
    for k in list(_login_bans.keys()):
        if _login_bans[k] <= now:
            del _login_bans[k] #del is delete (if the time that we put in _login_bans is less than now which means the time is expired)

    #2. Check if current IP is banned
    from flask_limiter.util import get_remote_address
    try:
        from flask import request
        ips = {
            get_remote_address(),
            request.remote_addr,
            get_client_public_ip(),
            getattr(request, "environ", {}).get("REMOTE_ADDR"),
        }
        max_remaining = 0 #0 is means no longer banned(time remaining)
        for ip in ips:
            if ip and ip in _login_bans:
                expires_at = _login_bans[ip]
                if expires_at > now:
                    rem = int(expires_at - now)
                    if rem > max_remaining:
                        max_remaining = rem #Update the remaining time
        return max_remaining  # Returns remaining seconds (e.g. 35)
    except Exception:
        return 0 # 0 means NOT banned


def record_signup_ban(duration=60):
    """
    Records a temporary ban for the current client IP on signup/register endpoints.
    Blocks both GET and POST requests for the duration.
    Preserves existing timer if a ban is already active (prevents timer reset on 'Try Again').
    """
    now = time.time()
    expires_at = now + duration
    from flask_limiter.util import get_remote_address
    try:
        from flask import request
        ips = {
            get_remote_address(),
            request.remote_addr,
            get_client_public_ip(),
            getattr(request, "environ", {}).get("REMOTE_ADDR"),
        }
        for ip in ips:
            if ip:
                existing_expiry = _signup_bans.get(ip)
                # DO NOT reset or extend timer if ban is already active!
                if not existing_expiry or existing_expiry <= now:
                    _signup_bans[ip] = expires_at
    except Exception:
        pass


def is_ip_signup_banned():
    """
    Checks if the current client IP has an active signup ban.
    Returns remaining seconds if banned (> 0), or 0 if not banned.
    Automatically cleans up expired ban records.
    """
    now = time.time()
    for k in list(_signup_bans.keys()):
        if _signup_bans[k] <= now:
            del _signup_bans[k]

    from flask_limiter.util import get_remote_address
    try:
        from flask import request
        ips = {
            get_remote_address(),
            request.remote_addr,
            get_client_public_ip(),
            getattr(request, "environ", {}).get("REMOTE_ADDR"),
        }
        max_remaining = 0
        for ip in ips:
            if ip and ip in _signup_bans:
                expires_at = _signup_bans[ip]
                if expires_at > now:
                    rem = int(expires_at - now)
                    if rem > max_remaining:
                        max_remaining = rem
        return max_remaining
    except Exception:
        return 0

#Telegram Alert Function:
#get bot_token and chat_id from config.py file
def send_telegram_alert(e):
    """
    Sends an alert notification to the configured Telegram group for error events (e.g., 429 and 500).
    Takes 'e' (the exception/event object passed into error handlers).
    For HTTP 429, suppresses duplicate notifications while the blocking duration is still active.
    """
    #Read bot_token and chat_id from config.py file(or from environment variables)
    configured_bot_token = Config.TELEGRAM_BOT_TOKEN.strip()
    if not configured_bot_token and ":" in Config.TELEGRAM_BOT_TOKEN_ENV:
        configured_bot_token = Config.TELEGRAM_BOT_TOKEN_ENV.strip()

    bot_token = (
        os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        or os.environ.get(Config.TELEGRAM_BOT_TOKEN_ENV, "").strip()
        or configured_bot_token
    )
    chat_id = (
        os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        or os.environ.get(Config.TELEGRAM_CHAT_ID_ENV, "").strip()
        or Config.TELEGRAM_CHAT_ID.strip()
    )

    if not bot_token or not chat_id:
        return False, "Missing Telegram bot credentials."
    #Get the status code, description, type, and representation of the exception, in order to send alert to Telegram
    status_code = getattr(e, "code", 500)
    err_description = getattr(e, "description", str(e))
    event_type = type(e).__name__
    event_repr = repr(e)
    #Get request path, method, and IP address, for make the alert more detailed
    try:
        from flask import request
        req_path = request.path #get the path of the request
        req_method = request.method #get the method of the request
        req_ip = get_client_public_ip() #get the public ip address of the client
    except Exception:
        req_path = "N/A" #N/A means Not Available
        req_method = "N/A"
        req_ip = "N/A"

    block_duration_text = ""

    # For HTTP 429: send alert only once while the blocking period remains active
    if status_code == 429:
        now = time.time()
        block_key = None
        reset_at = None

        # Check Flask-Limiter current_limit for exact key and reset_at
        try:
            from extensions import limiter
            cl = getattr(limiter, "current_limit", None)
            if cl and hasattr(cl, "key") and hasattr(cl, "reset_at") and cl.reset_at:
                block_key = cl.key #The block key is the unique key that identifies the block(e.g., '429/127.0.0.1/login')
                reset_at = cl.reset_at #The reset time is the time when the block will be reset
        except Exception:
            pass

        # For login routes, unify block key across GET & POST so anti-spam is 100% synchronized
        if "login" in req_path:
            block_key = f"429/{req_ip}/login"
            if not reset_at:
                reset_at = now + 60
        elif "register" in req_path or "signup" in req_path:
            block_key = f"429/{req_ip}/signup"
            if not reset_at:
                reset_at = now + 60
        elif not block_key:
            block_key = f"429/{req_ip}/{req_path}"
            reset_at = now + 60

        # If already blocked and still within the blocking window, suppress duplicate notification
        existing_reset_at = _active_429_blocks.get(block_key)
        if existing_reset_at and now < existing_reset_at:
            remaining = max(1, int(existing_reset_at - now))
            return False, f"Alert suppressed: block is still active for ~{remaining}s."

        # Register this active block and clean up expired entries
        _active_429_blocks[block_key] = reset_at
        for k in list(_active_429_blocks.keys()):
            if _active_429_blocks[k] <= now:
                del _active_429_blocks[k] #Delete the expired block(keys)

        remaining_sec = max(1, int(reset_at - now)) #1 means the block will be reset in 1 second
        block_duration_text = f"~{remaining_sec} seconds" #The approximate time remaining for the block

    # Extract user and session details if available(for banning user account)
    logged_user = None
    logged_uid = None
    logged_role = None
    try:
        from flask import session
        if session:
            logged_user = session.get("username")
            logged_uid = session.get("user_id")
            logged_role = session.get("role")
    except Exception:
        pass

    #Get the current time in Asia/Cambodia timezone(UTC+7)
    from datetime import datetime, timezone, timedelta
    cam_time_str = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")

    # Generate DIFFERENT alert messages based on target type (User ID vs IP Address)
    if status_code == 429:
        if logged_uid:
            # 1. DIFFERENT MESSAGE FOR USER ID BAN (Alert User ID, Username, Role, Panel policy)
            lines = [
                "🛡️ <b>[USER RATE LIMIT BAN] Account Activity Throttled</b>",
                "",
                "👤 <b>Target User Account:</b>",
                f"• <b>User ID:</b> <code>{html.escape(str(logged_uid))}</code>",
                f"• <b>Username:</b> <b>{html.escape(str(logged_user))}</b>",
                f"• <b>Role:</b> <code>{html.escape(str(logged_role or 'admin'))}</code>",
                "• <b>Restriction Type:</b> <code>User ID-Based Throttle (10 req/min)</code>",
                "",
                "🌐 <b>Network & Endpoint Context:</b>",
                f"• <b>Client IP:</b> <code>{html.escape(str(req_ip))}</code>",
                f"• <b>Endpoint:</b> <code>{html.escape(req_method)} {html.escape(req_path)}</code>",
                f"• <b>Cooldown Duration:</b> <b>{html.escape(block_duration_text)}</b>",
                f"• <b>Timestamp (PP Cambodia):</b> <code>{cam_time_str}</code>",
                "",
                f"⚠️ <b>Status:</b> Account temporarily throttled for exceeding activity/refresh threshold.",
            ]
        else:
            # 2. DIFFERENT MESSAGE FOR IP BAN (Target Public / Local IP, Login brute-force)
            lines = [
                "🌐 <b>[IP RATE LIMIT BAN] Network IP Throttled</b>",
                "",
                "🚫 <b>Target Network Address:</b>",
                f"• <b>Client IP:</b> <code>{html.escape(str(req_ip))}</code>",
                "• <b>User Identity:</b> <i>Unauthenticated / Anonymous Guest</i>",
                "• <b>Restriction Type:</b> <code>IP Address-Based Throttle (5 failed/min)</code>",
                "",
                "📡 <b>Request & Incident Context:</b>",
                f"• <b>Endpoint:</b> <code>{html.escape(req_method)} {html.escape(req_path)}</code>",
                f"• <b>Cooldown Duration:</b> <b>{html.escape(block_duration_text)}</b>",
                f"• <b>Timestamp (PP Cambodia):</b> <code>{cam_time_str}</code>",
                "",
                f"⚠️ <b>Status:</b> Network IP blocked due to repeated requests ({html.escape(str(err_description))}).",
            ]
    elif status_code == 500:
        # 3. HTTP 500 SERVER ERROR ALERT
        lines = [
            "🔥 <b>[ALERT 500] Internal Server Error</b>",
            "",
            "💥 <b>Server Exception Details:</b>",
            f"• <b>Error Type:</b> <code>{html.escape(event_type)}</code>",
            f"• <b>Exception:</b> <code>{html.escape(event_repr)}</code>",
            f"• <b>Error Message:</b> {html.escape(str(err_description))}",
            "",
            "📍 <b>Request & Client Context:</b>",
            f"• <b>Request:</b> <code>{html.escape(req_method)} {html.escape(req_path)}</code>",
            f"• <b>Client IP:</b> <code>{html.escape(str(req_ip))}</code>",
            f"• <b>User:</b> {html.escape(str(logged_user or 'Anonymous'))} (ID: {logged_uid or 'N/A'}, Role: {logged_role or 'N/A'})",
            f"• <b>Timestamp (PP Cambodia):</b> <code>{cam_time_str}</code>",
        ]
    else:
        lines = [
            f"⚠️ <b>[ALERT {status_code}] Application Exception</b>",
            "",
            f"• <b>Status Code:</b> {status_code}",
            f"• <b>Request:</b> {html.escape(req_method)} {html.escape(req_path)}",
            f"• <b>Client IP:</b> <code>{html.escape(str(req_ip))}</code>",
            f"• <b>User:</b> {html.escape(str(logged_user or 'Anonymous'))} (ID: {logged_uid or 'N/A'}, Role: {logged_role or 'N/A'})",
            f"• <b>Timestamp (PP Cambodia):</b> <code>{cam_time_str}</code>",
            f"• <b>Message:</b> {html.escape(str(err_description))}",
        ]
    message_text = "\n".join(lines)

    #payload is the data that will be sent to the Telegram API(https://api.telegram.org/bot{bot_token}/sendMessage)
    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,#The chat ID of the user or group to send the message to
            "text": message_text,#The text of the message
            "parse_mode": "HTML",#The parse mode of the message
        }
    ).encode("utf-8")#Encode the payload to bytes in order to be sent to the Telegram API

    request_data = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",#The URL of the Telegram API
        data=payload,#The payload to be sent to the Telegram API
        method="POST",#The method of the request
    )

    try:
        #set timeout of 5 seconds for the request in case the Telegram API is not responding 
        with urllib.request.urlopen(request_data, timeout=5) as response:#Open the URL and send the request to the Telegram API with a timeout of 5 seconds
            res_body = response.read().decode("utf-8")#Read the response from the Telegram API
            res_json = json.loads(res_body)#Parse the response from the Telegram API
            return res_json.get("ok", False), res_json.get("description", "")#Return True if the request was successful and the description of the response, False otherwise
    except Exception as ex:#Handle any exceptions that occur during the request
        return False, str(ex)#Return False and the exception as a string if the request failed

#Alias for send_telegram_alert to send_error_to_telegram(for backward compatibility)
send_error_to_telegram = send_telegram_alert

#Helper for Flask-Limiter deduct_when on login routes.
#Used by: @limiter.limit("5 per minute", deduct_when=is_failed_login)
def is_failed_login(response):
    """
    Helper for Flask-Limiter deduct_when on login routes.
    Returns True only when a login attempt fails (e.g. invalid credentials redirecting back to login),
    ensuring successful logins are not counted against the rate limit.
    """
    if getattr(response, "is_failed_login", False):
        return True # in order to count the failed login if it is true 
    location = response.headers.get("Location") or ""#Get the location header from the response
    #302 is the redirect status code, "login" is the login route
    return response.status_code == 302 and ("login" in location)#Return True if the response is a redirect to the login route

#Tracked Logged-In admin_user_id_key
#Used by: @limiter.limit("10 per minute", key_func=admin_user_id_key).
def admin_user_id_key():
    """
    Rate limit key function for the Admin panel.
    If an admin user is logged in, keys strictly on their user_id (e.g. 'user:1'),
    enforcing a per-user limit on refreshes/requests regardless of network IP changes.
    Falls back to client IP if not logged in.
    """
    try:
        from flask import session
        uid = session.get("user_id")
        if uid:
            return f"user:{uid}"
    except Exception:
        pass
    from flask_limiter.util import get_remote_address
    return get_remote_address()


def log_activity(action, module, description=None, record_id=None, old_data=None, new_data=None, user_id=None, username=None):
    """
    Safely creates and commits an entry to the activity_log table in the database.
    Automatically captures current session user (if available), client IP, and User-Agent.
    """
    try:
        from flask import request, session, has_request_context
        from extensions import db
        from models import ActivityLog

        ua = None
        ip = "127.0.0.1"
        if has_request_context():
            if user_id is None:
                user_id = session.get("user_id")
            if username is None:
                username = session.get("username") or "Anonymous"
            ip = get_client_public_ip()
            ua = request.headers.get("User-Agent")
        else:
            if username is None:
                username = "System"
            ua = "System/CLI"

        from models.activity_log import get_cambodia_now
        cam_now = get_cambodia_now()

        entry = ActivityLog(
            action=action,
            module=module,
            user_id=user_id,
            username=username,
            ip_address=ip,
            user_agent=ua,
            record_id=record_id,
            description=description,
            old_data=old_data,
            new_data=new_data,
            created_at=cam_now,
        )
        db.session.add(entry)
        db.session.commit()
        return entry
    except Exception as err:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return None
