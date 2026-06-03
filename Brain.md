# Project Brain

## Project
Flask Jinja storefront for MK7, a fashion-style shop using static Python product data and local image assets. The project does not use a database yet.

## Current App Shape
- Main Flask app: `app.py`
- Product data/helpers: `product.py`
- Templates: `templates/`
- Shared Jinja components: `templates/components/`
- CSS files: `static/css/`
- Local product images: `static/image/`

## Routes
- `/` renders the MK7 homepage from `templates/home.html`.
- `/product` renders the product listing from `templates/product.html`.
- `/product/<int:product_id>` renders product detail from `templates/product-detail.html`.
- `/product-detail/<int:product_id>` is kept as an old compatible detail route.
- `/cart` renders the cart. If `?product_id=ID` is present, it adds that product to the cart cookie and redirects to `/cart`.
- `/cart/update` handles POST actions: `plus`, `minus`, and `remove`.
- `/checkout` renders `templates/checkout.html`.

## Product Data
`product.py` stores static fashion product dictionaries with:
- `id`
- `title`
- `price`
- `description`
- `category`
- `image`
- `rating: {rate, count}`

Images are local paths such as `/static/image/01.jpg`.

Helpers in `product.py`:
- `get_product_by_id(product_id)`
- `get_related_products(product_id)`
- `get_cart_items(cart_cookie_data)`

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
- `inject_cart_count()`

This provides `cart_count` to templates for the navbar cart badge.

## Components
Navigation and footer were moved into shared Jinja components:
- `templates/components/navbar.html`
- `templates/components/footer.html`

Shared component CSS:
- `static/css/components.css`

All active pages include the component CSS and the shared navbar/footer.

Active pages using components:
- `templates/home.html`
- `templates/product.html`
- `templates/product-detail.html`
- `templates/cart.html`
- `templates/checkout.html`

## CSS Files
Page-level CSS was moved out of inline `<style>` blocks into:
- `static/css/home.css`
- `static/css/product.css`
- `static/css/product-detail.css`
- `static/css/cart.css`
- `static/css/checkout.css`
- `static/css/components.css`

Legacy/simple CSS file still exists:
- `static/css/style.css`

## Design Direction
The original MK7 design style was restored and preserved:
- Glass rounded navbar
- Playfair Display headings
- DM Sans body text
- Off-white background
- Rounded 24px cards
- Dark footer
- Fashion editorial layout

Checkout is intentionally removed from the navbar. It is reachable only from the cart page's checkout button.

## Product Images
Card/product images were adjusted to use:
```css
object-fit: cover;
object-position: top center;
```

Product/card image containers use portrait-style sizing where needed, such as `aspect-ratio: 4 / 5`, so clothing photos fit the cards more naturally.

Product detail page has:
- One large main image
- Three small thumbnail images underneath

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

## Recent Verification
The following routes were checked successfully during development:
- `/`
- `/product`
- `/product/1`
- `/cart`
- `/checkout`
- `/static/css/components.css`

All returned `200` after the most recent component refactor.

## Later Updates

### Search
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
- `templates/search.html`
- `static/css/search.css`
- `templates/components/navbar.html`
  - search form in the nav

### Product Card Hover Gallery
Product cards on the `/product` page now show sub images when hovering.

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
- `templates/product.html`
  - Adds `data-images`
  - Adds gallery buttons
  - Adds JavaScript for image cycling
- `static/css/product.css`
  - Adds hover controls and transition styles

### Product Detail Images
Product detail small thumbnail images now come from the same `product.images` list used by the product card hover gallery.

This keeps product cards and product detail pages consistent:
- Card hover gallery uses the product's own images.
- Product detail thumbnails use the product's own images.

File:
- `templates/product-detail.html`

### Component Refactor
Navbar and footer were extracted into reusable components:
- `templates/components/navbar.html`
- `templates/components/footer.html`

Shared component CSS:
- `static/css/components.css`

Active templates include the shared components:
- `templates/home.html`
- `templates/product.html`
- `templates/product-detail.html`
- `templates/cart.html`
- `templates/checkout.html`
- `templates/search.html`

