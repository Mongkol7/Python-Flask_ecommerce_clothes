# Project Brain

## Project
Flask Jinja storefront for MK7, a fashion-style shop using static Python product data and local image assets. The project does not use a database yet. It now includes a front-facing storefront and an AdminLTE-based admin panel.

## Current App Shape (Modular Blueprint Architecture)
- Main Flask application & Blueprint registration: [app.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/app.py)
- Configuration class: [config.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/config.py) (`class Config`)
- Extension initialization: [extensions.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/extensions.py) (`db`, `migrate`, `limiter`, `cors`, `csrf`)
- Global helpers & utilities: [helpers.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/helpers.py) (includes cart helpers, upload helpers, and `get_client_public_ip()`)
- Models package: [models/](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/models) (`models/users.py`, `models/activity_log.py`, `models/__init__.py`)
- Front Blueprint: [front/](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/front) (`front/__init__.py`, `home.py`, `product.py`, `cart.py`, `checkout.py`, `customer.py`)
- Admin Blueprint: [admin/](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/admin) (`admin/__init__.py`, `auth.py`, `dashboard.py`, `user.py`, `activity_log.py`)
- API Blueprint: [api/](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/api) (`api/__init__.py`, `user.py`, `product.py`)
- Product data/helpers: [api/product.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/api/product.py) (holds the static product list, helper functions, and `/api/product` routes) & [product.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/product.py) (re-exports for storefront backward compatibility)
- Templates: `templates/`
  - Front-facing pages: `templates/front/`
  - Admin pages: `templates/admin/`
  - Shared front components: `templates/components/`
- CSS files: `static/css/` (storefront)
- Admin static assets: `static/admin/` (AdminLTE CSS/JS)
- Additional style directory: `static/style/`
- Local product images: `static/image/`

## Template Directory Structure
Templates were reorganized from a flat layout into subdirectories:

### Front (Storefront)
- `templates/front/base.html` — minimal base layout (simple header, not the MK7 design)
- `templates/front/home.html`
- `templates/front/product.html`
- `templates/front/product-detail.html` — main product detail (MK7 design with thumbnails)
- `templates/front/product_detail.html` — alternate simpler product detail (extends `base.html`)
- `templates/front/cart.html`
- `templates/front/checkout.html`
- `templates/front/search.html`

### Admin
- `templates/admin/master.html` — admin master layout using AdminLTE
- `templates/admin/dashboard.html` — admin dashboard (extends `master.html`)
- `templates/admin/user/user.html` — user management page (extends `master.html`)
- `templates/admin/user/add.html` — add new user form page (extends `master.html`)
- `templates/admin/components/header.html`
- `templates/admin/components/navbar.html`
- `templates/admin/components/sidebar.html`
- `templates/admin/components/footer.html`
- `templates/admin/components/scripts.html`

### Shared Front Components
- `templates/components/navbar.html` — storefront glass navbar with search and interactive profile dropdown (Log In and Sign Up buttons for guests; user dashboard links and sign out for authenticated users)
- `templates/components/footer.html` — storefront dark footer

### Error Pages
- `static/css/error.css` — dedicated luxury editorial stylesheet sharing MK7 design tokens (`Playfair Display`, `DM Sans`, `JetBrains Mono`, frosted glassmorphic card, status pulse dots, ambient gradient spheres, and pill CTAs).
- `templates/400.html` — custom 400 Bad Request error page styled in MK7 luxury aesthetic with amber accent, security exception pill, device public IP chip, and refresh CTA.
- `templates/429.html` — custom 429 Too Many Requests error page styled in MK7 luxury aesthetic with crimson accent, rate limit enforced badge, device public IP chip, rate limit reason code, and retry CTA.
- `templates/404.html` — custom 404 Not Found error page styled in MK7 luxury aesthetic with charcoal/slate accent, resource not found badge, device public IP chip, and collection exploration CTA.
- `templates/500.html` — custom 500 Internal Server Error page styled in MK7 luxury aesthetic with deep wine accent, system malfunction badge, device public IP chip, incident report info, and retry CTA.

## Routes

### Storefront Routes
- `/` renders the MK7 homepage from `templates/front/home.html`.
  - Passes `products[:4]` and `featured_products=products[4:8]`.
- `/product` renders the product listing from `templates/front/product.html`.
- `/product/<int:product_id>` renders product detail from `templates/front/product-detail.html`.
- `/product-detail/<int:product_id>` is kept as an old compatible detail route.
- `/search?q=...` renders search results from `templates/front/search.html`.
- `/cart` renders the cart. If `?product_id=ID` is present, it adds that product to the cart cookie and redirects to `/cart`. Unauthenticated shoppers clicking "Checkout" receive a luxury modal alert prompting them to Log In or Sign Up.
- `/cart/update` handles POST actions: `plus`, `minus`, and `remove`.
- `/checkout` renders `templates/front/checkout.html` (guarded: requires `session['is_login']`; redirects unauthenticated guests to login with `next=/checkout`). Generates live Bakong KHQR (National Bank of Cambodia) via `services.khqr_service.generate_bakong_khqr()` and passes the dynamic `base64_uri`, merchant info, and transaction MD5 hash to the template.
- `/payment` handles POST checkout submission (guarded: requires `session['is_login']`; rate-limited to 5/min). Enforces real payment gateway only (`bakong_khqr`), recalculates total prices strictly from the database (anti-tampering), validates inventory stock before deduction, verifies payment status with NBC Bakong API, and triggers instant Telegram order alerts to `@SV26_Shop`.
- `/api/payment/check/<md5_hash>` provides real-time payment status checking via NBC Bakong API for live frontend AJAX polling.
- `/my-orders` and `/orders` render customer order history from `templates/front/orders.html`. Shows all orders placed by the authenticated user, live cancellation countdown timers, and auto-transitions pending orders older than 4 hours to `confirmed`.
- `/orders/<int:order_id>/cancel` handles POST cancellation by the order owner. If within 4 hours, sets status to `cancelled`, restores inventory stock (`Product.stock += item.quantity`), sends real-time Telegram cancellation alert notification to `@SV26_Shop` via `send_order_cancellation_to_telegram()`, and logs activity. If expired (>4 hours), transitions status to `confirmed` and rejects cancellation.
- `/profile` and `/my-profile` render customer profile from `templates/front/profile.html`. Allows authenticated customers to upload new avatar photos (original and Pillow-compressed thumbnail via `upload_service.py`), updates `user.profile` and `session['profile']`, and syncs with the navbar avatar.
- `/test500` triggers a real Python runtime error (`division by zero`) to test `templates/500.html` and the Telegram alert.
- `/api/test500` triggers a real Python runtime error (`division by zero`) to test the JSON 500 response and the Telegram alert.
- `/test400` triggers a real client parameter error (`BadRequestKeyError` on missing query param) to test `templates/400.html`.
- `/api/test400` triggers a real client parameter error (`BadRequestKeyError` on missing query param) to test JSON 400 response.

