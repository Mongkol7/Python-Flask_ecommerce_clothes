from flask import request, jsonify
from extensions import db
from models.product import Product
from models.category import Category
from models.brand import Brand
from . import api_bp
from .jwt_auth import jwt_admin_required

# Static Product Data (Kept as seed source and reliable offline fallback)
static_products = [
    {
        "id": 1,
        "title": "Contrast Bow Ribbed Crop Top",
        "price": 150.00,
        "description": "A fitted ribbed crop top with contrast trim and a small bow detail.",
        "category": "tops",
        "category_id": 1,
        "category_name": "Tops",
        "brand": "MK7 Studio",
        "brand_id": 1,
        "image": "/static/image/product/Man_Brown01.jpg",
        "sub_images": [
            "/static/image/product/Man_Brown02.jpg",
            "/static/image/product/Man_Brown03.jpg",
        ],
        "images": [
            "/static/image/product/Man_Brown01.jpg",
            "/static/image/product/Man_Brown02.jpg",
            "/static/image/product/Man_Brown03.jpg",
        ],
        "rating": {"rate": 4.8, "count": 124},
        "stock": 55,
        "gender": "woman",
        "is_featured": True,
    },
    {
        "id": 2,
        "title": "Soft Cream Ribbed Baby Tee",
        "price": 120.00,
        "description": "A light everyday baby tee with a close fit and soft rib texture.",
        "category": "tops",
        "category_id": 1,
        "category_name": "Tops",
        "brand": "Minimalist Co.",
        "brand_id": 2,
        "image": "/static/image/product/Woman_Brown01.jpg",
        "sub_images": [
            "/static/image/product/Woman_Brown02.jpg",
            "/static/image/product/Woman_Brown03.jpg",
        ],
        "images": [
            "/static/image/product/Woman_Brown01.jpg",
            "/static/image/product/Woman_Brown02.jpg",
            "/static/image/product/Woman_Brown03.jpg",
        ],
        "rating": {"rate": 4.7, "count": 98},
        "stock": 60,
        "gender": "woman",
        "is_featured": True,
    },
    {
        "id": 3,
        "title": "Minimal Knit Short Sleeve Top",
        "price": 180.00,
        "description": "A clean knit top designed for easy styling with tailored trousers or denim.",
        "category": "tops",
        "category_id": 1,
        "category_name": "Tops",
        "brand": "Urban Edition",
        "brand_id": 3,
        "image": "/static/image/product/Woman_Black01.jpg",
        "sub_images": [
            "/static/image/product/Woman_Black02.jpg",
            "/static/image/product/Woman_Black03.jpg",
        ],
        "images": [
            "/static/image/product/Woman_Black01.jpg",
            "/static/image/product/Woman_Black02.jpg",
            "/static/image/product/Woman_Black03.jpg",
        ],
        "rating": {"rate": 4.6, "count": 86},
        "stock": 45,
        "gender": "woman",
        "is_featured": False,
    },
    {
        "id": 4,
        "title": "Soft Sage Everyday Rib Top",
        "price": 100.00,
        "description": "A comfortable daily top in a muted sage tone with a gentle stretch feel.",
        "category": "tops",
        "category_id": 1,
        "category_name": "Tops",
        "brand": "Atelier Chic",
        "brand_id": 4,
        "image": "/static/image/product/Man_Green01.jpg",
        "sub_images": [
            "/static/image/product/Man_Green02.jpg",
            "/static/image/product/Man_Green03.jpg",
        ],
        "images": [
            "/static/image/product/Man_Green01.jpg",
            "/static/image/product/Man_Green02.jpg",
            "/static/image/product/Man_Green03.jpg",
        ],
        "rating": {"rate": 4.9, "count": 140},
        "stock": 70,
        "gender": "man",
        "is_featured": False,
    },
    {
        "id": 5,
        "title": "Minimal Olive Linen Blend Top",
        "price": 200.00,
        "description": "An airy linen blend top in an earthy olive shade for warm-weather layering.",
        "category": "tops",
        "category_id": 1,
        "category_name": "Tops",
        "brand": "MK7 Studio",
        "brand_id": 1,
        "image": "/static/image/product/Woman_Green01.jpg",
        "sub_images": [
            "/static/image/product/Woman_Green02.jpg",
            "/static/image/product/Woman_Green03.jpg",
        ],
        "images": [
            "/static/image/product/Woman_Green01.jpg",
            "/static/image/product/Woman_Green02.jpg",
            "/static/image/product/Woman_Green03.jpg",
        ],
        "rating": {"rate": 4.5, "count": 72},
        "stock": 40,
        "gender": "woman",
        "is_featured": True,
    },
    {
        "id": 6,
        "title": "Washed Denim Blue Fitted Top",
        "price": 160.00,
        "description": "A cool-toned blue top with subtle wash detailing and clean silhouette lines.",
        "category": "tops",
        "category_id": 1,
        "category_name": "Tops",
        "brand": "Minimalist Co.",
        "brand_id": 2,
        "image": "/static/image/product/Man_Blue01.jpg",
        "sub_images": [
            "/static/image/product/Man_Blue02.jpg",
            "/static/image/product/Man_Blue03.jpg",
        ],
        "images": [
            "/static/image/product/Man_Blue01.jpg",
            "/static/image/product/Man_Blue02.jpg",
            "/static/image/product/Man_Blue03.jpg",
        ],
        "rating": {"rate": 4.8, "count": 110},
        "stock": 65,
        "gender": "man",
        "is_featured": False,
    },
    {
        "id": 7,
        "title": "Dusty Sky Ribbed Scoop Neck",
        "price": 240.00,
        "description": "A soft dusty-blue scoop neck top designed to sit close and layer cleanly.",
        "category": "tops",
        "category_id": 1,
        "category_name": "Tops",
        "brand": "Urban Edition",
        "brand_id": 3,
        "image": "/static/image/product/Woman_Blue01.jpg",
        "sub_images": [
            "/static/image/product/Woman_Blue02.jpg",
            "/static/image/product/Woman_Blue03.jpg",
        ],
        "images": [
            "/static/image/product/Woman_Blue01.jpg",
            "/static/image/product/Woman_Blue02.jpg",
            "/static/image/product/Woman_Blue03.jpg",
        ],
        "rating": {"rate": 4.7, "count": 93},
        "stock": 50,
        "gender": "woman",
        "is_featured": False,
    },
    {
        "id": 8,
        "title": "Tailored Minimal Black Co-ord Set",
        "price": 300.00,
        "description": "A refined two-piece set featuring clean lines and a relaxed tailored drape.",
        "category": "sets",
        "category_id": 2,
        "category_name": "Sets",
        "brand": "MK7 Studio",
        "brand_id": 1,
        "image": "/static/image/product/Man_Black02.jpg",
        "sub_images": [
            "/static/image/product/Man_Black022.jpg",
            "/static/image/product/Man_Black01.jpg",
        ],
        "images": [
            "/static/image/product/Man_Black02.jpg",
            "/static/image/product/Man_Black022.jpg",
            "/static/image/product/Man_Black01.jpg",
        ],
        "rating": {"rate": 4.9, "count": 156},
        "stock": 35,
        "gender": "man",
        "is_featured": True,
    },
    {
        "id": 9,
        "title": "Pleated Linen Summer Co-ord Set",
        "price": 280.00,
        "description": "A lightweight two-piece matching set created for warm sunny weekends.",
        "category": "sets",
        "category_id": 2,
        "category_name": "Sets",
        "brand": "Atelier Chic",
        "brand_id": 4,
        "image": "/static/image/product/Woman_Black02.jpg",
        "sub_images": [
            "/static/image/product/Woman_Black022.jpg",
            "/static/image/product/Woman_Black03.jpg",
        ],
        "images": [
            "/static/image/product/Woman_Black02.jpg",
            "/static/image/product/Woman_Black022.jpg",
            "/static/image/product/Woman_Black03.jpg",
        ],
        "rating": {"rate": 4.8, "count": 132},
        "stock": 42,
        "gender": "woman",
        "is_featured": False,
    },
    {
        "id": 10,
        "title": "Relaxed Brown Structured Set",
        "price": 220.00,
        "description": "An effortless co-ord with structured shoulders and a modern warm-brown finish.",
        "category": "sets",
        "category_id": 2,
        "category_name": "Sets",
        "brand": "Minimalist Co.",
        "brand_id": 2,
        "image": "/static/image/product/Man_Brown02.jpg",
        "sub_images": [
            "/static/image/product/Man_Brown022.jpg",
            "/static/image/product/Man_Brown01.jpg",
        ],
        "images": [
            "/static/image/product/Man_Brown02.jpg",
            "/static/image/product/Man_Brown022.jpg",
            "/static/image/product/Man_Brown01.jpg",
        ],
        "rating": {"rate": 4.6, "count": 78},
        "stock": 38,
        "gender": "man",
        "is_featured": False,
    },
    {
        "id": 11,
        "title": "Oatmeal Knit Loungewear Set",
        "price": 250.00,
        "description": "A cozy two-piece knit set that balances loungewear ease with street readiness.",
        "category": "sets",
        "category_id": 2,
        "category_name": "Sets",
        "brand": "Urban Edition",
        "brand_id": 3,
        "image": "/static/image/product/Woman_Brown02.jpg",
        "sub_images": [
            "/static/image/product/Woman_Brown022.jpg",
            "/static/image/product/Woman_Brown03.jpg",
        ],
        "images": [
            "/static/image/product/Woman_Brown02.jpg",
            "/static/image/product/Woman_Brown022.jpg",
            "/static/image/product/Woman_Brown03.jpg",
        ],
        "rating": {"rate": 4.7, "count": 89},
        "stock": 48,
        "gender": "woman",
        "is_featured": False,
    },
    {
        "id": 12,
        "title": "Forest Green Casual Match Set",
        "price": 260.00,
        "description": "A deep green coordinated outfit with relaxed shorts and a matching short-sleeve shirt.",
        "category": "sets",
        "category_id": 2,
        "category_name": "Sets",
        "brand": "MK7 Studio",
        "brand_id": 1,
        "image": "/static/image/product/Man_Green02.jpg",
        "sub_images": [
            "/static/image/product/Man_Green02.jpg",
            "/static/image/product/Man_Green03.jpg",
        ],
        "images": [
            "/static/image/product/Man_Green02.jpg",
            "/static/image/product/Man_Green02.jpg",
            "/static/image/product/Man_Green03.jpg",
        ],
        "rating": {"rate": 4.9, "count": 164},
        "stock": 52,
        "gender": "man",
        "is_featured": False,
    },
]


