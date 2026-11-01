# Static data has moved to api/product.py
# Re-exporting here maintains backwards compatibility with existing storefront routes
from api.product import (
    products,
    get_products_by_category,
    get_product_by_id,
    search_products,
    get_product_gender,
    get_related_products,
    get_cart_items,
)