### Configuration & Upload Service
- [config.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/config.py): defines `UPLOAD_USER_FOLDER = static/image/user`, `UPLOAD_PRODUCT_FOLDER = static/image/product`, `UPLOAD_CAROUSEL_FOLDER = static/image/carousel`, `ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}`, and `MAX_CONTENT_LENGTH = 2MB`.
- [upload_service.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/upload_service.py): provides `allowed_file(filename, allowed_extensions)` and `save_user_image(file, user_id, upload_folder, allowed_extensions, scale=0.8)`. Saves original `{user_id}_org_{filename}` and 80% dimension Pillow compressed thumbnail `{user_id}_thum_{filename}` in `static/image/user/`. Returns clean base filename for database storage.

### Authentication & Admin Security
- `app.config["SECRET_KEY"]`: enables secure session cookies.
- `app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=1440)`: sets session lifetime to 24 hours.
- `@login_required` decorator: checks `session.get("is_login")` and validates `session.get("role") == "admin"`. Redirects unauthenticated users to `/admin/login` and redirects standard users (`role == "user"`) with a flash message to `/` (home storefront).
- `/admin/login` (GET, POST): Dedicated Administrator portal. Restricts authentication to `role == "admin"`. If non-admin attempts login, rejects with access denied flash alert. Redirects to `/admin/dashboard`.
- `/user/login` and `/login` (GET, POST): Dedicated Customer/Shopper portal. Authenticates users and redirects them to `/` for shopping.
- `/admin/logout`, `/user/logout`, `/logout` (GET): Clears session and redirects to storefront (`/`).
- `templates/admin/login.html`: Unified login page styled with `static/admin/css/login.css`. Dynamically adapts titles, kickers, brand icons (`bi-shield-lock` vs `bi-person-circle`), subtitle, submit buttons, and cross-portal switch links based on whether called from `/admin/login` or `/user/login`.
- **Flask-Limiter (Rate Limiting)**: Configured via [extensions.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/extensions.py) with `default_limits=["100 per minute", "10000 per day"]`.
  - **Login Rate Limit (IP-based)**: `@limiter.limit("5 per minute", methods=["POST"], deduct_when=is_failed_login)` restricts failed login attempts to 5 per minute per IP address. Successful logins do not deduct from the limit. Page refreshes on GET are protected with 10/min.
  - **Admin Rate Limit (User ID-based)**: Admin panel routes (`/admin/dashboard`, `/admin/users`, `/admin/activity-logs`) use `@limiter.limit("10 per minute", key_func=admin_user_id_key, methods=["GET"])`, tracking logged-in admins by `user:{user_id}` to prevent aggressive refreshes regardless of client IP changes.
  - **Ban Cooldown & Anti-Spam**: Once 429 is triggered, a 60-second cooldown is enforced. `send_telegram_alert(e)` notifies administrators via Telegram with device IP, user ID/username, request endpoint, and error details while suppressing duplicate alerts during active bans.
  - **Rate Limit Database Logging**: In [app.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/app.py), `ratelimit_handler(e)` writes full rate limit exception payloads into the `activity_log` table via `log_activity()`.
- **Flask-CORS**: Initialized in [extensions.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/extensions.py) and configured in [app.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/app.py) on `r"/api/*"` for testing from Angular (`http://localhost:4200`, `http://127.0.0.1:4200`) and storefront (`http://localhost:3000`, `http://127.0.0.1:3000`), with `supports_credentials=True`, methods `["GET", "POST", "PUT", "DELETE", "OPTIONS"]`, and custom headers `["Content-Type", "Authorization", "X-Requested-With", "Accept"]`. Test route `/api/data` verifies cross-origin access.
- **Flask-WTF CSRF**: Initialized via [extensions.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/extensions.py) (`csrf = CSRFProtect()`) and configured in [app.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/app.py) with `app.config["SECRET_KEY"]`. Every POST form ([login.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/admin/login.html), [add.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/admin/user/add.html), [edit.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/admin/user/edit.html), [cart.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/front/cart.html), [checkout.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/front/checkout.html)) includes `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`, and Axios AJAX requests in [user.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/admin/user/user.html) attach `X-CSRFToken`. The API blueprint (`api_bp`) is exempt (`csrf.exempt(api_bp)`) for CORS-compliant API access. Violations render [templates/400.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/400.html) or return JSON 400.

### Admin Design System & Theme
- [static/admin/css/admin-theme.css](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/static/admin/css/admin-theme.css): Comprehensive luxury editorial stylesheet aligning all Admin pages with the storefront style (`Playfair Display` + `DM Sans`, warm neutrals `--off-white: #f7f6f3`, `--black: #0a0a0a`, `--sand: #e8e6e0`, glassmorphism `.card-mk7`, pill buttons `.btn-pill-primary`, editorial table `.table-editorial`, and custom ApexCharts palette).
- [templates/admin/master.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/admin/master.html): Master layout container with kicker tags, serif titles, and minimal chevron breadcrumb navigation.
- [templates/admin/components/navbar.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/admin/components/navbar.html): Frosted header with dynamic DB profile avatar thumbnail (`inject_current_user`), user profile dropdown, role badge, and Sign out link.
- [templates/admin/components/sidebar.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/admin/components/sidebar.html): Sleek dark sidebar with `MK7 Admin` shield logo and pill menu items.

