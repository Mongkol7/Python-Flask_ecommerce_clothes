from extensions import db
from models.category import Category
from models.brand import Brand
from models.product import Product


def seed_database():
    """Seeds default categories, brands, and the 12 fashion products if tables are empty."""
    db.create_all()

    # 1. Seed Categories if empty
    cat_map = {}
    if Category.query.count() == 0:
        default_categories = [
            Category(name="Tops", slug="tops", description="Tops, shirts, tees, and refined knits"),
            Category(name="Sets", slug="sets", description="Matching co-ord sets and luxury outfits"),
            Category(name="Outerwear", slug="outerwear", description="Jackets, trench coats, and tailored blazers"),
            Category(name="Accessories", slug="accessories", description="Leather goods, hats, and fine jewelry"),
        ]
        for cat in default_categories:
            db.session.add(cat)
        db.session.commit()

    for c in Category.query.all():
        cat_map[c.slug.lower()] = c.id
        cat_map[c.name.lower()] = c.id

    # 2. Seed Brands if empty
    brand_map = {}
    if Brand.query.count() == 0:
        default_brands = [
            Brand(name="MK7 Studio", slug="mk7-studio", description="Signature in-house luxury editorial fashion", website="https://mk7fashion.com"),
            Brand(name="Minimalist Co.", slug="minimalist-co", description="Clean silhouettes and modern monochrome", website="https://minimalist.co"),
            Brand(name="Urban Edition", slug="urban-edition", description="Contemporary streetwear tailored for everyday elegance", website="https://urbanedition.style"),
            Brand(name="Atelier Chic", slug="atelier-chic", description="Refined materials and bespoke craftsmanship", website="https://atelierchic.fr"),
        ]
        for b in default_brands:
            db.session.add(b)
        db.session.commit()

    for b in Brand.query.all():
        brand_map[b.slug.lower()] = b.id
        brand_map[b.name.lower()] = b.id

    default_brand_id = Brand.query.first().id if Brand.query.first() else None

    # 3. Seed Products if empty
    if Product.query.count() == 0:
        try:
            # Import static products list
            from api.product import products as static_products

            for item in static_products:
                cat_slug = str(item.get("category", "tops")).lower()
                category_id = cat_map.get(cat_slug) or cat_map.get("tops")

                # Alternate brands for realistic catalog
                brand_id = default_brand_id
                if item["id"] % 4 == 0:
                    brand_id = brand_map.get("atelier-chic", default_brand_id)
                elif item["id"] % 3 == 0:
                    brand_id = brand_map.get("urban-edition", default_brand_id)
                elif item["id"] % 2 == 0:
                    brand_id = brand_map.get("minimalist-co", default_brand_id)
                else:
                    brand_id = brand_map.get("mk7-studio", default_brand_id)

                # Infer gender
                img_name = str(item.get("image", "")).lower()
                gender = "woman" if "woman" in img_name else ("man" if "man" in img_name else "unisex")

                rating_data = item.get("rating", {})
                rate = rating_data.get("rate", 4.8) if isinstance(rating_data, dict) else 4.8
                count = rating_data.get("count", 120) if isinstance(rating_data, dict) else 120

                prod = Product(
                    title=item["title"],
                    price=item["price"],
                    description=item.get("description", ""),
                    category_id=category_id,
                    brand_id=brand_id,
                    image=item["image"],
                    sub_images=item.get("sub_images", []),
                    stock=50 + (item["id"] * 5),
                    rating_rate=rate,
                    rating_count=count,
                    is_featured=(item["id"] in [1, 2, 5, 8]),
                    gender=gender,
                )
                db.session.add(prod)

            db.session.commit()
            print("Successfully seeded catalog: categories, brands, and products.")
        except Exception as e:
            db.session.rollback()
            print(f"Error seeding products: {e}")