def get_all_products_list():
    """Returns all products from the database, falling back to static list if DB is empty."""
    try:
        db_prods = Product.query.order_by(Product.id.asc()).all()
        if db_prods:
            return [p.to_dict() for p in db_prods]
    except Exception:
        pass
    return static_products


class ProductsProxy(list):
    """Dynamic list proxy ensuring existing imports get fresh database products."""
    def __iter__(self):
        return iter(get_all_products_list())

    def __len__(self):
        return len(get_all_products_list())

    def __getitem__(self, idx):
        return get_all_products_list()[idx]


products = ProductsProxy()


def get_product_by_id(product_id):
    """Finds product by integer ID from the database or fallback list."""
    try:
        p = Product.query.get(product_id)
        if p:
            return p.to_dict()
    except Exception:
        pass

    for item in static_products:
        if item["id"] == product_id:
            return item
    return None


class CategorySectionsList(list):
    """List of category section objects supporting iteration and dict-like lookup."""
    def __getitem__(self, key):
        if isinstance(key, str):
            for s in self:
                if s.get("slug") == key or s.get("label", "").lower() == key.lower():
                    return s.get("products", [])
            return []
        return super().__getitem__(key)

    def get(self, key, default=None):
        for s in self:
            if s.get("slug") == key or s.get("label", "").lower() == key.lower():
                return s.get("products", [])
        return default