### Admin Routes
- `/admin/dashboard` (@login_required) renders `templates/admin/dashboard.html` (4 luxury metric cards, themed ApexCharts, and quick action panels). Protected by 10/min `user_id` rate limit.
- `/admin/users` (@login_required) renders `templates/admin/user/user.html` (editorial table with thumbnail avatars, pill badges, and glassmorphic delete confirmation modal).
- `/admin/users/add` (@login_required, GET/POST) renders `templates/admin/user/add.html` (centered form card with circular avatar upload picker and pill buttons).
- `/admin/users/edit/<int:user_id>` (@login_required, GET/POST) renders `templates/admin/user/edit.html` (centered form card with original image preview, change photo picker, and pill buttons).
- `/admin/users/delete/<int:user_id>` (@login_required, POST) deletes user via ORM and returns JSON response `{"success": true, "message": "..."}` for Axios.
- `/admin/activity-logs` and `/admin/logs` (@login_required) renders `templates/admin/activity_log/index.html` (system activity security audit trail with Module and Action filter dropdowns, search query box, editorial table with UTC+7 timestamps, and dynamic telemetry modal for rate limits and 500 error investigations). Protected by 10/min `user_id` rate limit.
- `/admin/activity-logs/<int:log_id>` (@login_required) returns JSON details for the audit log entry modal.

#### Admin Catalog Management (CRUD)
- **Categories**:
  - `/admin/categories` (@login_required, GET): Editorial table listing all taxonomies, cover thumbnails, product count pill badges, search bar, and delete confirmation modal.
  - `/admin/categories/add` (@login_required, GET/POST): Category creation form with cover image upload, slug auto-generation, and name validation.
  - `/admin/categories/edit/<int:cat_id>` (@login_required, GET/POST): Category edit form with current cover preview, change image picker, and slug modification.
  - `/admin/categories/delete/<int:cat_id>` (@login_required, POST): AJAX deletion endpoint returning JSON `{success: true, message: "..."}` for Axios.
- **Brands**:
  - `/admin/brands` (@login_required, GET): Fashion houses registry table with logo preview, website link, product count badge, search filter, and delete modal.
  - `/admin/brands/add` (@login_required, GET/POST): Brand creation form with logo file picker, website URL, slug generation, and brand story description.
  - `/admin/brands/edit/<int:brand_id>` (@login_required, GET/POST): Brand update form with logo replacement and brand details.
  - `/admin/brands/delete/<int:brand_id>` (@login_required, POST): AJAX deletion endpoint returning JSON `{success: true, message: "..."}` for Axios.
- **Products**:
  - `/admin/products` (@login_required, GET): Luxury product inventory table with main thumbnail, title, price, category badge, brand badge, stock status pill, gender fit, rating stars, search bar, and multi-filter dropdowns (by category, brand, gender).
  - `/admin/products/add` (@login_required, GET/POST): Product creation form with multi-angle image upload (primary hero photo and 2 gallery angle shots), title, price, category dropdown, brand dropdown, gender selector, inventory stock, description, and "Featured Collection" checkbox.
  - `/admin/products/edit/<int:product_id>` (@login_required, GET/POST): Product update form with live previews of all existing images, replacement file pickers, and inventory controls.
  - `/admin/products/delete/<int:product_id>` (@login_required, POST): AJAX deletion endpoint returning JSON `{success: true, message: "..."}` for Axios.
- **Customer Orders & Stock Interaction**:
  - `/admin/orders` (@login_required, GET): Order management suite with 4 metrics (Total Orders, Pending Review, Confirmed/Delivered, Gross Revenue), status and keyword filters, interactive status dropdowns, detail modal, and deletion modal.
  - `/admin/orders/add` (@login_required, GET/POST): Allows admin to manually create an order for a registered user or guest customer. Features dynamic product line items with live stock limits, price calculation, and real-time database stock deduction.
  - `/admin/orders/<int:order_id>` (@login_required, GET): Returns JSON breakdown of customer info, shipping destination, and ordered items for the modal inspector.
  - `/admin/orders/<int:order_id>/status` (@login_required, POST): Bidirectional inventory management. Changing status to `cancelled` automatically restocks the ordered items back into product inventory; moving back from `cancelled` re-deducts the stock.
  - `/admin/orders/<int:order_id>/delete` (@login_required, POST): Deletes order and automatically restocks inventory if the order was active.

### Storefront Stock Display & Live Deduction
- **Product Badges**: Every product card ([home.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/front/home.html), [product.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/front/product.html), [search.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/front/search.html)) and the product detail view ([product-detail.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/front/product-detail.html)) display a real-time stock pill:
  - `stock > 10`: Green pill (`X in stock`).
  - `1 <= stock <= 10`: Amber pill (`Only X left`).
  - `stock <= 0`: Red pill (`Out of stock`), automatically disabling the Add button.
- **Real-time AJAX Cart Deduction** (`static/js/stock-cart.js` & `/cart/add-ajax`):
  - Clicking `+` or `Add to Bag` sends an asynchronous request to `/cart/add-ajax`.
  - Decrements the visible `.stock-count` on the UI instantly with a pulse micro-animation.
  - Automatically updates the navbar bag counter badge `data-count` with a bounce effect.
  - Displays a glassmorphic floating toast notification showing units remaining.
  - If units reach 0, disables the button and updates the pill to "Out of stock".
- **Storefront Checkout Stock Deduction** (`/payment` in [front/checkout.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/front/checkout.py)):
  - Persists customer order into `orders` and `order_items` tables.
  - Deducts `product.stock` in the SQLite database in real time for every item purchased.

### API Architecture & JWT Authentication
To allow seamless external and cross-origin access (such as Angular on port 4200 or mobile apps) without relying on cookie sessions:
- **JWT Authentication Engine** ([api/jwt_auth.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/api/jwt_auth.py)):
  - Tokens generated using `pyjwt` with HMAC-SHA256 and `Config.JWT_SECRET_KEY`.
  - Token payload encodes `sub` (user_id), `username`, `email`, `role`, `iat`, and `exp` (1-day expiration).
  - `@jwt_required`: Protects API routes, extracting `Authorization: Bearer <token>` header, verifying signature, and attaching `g.current_user`.
  - `@jwt_admin_required`: Restricts write/delete mutations exclusively to users with `role == "admin"`.
