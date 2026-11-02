# MK7 Luxury Fashion E-Commerce Platform — Comprehensive Project Summary

> **Document Version**: 1.0.0  
> **Target Framework**: Python 3.12 / Flask 3.x  
> **Production Server**: AWS EC2 (Ubuntu 22.04 LTS)  
> **Live Production Domain**: [https://mk7-luxury-shop.duckdns.org](https://mk7-luxury-shop.duckdns.org)  
> **Local Development Port**: `3000` (Strict Project Rule)  
> **Repository**: [https://github.com/Mongkol7/ecommerce_clothes.git](https://github.com/Mongkol7/ecommerce_clothes.git) (`main` branch)

---

## 1. What This Project Is About

**MK7 Luxury Fashion** is an end-to-end modern e-commerce storefront and boutique retail operations management platform. Built with Python Flask, SQLAlchemy, and clean iOS-inspired glassmorphism, it bridges consumer shopping with enterprise warehouse management, real-time national banking payments, automated Telegram messaging, and robust security protections.

### Core Architecture & Design Philosophy
* **Aesthetic**: Minimalist luxury fashion editorial design featuring frosted glassmorphic cards, typography pairings (`Playfair Display` serif headers + `DM Sans` body), and subtle micro-interactions.
* **Dual-Currency Standard**:
  * **Authoritative Database Base Currency**: Cambodian Riel (**`KHR ៛`**). All database calculations, product prices, order subtotals, and refund balances are calculated and stored in integer/float KHR.
  * **Secondary Display Estimation**: United States Dollar (**`USD $`**), calculated in real-time across templates at a fixed conversion rate of `1 USD = 4,000 KHR` (`Config.KHR_RATE`).
* **Omnichannel Device Responsiveness**: Tailored viewports for desktop, iPad/tablets (768px–1024px), and mobile smartphones (320px–575px) featuring floating headers, slide-down drawers, and swipeable product/category carousels.

---

## 2. National Bank of Cambodia (NBC) Bakong KHQR Integration

MK7 incorporates a fully automated integration with Cambodia's national retail payments infrastructure via the **National Bank of Cambodia (NBC) Bakong KHQR** standard.

```
+-----------------------------------------------------------------------------------+
|                           BAKONG KHQR CHECKOUT FLOW                               |
+-----------------------------------------------------------------------------------+
   [ Customer Cart ] ---> [ Split Balance Check ] ---> [ Dynamic KHQR Generated ]
                                                               |
                                                   (Account ID: bkrt, 30m Exp,
                                                    EMVCo Tag 54 Integer KHR)
                                                               |
                                                               v
   [ Bank Transfer ] <--- [ Customer Banking App ] <--- [ Base64 QR Scanned ]
   (ABA, Acleda, Wing,    (Bakong NBC Protocol)
    Canadia, etc.)
          |
          v
   [ Merchant Polling ] ---> [ NBC Gateway Verify ] ---> [ Verified Paid Order ]
   (/api/payment/check/<md5>)  (/check_transaction_by_md5) (Order Created, DB Logged,
                                                            Telegram Alert Dispatched)
```

### Key Components & Logic (`services/khqr_service.py` & `front/checkout.py`)

1. **Dynamic EMVCo QR Code Generation (`generate_bakong_khqr`)**:
   * Uses the official `bakong_khqr` Python SDK.
   * **Merchant Account**: `thoeung_sereymongkol@bkrt`
   * **Merchant Identity**: `MK7 LUXURY STORE` (Phnom Penh)
   * **Store / Terminal Labels**: `Cashier-01` / `POS-01`
   * **Integer KHR Sanitization**: KHR currency has no fractional decimal cents in EMVCo Tag 54. The system rounds amounts (`int(round(amount))`) to ensure 100% banking scanner compatibility.
   * **Dynamic Expiration**: Generates dynamic individual QRs with a 30-minute validity window.
   * **Embedded Base64 Delivery**: Encodes QR directly into `data:image/png;base64,...` so images render instantly in templates without saving temporary files to disk.

2. **Transaction MD5 Hash Fingerprint**:
   * Each dynamic QR computes a unique 32-character MD5 transaction hash representing the specific bill and amount.
   * Stored in the order record and rendered in the admin management modal for accounting reconciliation.

3. **Live Bank Verification Polling (`check_bakong_payment`)**:
   * Frontend checkout triggers `/api/payment/check/<md5>` before form submission.
   * The backend queries NBC's gateway endpoint `/check_transaction_by_md5`.
   * **Response Code 0**: Marks transaction as verified paid (`PAID`), updates order payment status, and locks against duplicate submissions.
   * **Developer Quota Protection**: NBC's free developer tier limits API checks to 100 calls/day. The service detects error codes `17, 18, 19` or "daily request limit" messages, entering a graceful fallback mode allowing order creation while alerting administrators.

4. **Split Payment Engine (Store Credit Wallet + Bakong KHQR)**:
   * **Scenario A (100% Store Balance)**: If a customer has sufficient return money from previous cancellations, the entire order is deducted from `user.balance`. No QR is generated or scanned.
   * **Scenario B (100% Bakong KHQR)**: If the customer has zero balance, the full order amount generates a dynamic KHQR.
   * **Scenario C (Split Payment)**: Customer uses their available store credit, and the system dynamically generates a KHQR for only the **remaining due balance** (`remaining_due = total - balance_applied`).

---

## 3. Telegram Channel & Bot Automation

The platform features an automated real-time dispatch system connecting store events directly to a Telegram operations channel using the official Telegram Bot API via `helpers.py`.

* **Bot Token**: `8731861019:AAGvUklnjOPIN2E0cfF8k5mLJvxpJfwg1aY`
* **Target Channel / Group**: `@SV26_Shop` (`Config.TELEGRAM_CHAT_ID`)

```
+-----------------------------------------------------------------------------------+
|                        TELEGRAM DISPATCH ARCHITECTURE                             |
+-----------------------------------------------------------------------------------+
    Store Events               helpers.py Formatter              Telegram Bot API
 ------------------        -----------------------------        ------------------
  New Order Placed    --->  format_order_for_telegram()    --->  POST sendMessage
  Order Cancelled     --->  format_order_cancellation...() --->  Channel: @SV26_Shop
  500 / 429 Errors    --->  send_telegram_alert()          --->  Instant Notification
```

### Alert Types & Real-Time Payloads

#### A. New Customer Order Alert (`send_order_to_telegram`)
Triggered immediately upon successful checkout verification:
* **Order Number & Bill Reference**: Unique order identifier (`ORD-XXXXX`).
* **Payment Gateway & Status**: Displays `Verified Paid via Bakong KHQR (280 ៛ KHR / ≈ $0.07 USD)` or `Paid via MK7 Store Credit`.
* **Bakong MD5 Fingerprint**: The 32-character transaction hash for instant banking lookup.
* **Customer Contact & Shipping Profile**: Recipient full name, verified phone number, email address, physical delivery address, and customer special instructions.
* **Itemized Cart Breakdown**: Every item title, purchased quantity, unit price in dual currency, line item subtotal, and stock synchronization confirmation.
* **Phnom Penh Timestamp**: Local Cambodia time (`UTC+7`).

#### B. Customer Order Cancellation Alert (`send_order_cancellation_to_telegram`)
Triggered when a customer exercises their cancellation right within the 4-hour grace window:
* **Order Details**: Cancelled order number, original payment method, and total amount.
* **Automatic Refund Confirmation**: Confirms 100% of the funds were credited to the customer's MK7 account balance.
* **Warehouse Restock Log**: Lists all cancelled items and confirms stock has been added back to active inventory.
* **Incident Timeline**: Placed timestamp vs. Cancelled timestamp in Phnom Penh local time.

#### C. System Exceptions & Security Lockout Alerts (`send_telegram_alert`)
Triggered automatically by Flask error handlers:
* **HTTP 500 Runtime Crashes**: Exception type, error message, failing route, HTTP method, client IP, and stack trace representation.
* **HTTP 429 Rate Limiting & Anti-Spam Bans**: Notifies administrators when an IP triggers rate limits or gets temporarily locked out after 5 consecutive failed login attempts. Includes built-in deduplication so admins are not spammed while an IP is actively banned.

---

## 4. Customer Storefront & Lifecycle Workflows

```
  [ Home / Catalog ] ---> [ Product Detail ] ---> [ Shopping Bag ]
                                                         |
                                                         v
  [ Orders History ] <--- [ Verified Order ] <--- [ Checkout + KHQR ]
          |
     (Within 4 Hours)
          |
          v
  [ Instant Cancel ] ---> [ 100% Wallet Credit ] ---> [ Re-checkout Next Order ]
```

1. **Catalog & Intelligent Search**:
   * Products classified into categories (`tops`, `sets`, `outerwear`, etc.).
   * Dual-currency price badges (`{price|khr_format}` and `{price|usd_format}`).
   * Live inventory pill badges (`In Stock`, `Only X Left`, `Out of Stock`).
   * Dynamic horizontal category carousel supporting touch swipe on mobile and iPad.
2. **Product Detail Page**:
   * Interactive image gallery with responsive height scaling.
   * Live stock checking prevents adding out-of-stock items.
   * Real-time AJAX bag insertion with toast feedback without full page reloads.
3. **Cart & Bag Engine**:
   * Cookie-backed persistent bag supporting quantity increments, decrements, and removals.
4. **Member Center & Return Money Ledger (`/profile`)**:
   * **Editable Credentials**: Users can change their avatar picture (scaled and saved), display username (uniqueness validated), email, and password.
   * **Store Balance / Return Money Card**: Displays available store credit in KHR and USD.
   * **Audit Ledger Table**: Historical records of all cancellation refunds and checkout balance applications.
5. **4-Hour Grace Window Cancellation Engine**:
   * Customers can cancel an order within 4 hours directly from their order history (`/orders`).
   * **Instant Automated Refund**: 100% of the order total is credited back to `user.balance` via a recorded `WalletTransaction`.
   * **Inventory Restoration**: Quantities of all ordered items are returned to active warehouse stock immediately.
   * **Notification**: Generates an in-app `Notification` record and sends an alert to the Telegram admin channel.

---

## 5. Admin Management Portal (`/admin`)

* **Executive Dashboard (`admin/dashboard.py`)**:
  * **Net Realized Revenue**: Real-time revenue from confirmed orders in KHR and USD.
  * **Total Stock Inventory Value**: Aggregated value of all warehouse inventory (`SUM(price * stock)`).
  * **Orders & Fulfillment Card**: Confirmed orders count vs. Cancelled orders count with status badges.
  * **Financial Liabilities**: Tracks Return Money liability (`SUM(user.balance)`) and Cancelled revenue loss.
  * **Interactive Revenue Charts**: Weekly revenue trend charts displaying dual currency tooltips (both KHR and USD).
* **Order Management & Detail Modal (`admin/order.py`)**:
  * Complete lifecycle filtering (`pending`, `confirmed`, `shipped`, `delivered`, `cancelled`).
  * Phnom Penh local time formatting (`@app.template_filter("cambodia_time")`).
  * **Luxury Redesigned Order Modal**: Structured cards for Recipient Profile, Delivery Destination, Payment Gateway (with MD5 hash box and copy button), Amber Callout box for Customer Special Instructions, Split Payment breakdown bar, and live warehouse inventory counts.
* **Product Catalog CRUD**:
  * Add, edit, and delete products, manage inventory stock counts, upload product gallery images, and assign categories.
* **User Management (`admin/users.py`)**:
  * Review customer accounts, adjust account roles (`admin` / `shopper`), inspect balances, and enforce administrative bans.
* **Activity Audit Logging (`admin/activity_log.py`)**:
  * Stores security events, login attempts, rate limit violations, and 500 runtime exceptions into the database.

---

## 6. Security, Rate Limiting & Concurrency Hardening

1. **Proxy-Aware Client IP Extraction**:
   * Unified in `get_limiter_client_ip()` ([`extensions.py`](file:///d:/Document/CODES DEV/SV2-Y3/Phython/FlaskProject/extensions.py)) and `get_client_public_ip()` ([`helpers.py`](file:///d:/Document/CODES DEV/SV2-Y3/Phython/FlaskProject/helpers.py)).
   * Sequentially inspects `CF-Connecting-IP` (Cloudflare) $\rightarrow$ `X-Real-IP` (Nginx) $\rightarrow$ `X-Forwarded-For` $\rightarrow$ `remote_addr`.
   * Operates seamlessly across local development, Docker, and Nginx reverse proxies.

2. **Rate Limiting & Anti-Brute-Force Lockouts**:
   * Powered by **Flask-Limiter** with custom client IP keying.
   * Failed login and signup protection: 5 failed attempts within 60 seconds triggers a synchronized 60-second lockout.
   * Dedicated testing routes: `/test429` (HTML) and `/api/test429` (JSON).

3. **Error Handlers & Template Resilience**:
   * `internal_error_handler` (500) and `ratelimit_handler` (429) execute `db.session.rollback()` and isolate all Telegram and database operations inside `try...except`.
   * Secondary network timeouts or database lock exceptions never suppress template rendering, ensuring luxury `500.html` and `429.html` pages always display.

4. **Gunicorn Shared-Memory Architecture**:
   * Single-node production servers run `gunicorn --workers 1 --threads 8 --bind 127.0.0.1:5000 app:app`.
   * **Why 1 Worker with 8 Threads?**: In-memory rate limiting and login ban registries (`_login_bans`) reside in Python process memory. A single process with 8 concurrent threads ensures all requests share the same ban counter and memory space, eliminating round-robin memory isolation across multiple worker processes.

---

## 7. Database Schema & Data Models

Primary database engine: **PostgreSQL 18** (production) / **SQLite 3** (local development).

| Model | Table | Core Fields | Description |
| :--- | :--- | :--- | :--- |
| **`User`** | `users` | `id`, `username`, `email`, `password`, `role`, `profile`, `balance` | Customer & Admin user accounts with hashed credentials and wallet balance. |
| **`Product`** | `products` | `id`, `title`, `price` (KHR), `category`, `stock`, `image`, `thumbnail`, `description`, `rating` | Catalog items with stock levels, dual image URLs, and KHR prices. |
| **`Order`** | `orders` | `id`, `order_number`, `user_id`, `customer_name`, `customer_email`, `customer_phone`, `delivery_address`, `total`, `balance_used`, `status`, `payment_method`, `payment_status`, `notes`, `paid_at`, `cancelled_at`, `created_at` | Customer purchase orders tracking lifecycle states, payment gateway, MD5, and timestamps. |
| **`OrderItem`** | `order_items` | `id`, `order_id`, `product_id`, `product_title`, `product_price`, `quantity`, `subtotal` | Normalized order line items linking products to orders. |
| **`WalletTransaction`**| `wallet_transactions` | `id`, `user_id`, `amount`, `balance_after`, `type`, `description`, `order_id`, `created_at` | Financial ledger tracking balance credits (cancellations) and debits (checkouts). |
| **`Notification`** | `notifications` | `id`, `user_id`, `title`, `message`, `is_read`, `type`, `created_at` | In-app user notifications for refunds, order progress, and account updates. |
| **`ActivityLog`** | `activity_logs` | `id`, `action`, `module`, `description`, `user_id`, `username`, `ip_address`, `old_data`, `new_data`, `created_at` | Comprehensive security, audit, rate limit, and exception log. |

---

## 8. Server Specifications & Production Runbook

* **Cloud Infrastructure**: Amazon Web Services (AWS) EC2
* **Operating System**: Ubuntu 22.04 LTS
* **Web Server**: Nginx Reverse Proxy with Let's Encrypt SSL
* **WSGI Server**: Gunicorn (managed by Systemd `mk7.service`)
* **Local Development Command**:
  ```bash
  python app.py  # Strictly runs on port 3000
  ```

### Standard Deployment Runbook
```bash
# 1. Connect to EC2 server
ssh -i /path/to/key.pem ubuntu@mk7-luxury-shop.duckdns.org

# 2. Pull latest code from GitHub
cd /home/ubuntu/ecommerce_clothes
git pull origin main

# 3. Activate virtual environment & update dependencies
source .venv/bin/activate
pip install -r requirements.txt

# 4. Verify Gunicorn service configuration (--workers 1 --threads 8)
sudo sed -i 's/--workers 3/--workers 1 --threads 8/g' /etc/systemd/system/mk7.service

# 5. Reload systemd and restart services
sudo systemctl daemon-reload
sudo systemctl restart mk7
sudo systemctl restart nginx
sudo systemctl status mk7 --no-pager
```

---

## 9. Technology Stack Summary

* **Backend**: Python 3.12, Flask 3.x, Werkzeug, Jinja2
* **ORM & Database**: SQLAlchemy, Flask-SQLAlchemy, Flask-Migrate, PostgreSQL 18 / SQLite3
* **Payment Gateway**: National Bank of Cambodia (NBC) Bakong KHQR SDK (`bakong_khqr`)
* **Alerting & Messaging**: Telegram Bot API (`urllib.request` / `requests`)
* **Security & Protection**: Flask-Limiter, Flask-WTF (CSRF), Werkzeug Security (PBKDF2 SHA-256), ProxyFix
* **Frontend UI**: HTML5, Vanilla JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons, DM Sans & Playfair Display fonts
* **Hosting & DevOps**: AWS EC2, Nginx, Gunicorn (gthread), Systemd, DuckDNS, Certbot (SSL)