def get_products_by_category():
    """
    Groups products by categories retrieved from the database.
    Returns a CategorySectionsList of sections:
    [
        {
            "id": cat.id,
            "label": cat.name,
            "slug": cat.slug,
            "description": cat.description or "",
            "image": cat.image or "",
            "products": [ ... ],
            "count": len(products),
        },
        ...
    ]
    """
    all_prods = get_all_products_list()
    sections = CategorySectionsList()

    try:
        categories = Category.query.order_by(Category.id.asc()).all()
    except Exception:
        categories = []

    seen_product_ids = set()

    if categories:
        for cat in categories:
            cat_slug = cat.slug.lower()
            cat_name = cat.name.lower()
            matching_products = [
                p for p in all_prods
                if p.get("category_id") == cat.id
                or str(p.get("category", "")).lower() == cat_slug
                or str(p.get("category_name", "")).lower() == cat_name
            ]
            for p in matching_products:
                seen_product_ids.add(p["id"])

            sections.append({
                "id": cat.id,
                "label": cat.name,
                "slug": cat.slug,
                "description": cat.description or "",
                "image": cat.image or "",
                "products": matching_products,
                "count": len(matching_products),
            })

    # Catch any orphan/static products whose category was not in Category table
    orphans = [p for p in all_prods if p["id"] not in seen_product_ids]
    if orphans:
        orphan_groups = {}
        for p in orphans:
            cat_name = p.get("category_name") or p.get("category", "Other")
            cat_slug = str(p.get("category") or cat_name).lower().replace(" ", "-")
            if cat_slug not in orphan_groups:
                orphan_groups[cat_slug] = {"label": cat_name.capitalize(), "slug": cat_slug, "products": []}
            orphan_groups[cat_slug]["products"].append(p)
        for og in orphan_groups.values():
            sections.append({
                "id": None,
                "label": og["label"],
                "slug": og["slug"],
                "description": "",
                "image": "",
                "products": og["products"],
                "count": len(og["products"]),
            })

    # Fallback if DB was completely empty and no categories existed
    if not sections and all_prods:
        raw_groups = {}
        for p in all_prods:
            c = p.get("category", "general").lower()
            if c not in raw_groups:
                raw_groups[c] = []
            raw_groups[c].append(p)
        for slug, prods in raw_groups.items():
            sections.append({
                "id": None,
                "label": slug.capitalize(),
                "slug": slug,
                "description": "",
                "image": "",
                "products": prods,
                "count": len(prods),
            })

    return sections