- **JWT Auth Endpoints** ([api/auth.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/api/auth.py)):
  - `POST /api/auth/login` (and `/api/login`): Accepts JSON `{"username": "admin", "password": "password123"}` (or email), validates credentials, and returns `{success: true, token: "<jwt>", access_token: "<jwt>", token_type: "Bearer", user: {...}}`.
  - `POST /api/auth/register` (and `/api/register`): Registers new user and returns JWT token immediately.
  - `GET /api/auth/me`: Returns profile of the authenticated token bearer.
- **REST API Endpoints**:
  - `/api/categories` (GET, POST): List all categories / Create category (admin only).
  - `/api/categories/<id>` (GET, PUT, DELETE): Get detail with linked products / Update category / Delete category.
  - `/api/brands` (GET, POST): List all brands / Create brand (admin only).
  - `/api/brands/<id>` (GET, PUT, DELETE): Get brand detail with products / Update brand / Delete brand.
  - `/api/products` (GET, POST): List all products with filtering (`category`, `brand`, `gender`, `search`, `featured`) / Create product (admin only).
  - `/api/products/<id>` (GET, PUT, DELETE): Single product detail / Update product / Delete product.
  - `/api/orders` (GET, POST): List user/admin orders / Place order with live stock deduction.
  - `/api/orders/<id>` (GET): Order detail breakdown.
  - `/api/orders/<id>/status` (PUT, PATCH): Update status with automatic restock / re-deduct.

## Database & Models
Database is SQLite (`instance/mydb.sqlite3`) managed via SQLAlchemy ORM:
- **User** ([models/users.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/models/users.py)): id, username, email, password (hashed), role ('admin'|'user'), profile, created_at.
- **ActivityLog** ([models/activity_log.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/models/activity_log.py)): id, user_id, action, module, description, ip_address, created_at.
- **Category** ([models/category.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/models/category.py)): id, name, slug (unique), description, image, created_at, products relationship.
- **Brand** ([models/brand.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/models/brand.py)): id, name, slug (unique), description, logo, website, created_at, products relationship.
- **Product** ([models/product.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/models/product.py)): id, title, price, description, category_id (FK), brand_id (FK), image, sub_images (JSON text), stock, rating_rate, rating_count, is_featured, gender, created_at.
- **Order & OrderItem** ([models/order.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/models/order.py)):
  - `Order`: id, order_number (unique), user_id (FK), customer_name, customer_email, customer_phone, shipping_address, city, zip_code, payment_method, subtotal, total, status, notes, created_at.
  - `OrderItem`: id, order_id (FK), product_id (FK), product_title, product_price, product_image, quantity, subtotal.
- **Dynamic Proxy Architecture** ([api/product.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/api/product.py)):
  - Implements `ProductsProxy` so existing storefront helpers and lists (`products`, `get_product_by_id`, `get_cart_items`, `get_related_products`) automatically query the SQLite database in real-time while remaining 100% backward-compatible with static fallback.
- **Database Seeder** ([models/seed.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/models/seed.py)): Automatically seeds default categories (`Tops`, `Sets`), brands (`MK7 Studio`, `L'Atelier Minimal`, `Celine`), and all 12 original fashion merchandise items upon first boot.
- **Dynamic Proxy Architecture** ([api/product.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/api/product.py)):
  - Implements `ProductsProxy` so existing storefront helpers and lists (`products`, `get_product_by_id`, `get_cart_items`, `get_related_products`) automatically query the SQLite database in real-time while remaining 100% backward-compatible with static fallback.
- **Database Seeder** ([models/seed.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/models/seed.py)): Automatically seeds default categories (`Tops`, `Sets`), brands (`MK7 Studio`, `L'Atelier Minimal`, `Celine`), and all 12 original fashion merchandise items upon first boot.
- `search_products(query)`
- `get_products_by_category()`
- `get_product_gender(product)`

## Cart Behavior
Cart is stored in a browser cookie named `cart`.

Cookie format:
```json
[{"id": 1, "qty": 2}]
```

Only product ID and quantity are stored in the cookie. Full product information is mapped from `product.py` when rendering cart/checkout.

`app.py` helpers:
- `load_cart()`
- `save_cart(response, cart)`
- `add_to_cart(cart, product_id)`
- `update_cart_item(cart, product_id, action)`

`app.py` also has a context processor:
- `inject_cart_count()` — provides `cart_count` (number of distinct products, not total qty) to templates for the navbar cart badge.

## Components
Navigation and footer were moved into shared Jinja components:
- `templates/components/navbar.html`
- `templates/components/footer.html`

Shared component CSS:
- `static/css/components.css`

All active front pages include the component CSS and the shared navbar/footer.

Active pages using components:
- `templates/front/home.html`
- `templates/front/product.html`
- `templates/front/product-detail.html`
- `templates/front/cart.html`
- `templates/front/checkout.html`
- `templates/front/search.html`

## CSS Files

### Storefront CSS (`static/css/`)
- `components.css`
- `home.css`
- `product.css`
- `product-detail.css`
- `cart.css`
- `checkout.css`
- `search.css`
- `style.css` — legacy/simple layout CSS, not the main active styling source

### Admin CSS (`static/admin/css/`)
- `adminlte.css` (and `.min.css`, `.rtl.css`, `.map` variants)

### Admin JS (`static/admin/js/`)
- `adminlte.js` (and `.min.js`, `.map` variants)

### Other
- `static/style/main.css` — currently empty

## Design Direction
The original MK7 design style was restored and preserved for the storefront:
- Glass rounded navbar
- Playfair Display headings
- DM Sans body text
- Off-white background
- Rounded 24px cards
- Dark footer
- Fashion editorial layout

Checkout is intentionally removed from the navbar. It is reachable only from the cart page's checkout button.

## Product Images
Card/product images use:
```css
object-fit: cover;
object-position: top center;
```

Product/card image containers use portrait-style sizing where needed, such as `aspect-ratio: 4 / 5`.

Product detail page has:
- One large main image
- Three small thumbnail images underneath (from `product.images`)