The navbar cart badge uses `cart_count` from `app.py`.

### CSS Organization
Inline page styles were moved into page-specific CSS files in `static/css`.

Current CSS files:
- `components.css`
- `home.css`
- `product.css`
- `product-detail.css`
- `cart.css`
- `checkout.css`
- `search.css`
- `style.css` remains from the earlier simple layout but is not the main active styling source.

## Latest Updates

### Product Data Normalization
All 12 current products in `product.py` now store exactly three product images:
- `image`: main image
- `sub_images`: exactly two sub images
- `images`: exactly three images in display order

The product listing, homepage cards, hover galleries, product detail thumbnails, cart, checkout, and search all use this static data from `product.py`.

### Homepage
The homepage hero uses a carousel background:
- `static/image/Carousel01.png`
- `static/image/Carousel02.png`
- `static/image/Carousel03.png`

Hero text has stronger contrast shadows for readability. A small text carousel runs under the hero copy.

The homepage product cards use the first four products from `product.py` and support the same product image hover/click gallery pattern as the product listing. The `+` add-to-cart control is styled as a round black button.

### Product Listing
The product page has:
- An `All Products` section showing every product.
- Category sections below, grouped from `get_products_by_category()`.
- Category buttons: `All`, `Tops`, and `Sets`.

The category buttons start in the old right-side position beside the `All Products` heading. When the user scrolls past them, JavaScript fixes them under the navbar while keeping them aligned to the product container's right edge.

### Product Detail Related Products
Related products now filter by both:
- same category
- same gender

Gender is inferred in `product.py` by `get_product_gender(product)`, checking `image` and `title`. It checks `woman` before `man` so `Woman` does not accidentally match `Man`.

Updated helper:
- `get_related_products(product_id)`

### Cart Badge Count
The navbar cart badge now shows the number of different products in the cart, not the total quantity.

Example:
- Product 1 quantity `2`
- Product 2 quantity `1`
- Badge shows `2`

This is handled by:
- `inject_cart_count()` in `app.py`

### Checkout Flow
Checkout now has a real POST flow.

Routes:
- `/checkout` renders checkout.
- `/do_checkout` handles POST checkout submission.

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

`do_checkout()` reads:
- cart cookie data
- mapped full cart items from `get_cart_items()`
- shipping/user form info
- payment method

It builds an `order_info` payload and has a TODO for sending that data to Telegram later.

After checkout submission:
- The checkout page shows a success message.
- The cart cookie is cleared.

Checkout order summary now shows:
- product image
- product title
- category x quantity
- one-item price
- line subtotal
- order total

## Latest Checkout/Payment Updates

### Payment Route
The checkout POST route was renamed:
- Old: `/do_checkout`
- Current: `/payment`

The route function is now:
- `payment()` in `app.py`

The checkout form posts with:
- `url_for('payment')`

There should be no remaining `do_checkout` references.

### Telegram Order Sending
Checkout payment now attempts to send order info to a Telegram bot/group.

Telegram helper functions in `app.py`:
- `format_order_for_telegram(order_info)`
- `send_order_to_telegram(order_info)`

`send_order_to_telegram()` returns:
- `(True, "")` when Telegram accepts the message.
- `(False, reason)` when Telegram fails.

Telegram data can come from environment variables or file constants.

Environment variable names:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

File constants:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Note: the bot token was accidentally put into `TELEGRAM_BOT_TOKEN_ENV`; the sender now tolerates that case by treating `TELEGRAM_BOT_TOKEN_ENV` as a token if it contains `:`.

For groups, `TELEGRAM_CHAT_ID` usually needs a negative numeric ID such as `-1001234567890`. If using `@name`, it must be a real public group/channel username and the bot must be a member.

### Post-Payment Checkout Screen
After submitting `/payment`, the checkout page no longer shows:
- `1. Shipping Info`
- `2. QR Code Payment`
- Pay button

Instead it shows:
- order result message
- `Continue Shopping` button
- order/product summary

The order/product summary still shows after payment:
- product image
- product title
- category x quantity
- one-item price
- line subtotal
- total

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

The alert markup is in `templates/checkout.html`:
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