def get_product_gender(product):
    """Infers gender from product attributes or image filename."""
    if product.get("gender"):
        return str(product["gender"]).lower()
    gender_source = f"{product.get('image', '')} {product.get('title', '')}".lower()
    if "woman" in gender_source:
        return "woman"
    if "man" in gender_source:
        return "man"
    return "unisex"


def get_related_products(product_id):
    """Finds up to 4 related products sharing category and gender."""
    selected_product = get_product_by_id(product_id)
    if selected_product is None:
        return []

    selected_gender = get_product_gender(selected_product)
    selected_cat_id = selected_product.get("category_id")
    selected_cat = selected_product.get("category")

    related = []
    for p in get_all_products_list():
        if p["id"] == selected_product["id"]:
            continue
        same_cat = (p.get("category_id") == selected_cat_id) or (p.get("category") == selected_cat)
        same_gender = get_product_gender(p) == selected_gender
        if same_cat and same_gender:
            related.append(p)
        elif same_cat and len(related) < 4:
            related.append(p)

    return related[:4]


def get_cart_items(cart_cookie_data):
    """Hydrates cart items from product ID and quantity."""
    cart_items = []
    for cart_item in cart_cookie_data:
        p = get_product_by_id(cart_item.get("id"))
        if p is None:
            continue
        item = p.copy()
        item["qty"] = int(cart_item.get("qty", 1))
        item["subtotal"] = round(item["price"] * item["qty"], 2)
        cart_items.append(item)
    return cart_items


def search_products(query):
    """Searches products by title and description."""
    q_str = (query or "").strip().lower()
    if not q_str:
        return []

    try:
        db_matches = Product.query.filter(
            (Product.title.ilike(f"%{q_str}%")) | (Product.description.ilike(f"%{q_str}%"))
        ).all()
        if db_matches:
            return [p.to_dict() for p in db_matches]
    except Exception:
        pass

    return [p for p in static_products if q_str in p["title"].lower() or q_str in p.get("description", "").lower()]


# ==========================================
# REST API Endpoints
# ==========================================