The thumbnail row uses a fixed grid row height so thumbnail images fill the full height.

## Important User Preferences
- Keep the original MK7 visual design.
- Use Jinja loops for product cards.
- Use static data from `product.py`.
- Use integer dynamic product routes to avoid unsafe path strings.
- Store cart in cookies for now, not a database.
- Use local images from `static/image`.
- Keep checkout out of the main navigation.
- Make navigation/footer reusable components.
- Keep CSS in `static/css`, not inline inside each page.

## Search
Search was added to the shared navbar.

Search route:
- `/search?q=...`

Search behavior:
- Search only checks product titles/names.
- If a product title does not contain the typed text, it does not show.
- If the search input is empty and the user presses Enter, `/search` redirects back to `/product`.
- Search result product names highlight the matched text using a custom Jinja filter.

Search-related files:
- `app.py`
  - `search()` route
  - `highlight_query` template filter
- `product.py`
  - `search_products(query)`
- `templates/front/search.html`
- `static/css/search.css`
- `templates/components/navbar.html`
  - search form in the nav

## Product Card Hover Gallery
Product cards on the `/product` page show sub images when hovering.

Behavior:
- Hover over a product card image to show that product's next/sub image.
- Left and right buttons appear on hover.
- Clicking left/right cycles through that product's own `product.images` list.
- Mouse leave resets the card back to the main product image.
- Hover image transition is intentionally slower than left/right click transitions.

Timing:
- Hover fade: about `0.64s`
- Mouse leave reset: about `0.42s`
- Left/right click: about `0.24s`

Files:
- `product.py`
  - Adds `sub_images`
  - Adds `images`
- `templates/front/product.html`
  - Adds `data-images`
  - Adds gallery buttons
  - Adds JavaScript for image cycling
- `static/css/product.css`
  - Adds hover controls and transition styles

## Product Detail Images
Product detail small thumbnail images come from the same `product.images` list used by the product card hover gallery.

This keeps product cards and product detail pages consistent:
- Card hover gallery uses the product's own images.
- Product detail thumbnails use the product's own images.

## Homepage
The homepage hero uses a carousel background:
- `static/image/Carousel01.png`
- `static/image/Carousel02.png`
- `static/image/Carousel03.png`

Hero text has stronger contrast shadows for readability. A small text carousel runs under the hero copy.

The homepage product cards use the first four products from `product.py` and support the same product image hover/click gallery pattern as the product listing. The `+` add-to-cart control is styled as a round black button.

Featured products use `products[4:8]`.

## Product Listing
The product page has:
- An `All Products` section showing every product.
- Category sections below, grouped from `get_products_by_category()`.
- Category buttons: `All`, `Tops`, and `Sets`.

The category buttons start in the old right-side position beside the `All Products` heading. When the user scrolls past them, JavaScript fixes them under the navbar while keeping them aligned to the product container's right edge.

## Product Detail Related Products
Related products filter by both:
- same category
- same gender

Gender is inferred in `product.py` by `get_product_gender(product)`, checking `image` and `title`. It checks `woman` before `man` so `Woman` does not accidentally match `Man`.

Updated helper:
- `get_related_products(product_id)`

## Checkout Flow
Checkout has a real POST flow.

Routes:
- `/checkout` renders checkout.
- `/payment` handles POST checkout submission.

Checkout form collects:
- full name
- phone
- email
- address
- city
- zip code
- delivery note
- payment method

Payment section:
- Shows a QR code payment block.
- The current QR is CSS-generated as a placeholder because no real QR image asset exists yet.

`payment()` reads:
- cart cookie data
- mapped full cart items from `get_cart_items()`
- shipping/user form info
- payment method

It builds an `order_info` payload and sends it to Telegram.

After checkout submission:
- The checkout page shows a success message.
- The cart cookie is cleared.

Checkout order summary shows:
- product image
- product title
- category x quantity
- one-item price
- line subtotal
- order total

## Telegram Integration (Orders & Security Alerts)
Checkout payment sends order info and security/error events send alerts to the Telegram group (`@SV26_Shop`).

Telegram helper functions in [helpers.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/helpers.py):
- `format_order_for_telegram(order_info)`
- `send_order_to_telegram(order_info)`: returns `(True, "")` on success or `(False, reason)` on failure.
- `send_telegram_alert(e)`: sends security/error notifications to the Telegram group for HTTP 429 (Rate Limit Exceeded) and HTTP 500 (Internal Server Error). Takes `e` (the error event object parameter from `@app.errorhandler`) and includes the status code, request method, request path, client public IP, `repr(e)`, exception type, description, and blocking duration. For HTTP 429, it tracks active block expiration (`_active_429_blocks`) using `limiter.current_limit.reset_at` so only ONE alert is sent per blocking period; repeated reloads/visits while the block remains active are suppressed to prevent spam.

Telegram credentials:
- `TELEGRAM_BOT_TOKEN` in [config.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/config.py)
- `TELEGRAM_CHAT_ID` in [config.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/config.py) (currently `@SV26_Shop`)
- Can also come from environment variables `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

Note: the bot token was accidentally put into `TELEGRAM_BOT_TOKEN_ENV`; the sender tolerates that case by treating `TELEGRAM_BOT_TOKEN_ENV` as a token if it contains `:`.

For groups, `TELEGRAM_CHAT_ID` usually needs a negative numeric ID such as `-1001234567890`. If using `@name`, it must be a real public group/channel username and the bot must be a member.

## Post-Payment Checkout Screen
After submitting `/payment`, the checkout page no longer shows:
- `1. Shipping Info`
- `2. QR Code Payment`
- Pay button

Instead it shows:
- order result message
- `Continue Shopping` button
- order/product summary

### Customer-Facing Order Result
Telegram-specific wording was removed from the customer-facing checkout result.

Success state:
- `Order Confirmed`
- `Your order has been placed successfully.`
- Thank-you message with customer name.

Failure state:
- `Order Not Confirmed`
- `We could not complete your order.`
- A cleaner failure reason appears below.

### Apple Pay-Style Success Alert
When the order is confirmed, checkout shows an Apple Pay-style success alert:
- fixed at the top center of the screen
- above the navbar
- green circular alert
- white tick centered inside the circle
- appears for about 3 seconds
- then slowly fades/floats upward and disappears

The alert markup is in `templates/front/checkout.html`:
- `.apple-pay-success`
- `.ap-ring`
- `.ap-ripple`
- `.ap-check`
- `.ap-path`

The animation CSS is in `static/css/checkout.css`.

Important animation note:
- The green circle and tick are separate elements.
- The tick originally stayed visible after the circle disappeared because only `.ap-ring` had the exit animation.
- The fix was to add `apAlertExit` to the `.apple-pay-success` wrapper, so the whole alert disappears together.

## Admin Panel
An AdminLTE-based admin panel.

### Admin Architecture
- Uses **AdminLTE** CSS and JS framework (local files, not CDN).
- Master layout: `templates/admin/master.html`
  - Includes admin components via `{% include %}`: header, navbar, sidebar, footer, scripts.
- Admin pages extend `master.html`.

### Admin Sidebar Active State
The sidebar uses a `module` variable to determine the active tab.

Each admin route passes `module` to the template:
```python
@app.route("/admin/dashboard")
def dashboard():
    module = "dashboard"
    return render_template("admin/dashboard.html", module=module)
```

The sidebar template checks:
```html
class="nav-link {{ 'active' if module == 'dashboard' else '' }}"
```

### Admin Sidebar
The sidebar contains only two items:
- **Dashboard** — direct link to `/admin/dashboard`
- **Users** — direct link to `/admin/users`

All AdminLTE demo items (Theme Generate, Widgets, Layout Options, UI Elements, Mailbox, Forms, Tables, Pages, Examples, Multi Level, Labels, Docs CTA) were removed.

### Admin Static Files
- CSS: `static/admin/css/adminlte.css` (+ minified, RTL, and sourcemap variants)
- JS: `static/admin/js/adminlte.js` (+ minified and sourcemap variants)
- Assets: `static/admin/assets/img/`

### Admin Components
- `templates/admin/components/header.html` — HTML head and opening tags
  - Body tag has inline `style="background-color: #f0f2f5;"` to prevent white flash on page load
  - `adminlte.css` is loaded once (duplicate was removed)
- `templates/admin/components/navbar.html` — top admin navbar
- `templates/admin/components/sidebar.html` — left sidebar (Dashboard + Users only)
- `templates/admin/components/footer.html` — admin footer
- `templates/admin/components/scripts.html` — JS includes
  - CDN library tags: OverlayScrollbars, Popper, Bootstrap 5, Sortable, ApexCharts, jsVectorMap
  - Local: `adminlte.js`
  - OverlayScrollbars config and Color Mode toggle scripts
  - Dashboard-specific chart/map rendering scripts

### Admin Pages
- **Dashboard** (`/admin/dashboard`): Shows stat widgets (New Orders, Bounce Rate, User Registrations, Unique Visitors) and charts (Sales Value area chart, World Map, sparklines). Uses hardcoded static values.
- **Users** (`/admin/users`): Shows a user management table with columns: ID, Profile, Name, Email, Role, Status, Created At, Actions (Edit/Delete). Profile column shows a 36×36 rounded-circle avatar image (`avatar.png`). Uses hardcoded static sample data (5 users). Has an "Add User" button (`bi-person-plus-fill` icon) in the card header linking to `/admin/users/add`. Edit buttons have `bi-pencil-square` icon. Delete buttons have `bi-trash3` icon and store `data-user-id` and `data-user-name` attributes for the delete modal.
- **Add User** (`/admin/users/add`): A form page (centered, `col-md-8 offset-md-2`) for creating new users. Card title has `bi-person-plus-fill` icon. Form fields use horizontal row layout (`col-sm-3` label / `col-sm-9` input):
  - Profile Image — 120×120 rounded-circle preview with click-to-choose; hidden `<input type="file">` triggered by "Choose Image" button (`bi-image` icon) or clicking the preview image; `FileReader` for client-side preview; preview resets on form reset.
  - Name (`bi-person` icon label) — text input, required
  - Email (`bi-envelope` icon label) — email input, required
  - Password (`bi-lock` icon label) — password input, required
  - Buttons: Back (`bi-arrow-left`, links to users list, left-aligned), Reset (`bi-arrow-counterclockwise`, warning color), Save Changes (`bi-check-lg`, success color, right-aligned)
  - Form uses `enctype="multipart/form-data"` for image upload.
  - POST handler in `app.py` reads `name`, `email`, `password`, `image` (file) — currently placeholder, no database.

### Admin User Delete (Popup Modal)
Delete confirmation uses a Bootstrap modal popup (`#deleteModal`) within the users page, powered by Axios.

Modal structure:
- `modal-dialog-centered` for vertical centering
- Header: `bg-danger text-white` with `bi-exclamation-triangle-fill` icon, title "Confirm Deletion", white close button
- Body: 80×80 rounded-circle profile image preview (`#deleteUserProfile`), "Are you sure you want to delete user **[Name]**?" with "This action cannot be undone." muted text
- Footer: Delete button (`btn-danger`, `me-auto` to push it **left**) and Cancel button (`btn-secondary`, **right** side)

Behavior:
- Each `.btn-delete` button stores `data-user-id`, `data-user-name`, and `data-user-profile`
- Clicking a delete button sets `currentUserId`, fills `#deleteUserName` with the user's name, sets `#deleteUserProfile` image src, and shows the modal via `bootstrap.Modal`
- On confirm, the Delete button is disabled and shows a `spinner-border` loading animation with "Deleting..." text
- Axios sends POST to `/admin/users/delete/<user_id>`
- On success (`.then`): the user's `<tr>` row is removed from DOM via `closest('tr').remove()`, modal hides
- On error (`.catch`): shows an alert "Failed to delete user"
- `.finally` resets button state and clears `currentUserId`
- Axios is loaded from CDN: `https://cdn.jsdelivr.net/npm/axios@1.7.9/dist/axios.min.js`
- The route `user_delete(user_id)` in `app.py` currently returns a placeholder JSON response (no database yet)

### Admin White Flash Fix
To prevent a white background flash when switching between admin pages:
- `<body>` has inline `style="background-color: #f0f2f5;"` matching AdminLTE's `bg-body-tertiary`
- Duplicate `adminlte.css` link was removed from `header.html`