@api_bp.route("/product", methods=["GET"])
@api_bp.route("/products", methods=["GET"])
def api_get_products():
    """
    List products from database with optional filters.
    Query params: category, brand, gender, search, featured
    """
    query = Product.query

    category_slug = request.args.get("category", "").strip().lower()
    if category_slug:
        cat = Category.query.filter((Category.slug == category_slug) | (Category.name.ilike(category_slug))).first()
        if cat:
            query = query.filter(Product.category_id == cat.id)

    brand_slug = request.args.get("brand", "").strip().lower()
    if brand_slug:
        b = Brand.query.filter((Brand.slug == brand_slug) | (Brand.name.ilike(brand_slug))).first()
        if b:
            query = query.filter(Product.brand_id == b.id)

    gender = request.args.get("gender", "").strip().lower()
    if gender:
        query = query.filter(Product.gender == gender)

    featured = request.args.get("featured", "").strip().lower()
    if featured in ("true", "1", "yes"):
        query = query.filter(Product.is_featured == True)

    search_term = request.args.get("search") or request.args.get("q")
    if search_term:
        term = f"%{search_term.strip()}%"
        query = query.filter((Product.title.ilike(term)) | (Product.description.ilike(term)))

    db_prods = query.order_by(Product.id.asc()).all()
    if db_prods:
        return jsonify([p.to_dict() for p in db_prods]), 200

    return jsonify(static_products), 200


@api_bp.route("/product/<int:product_id>", methods=["GET"])
@api_bp.route("/products/<int:product_id>", methods=["GET"])
def api_get_product_detail(product_id):
    """Retrieve single product by ID."""
    p = Product.query.get(product_id)
    if p:
        return jsonify(p.to_dict()), 200

    for item in static_products:
        if item["id"] == product_id:
            return jsonify(item), 200

    return jsonify({"success": False, "error": "Product not found"}), 404


@api_bp.route("/products", methods=["POST"])
@jwt_admin_required
def api_create_product():
    """Create a new product via JSON (Requires Admin JWT)."""
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    price = data.get("price")

    if not title or price is None:
        return jsonify({"success": False, "error": "Title and price are required."}), 400

    new_prod = Product(
        title=title,
        price=float(price),
        description=data.get("description"),
        category_id=data.get("category_id"),
        brand_id=data.get("brand_id"),
        image=data.get("image") or "/static/image/product/Man_Brown01.jpg",
        sub_images=data.get("sub_images") or [],
        stock=data.get("stock", 50),
        rating_rate=data.get("rating_rate", 4.8),
        rating_count=data.get("rating_count", 100),
        is_featured=bool(data.get("is_featured", False)),
        gender=data.get("gender", "woman"),
    )
    db.session.add(new_prod)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Product created successfully.",
        "product": new_prod.to_dict(),
    }), 201


@api_bp.route("/products/<int:product_id>", methods=["PUT", "PATCH"])
@jwt_admin_required
def api_update_product(product_id):
    """Update an existing product via JSON (Requires Admin JWT)."""
    p = Product.query.get(product_id)
    if not p:
        return jsonify({"success": False, "error": "Product not found"}), 404

    data = request.get_json(silent=True) or {}
    if "title" in data and data["title"].strip():
        p.title = data["title"].strip()
    if "price" in data and data["price"] is not None:
        p.price = float(data["price"])
    if "description" in data:
        p.description = data["description"]
    if "category_id" in data:
        p.category_id = data["category_id"]
    if "brand_id" in data:
        p.brand_id = data["brand_id"]
    if "image" in data and data["image"]:
        p.image = data["image"]
    if "sub_images" in data:
        p.set_sub_images(data["sub_images"])
    if "stock" in data and data["stock"] is not None:
        p.stock = int(data["stock"])
    if "rating_rate" in data:
        p.rating_rate = float(data["rating_rate"])
    if "rating_count" in data:
        p.rating_count = int(data["rating_count"])
    if "is_featured" in data:
        p.is_featured = bool(data["is_featured"])
    if "gender" in data:
        p.gender = data["gender"]

    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Product updated successfully.",
        "product": p.to_dict(),
    }), 200


@api_bp.route("/products/<int:product_id>", methods=["DELETE"])
@jwt_admin_required
def api_delete_product(product_id):
    """Delete a product from the catalog (Requires Admin JWT)."""
    p = Product.query.get(product_id)
    if not p:
        return jsonify({"success": False, "error": "Product not found"}), 404

    db.session.delete(p)
    db.session.commit()
    return jsonify({
        "success": True,
        "message": f"Product #{product_id} deleted successfully.",
    }), 200