### Front Base Template
A `templates/front/base.html` exists as a minimal base layout. It uses `static/css/style.css` and has a simple header with "Flask Store" branding. This is separate from the MK7 design used by the main storefront pages. The alternate `templates/front/product_detail.html` extends this base.

## Render Template Paths
All `render_template()` calls in `app.py` now use the `front/` prefix:
- `"front/home.html"`
- `"front/product.html"`
- `"front/product-detail.html"`
- `"front/search.html"`
- `"front/cart.html"`
- `"front/checkout.html"`
- `"admin/dashboard.html"`
- `"admin/user/user.html"`
- `"admin/user/add.html"`
- `"front/register.html"`

## Authentication, Rate Limiting & Cooldown Security

### 1. Dual-Track Login Limits

- **Page Refresh / Visit Limit**: 10 GET requests per minute per IP on `/admin/login` and `/login`.
- **Credential Attempt Limit**: 3 POST requests per minute per IP on `/admin/login` and `/login`.
- Exceeding either limit triggers HTTP 429 (Too Many Requests), issues a Telegram alert to administrators, and places the offending client IP in a 60-second cooldown ban.

### 2. Cooldown Timer Preservation ("Try Again" Fix)

- In `helpers.py`: `record_login_ban(duration=60)` and `record_signup_ban(duration=60)` check whether an active ban already exists for the IP (`existing_expiry > now`).
- If an active ban exists, the original expiration timestamp is **strictly preserved** and not reset.
- When an IP is banned on login or signup and repeatedly reloads or clicks "Try Again", the 429 page calculates `retry_after = int(ban_expiry - now)` and displays a live real-time countdown timer without extending the ban duration.
- The "Try Again" button dynamically updates with remaining seconds (`Try Again (35s)`) and unlocks (`Try Again Now`) once the cooldown finishes.
- The retry action performs a clean GET navigation (`retryRequest()`) to avoid browser "Confirm Form Resubmission" dialogs.

### 3. Sign Up Isolation & Rate Limiting

- **Independent Route**: `/register`, `/signup`, `/user/register` mapped to `front_bp.user_register` in `front/customer.py`.
- **Isolated Rate Limiting**: Dedicated rate limits (10/min GET, 5/min POST) separate from login endpoints.
- **Isolated Ban Tracking**: Separate `_signup_bans` and `is_ip_signup_banned()` prevent signup limits from interfering with login, and vice-versa.
- **No Cross-Route Blocking**: `user_register` does **NOT** check `is_ip_login_banned()`, and `user_login` does **NOT** check `is_ip_signup_banned()`. If an IP gets blocked on `/login`, they can freely access the Sign Up page and create an account unless they spam the Sign Up page itself.
- **Storefront Navbar Link**: The "Sign Up" button in `templates/components/navbar.html` points directly to `front_bp.user_register` instead of the admin-only user creation page.
- **Login Modal Link**: Added a "Don't have an account? Create an Account" link in `templates/admin/login.html` directing to `front_bp.user_register`.

### 4. Telegram Anti-Spam Alerts

- Telegram alert notifications (`helpers.py:send_telegram_alert`) use an in-memory anti-spam cooldown dictionary (`_telegram_alert_cooldowns`).
- Only 1 alert message is sent per IP per 60 seconds, preventing webhook flooding when bots or users spam requests during an active ban.

## Offline Dino Runner Arcade Component

- **File**: `templates/components/dino_game.html`
- **Embedded In**: `templates/429.html` and `templates/500.html` via `{% include "components/dino_game.html" %}`. *(Note: Commented off per user preference)*.
- **Visual Design**: Sleek mini-window matching MK7 luxury editorial styling (rounded 18px corners, frosted border, `JetBrains Mono` score readouts, responsive canvas).
- **Pixel-Art Graphics**: Self-contained vector/pixel bitmap rendering for the iconic Google Chrome T-Rex (stand, run, jump, duck, crash), cacti (small, double, large), flying pterodactyl birds, drifting clouds, and horizon ground texture.
- **Progressive Speed Curve**: Starts at a gentle, relaxed pace (`START_SPEED = 3.6`) with a 2-second initial runway, then smoothly accelerates based on score (`speed = min(13.0, 3.6 + score^0.72 * 0.065)`). The longer the player runs, the faster and more thrilling the challenge becomes.
- **Speed-Adapted Mechanics**:
  - Footstep running animation dynamically accelerates with speed.
  - Obstacle spawn spacing automatically widens at higher speeds to guarantee fair, jumpable gaps.
- **Audio & Controls**:
  - Audio generated via HTML5 Web Audio API oscillators (jump beep, 100-point milestone chime, crash sound) with a mute button persisted in `localStorage`.
  - Playable via keyboard (`Space` or `Up Arrow` to jump, `Down Arrow` to duck) or tap/click anywhere on the canvas. Spacebar scrolling is suppressed while playing.
  - High score saved in browser `localStorage`.

## Security Telemetry, Activity Logging & Audit Trail System

### 1. Phnom Penh, Cambodia (UTC+7 / ICT) Timestamp Standard

- **Timezone Definition**: In `models/activity_log.py`, `CAMBODIA_TZ = timezone(timedelta(hours=7))` with helper `get_cambodia_now()`.
- **Database Model Default**: All rows inserted into `activity_log` set `created_at` automatically using `get_cambodia_now()`.
- **Display & Alerts**: Admin UI table, modal telemetry readouts, card footers, and Telegram alert headers explicitly display timestamps in `Asia/Phnom_Penh (UTC+7)`.

### 2. Strict Audit Log Filtering (Rate Limits & 500s Only)

- In `helpers.py:log_activity()`, persistence to the database is strictly filtered to security and server incidents:
  - Allowed Actions: `USER_RATE_LIMIT`, `IP_RATE_LIMIT`, `500_INTERNAL_ERROR` (and `500_ERROR`, `RATE_LIMIT`).
  - Routine events (e.g. regular logins, CRUD updates) are deliberately skipped from the security audit log to maintain high signal-to-noise ratio.
- Automatic payload extraction: Saves endpoint, method, route parameters, exception signatures, and user context as formatted JSON in `new_data`.

### 3. Differentiated Telegram Security Dispatcher

In `helpers.py:send_telegram_alert(e)`, notifications sent to the Telegram group (`@SV26_Shop`) feature tailored formatting and distinct badges:

1. **User ID Rate Limit Ban (`USER_RATE_LIMIT`)**:
   - Header: `🚨 SECURITY ALERT: USER RATE LIMIT BAN (429)`
   - Telemetry details: User ID (`#user_id`), Username, User Role (`admin`/`user`), Endpoint, HTTP Method, Client IP, Cooldown (~60s), Policy (`10 requests / min (User ID)`), and Cambodia UTC+7 Timestamp.
2. **Network IP Rate Limit Ban (`IP_RATE_LIMIT`)**:
   - Header: `🚨 SECURITY ALERT: IP RATE LIMIT BAN (429)`
   - Telemetry details: Offending Client IP, User (`Unauthenticated Guest`), Endpoint, HTTP Method, Cooldown (~60s), Policy (`5 failed attempts / min (IP)`), and Cambodia UTC+7 Timestamp.
3. **HTTP 500 Internal Server Error (`500_INTERNAL_ERROR`)**:
   - Header: `🔥 CRITICAL SERVER ERROR: HTTP 500`
   - Telemetry details: Exception Type (e.g., `ZeroDivisionError`), Request Path, HTTP Method, Client IP, User Context, Traceback snippet, and Cambodia UTC+7 Timestamp.

### 4. Audit Log Entry Details Modal (`#logDetailsModal`)

- **File**: `templates/admin/activity_log/index.html`
- **Dynamic Theming**:
  - `USER_RATE_LIMIT`: Deep purple gradient header (`linear-gradient(135deg, #581c87 0%, #3b0764 100%)`) with warning status badge and user slash icon.
  - `IP_RATE_LIMIT`: Rich crimson gradient header (`linear-gradient(135deg, #881337 0%, #4c0519 100%)`) with danger status badge and shield slash icon.
  - `500_INTERNAL_ERROR`: Flame red gradient header (`linear-gradient(135deg, #7f1d1d 0%, #450a0a 100%)`) with critical fire icon.
- **4 Telemetry Inspection Cards**:
  1. *Network Route & Method*: HTTP verb badge, request path, full client IP.
  2. *Incident Target Identity*: Differentiates authenticated User ID/role vs anonymous IP.
  3. *Enforced Policy & Cooldown*: Displays throttling rule (e.g. 10/min vs 5/min) and cooldown seconds.
  4. *Technical Signature*: Incident category, database record ID, and client user-agent.
- **Full-Width JSON Inspector**: If no previous state (`old_data`) exists, `new_data` automatically spans full 12 columns with syntax highlighting and a 1-click "Copy JSON" button.
- **Pixel-Perfect Close Button ("X") Fix**:
  - Fixed Bootstrap 5's `.modal-header .btn-close` default styling which injected negative margins (`margin-top: -0.5rem`, `margin-right: -0.5rem`, `margin-left: auto`) and 50% opacity, causing the button to look misaligned, cut off, or disabled.
  - Replaced with dedicated `.btn-modal-close` element: circular frosted glass button (`32px × 32px`, `margin: 0 !important`), full-contrast pure white `<i class="bi bi-x-lg"></i>` icon, scale micro-animations on hover/active, and dual dismiss handling (`data-bs-dismiss="modal"` + direct JavaScript `modal.hide()`).

## Storefront Dynamic Database Categories

- **Dynamic Data Source**: [api/product.py:get_products_by_category()](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/api/product.py) dynamically queries all categories from the `Category` database table (`Category.query.order_by(Category.id.asc()).all()`).
- **Data Structure (`CategorySectionsList`)**: Returns a custom list of category section objects supporting both iteration in Jinja templates (`for section in category_sections`) and dictionary subscripting (`category_sections['tops']`).
- **Storefront Navigation & Sections**:
  - Filter Bar on [templates/front/product.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/front/product.html): renders filter pills for `All` and all database categories (`Tops`, `Sets`, `Outerwear`, `Accessories`, etc.) with product piece count badges (`.category-pill-count`).
  - Category Sections: each category renders its collection grid with its title, piece count, description, product cards, and live stock pills.
  - Empty Category Graceful State: empty categories render a chic `.empty-category-card` placeholder ("New Pieces Arriving Soon") instead of a broken empty row.
  - Category Subtitle on Cards: displays formatted `category_name` or capitalized category across [home.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/front/home.html), [product.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/front/product.html), [search.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/front/search.html), and [product-detail.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/front/product-detail.html).
  - Smooth Scrolling & Filtering: supports URL query param `?category=<slug>` and clicking category pills to smoothly jump to the respective category collection.

## Admin Dashboard Real-Time Analytics

- **Controller**: [admin/dashboard.py](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/admin/dashboard.py)
  - Fetches live statistics from SQLAlchemy:
    - **Gross Revenue**: sums `Order.total` where `status != 'cancelled'`.
    - **Orders & Status Breakdown**: total orders, pending count, confirmed, delivered, and cancelled.
    - **Inventory & Stock Tracking**: total products, total inventory units (`sum(Product.stock)`), out-of-stock items, and low-stock alerts ($\le 15$ units).
    - **Account Demographics**: customer users vs admin users.
    - **Category & Brand Ratios**: calculates product distribution percentages per registered category.
    - **7-Day Dynamic Chart Trajectory**: groups orders and sales into a past-7-day timeline.
    - **Recent Orders & Audit Logs**: latest orders and security logs.
- **View**: [templates/admin/dashboard.html](file:///d:/Document/CODES%20DEV/SV2-Y3/Phython/FlaskProject/templates/admin/dashboard.html)
  - 4 real-time stat cards with live counters and badges.
  - Interactive dual-axis ApexCharts area & column graph driven by real daily revenue and orders volume.
  - Management shortcuts with live pending and item counter badges.
  - Recent customer orders table with order numbers, email, items, amount, status pill, and direct links.
  - Category distribution progress bars and low-stock inventory alerts card.
