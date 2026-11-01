import json
from app import app
from extensions import db
from models.product import Product
from models.category import Category
from models.brand import Brand
from api.product import static_products

def sync_products():
    with app.app_context():
        print("Syncing 12 products with exact matching images from catalog...")
        for item in static_products:
            prod = db.session.get(Product, item["id"])
            if not prod:
                prod = Product(
                    title=item["title"],
                    price=item["price"],
                    description=item["description"],
                    image=item["image"],
                    sub_images=item.get("sub_images", []),
                    category_id=item.get("category_id", 1),
                    brand_id=item.get("brand_id", 1),
                    gender=item.get("gender", "unisex"),
                    stock=item.get("stock", 50),
                    is_featured=item.get("is_featured", False),
                )
                prod.id = item["id"]
                db.session.add(prod)
            else:
                prod.title = item["title"]
                prod.price = item["price"]
                prod.description = item["description"]
                prod.image = item["image"]
                prod.set_sub_images(item.get("sub_images", []))
                prod.gender = item.get("gender", prod.gender)
                prod.is_featured = item.get("is_featured", prod.is_featured)
                if item.get("category_id"):
                    prod.category_id = item["category_id"]
                if item.get("brand_id"):
                    prod.brand_id = item["brand_id"]

        db.session.commit()
        print("SUCCESS: All 12 products synced successfully with exact image sets!")
        print("\n--- Catalog Image Set Verification ---")
        for p in Product.query.order_by(Product.id.asc()).all():
            print(f" • #{p.id} {p.title} -> Main: {p.image} | Subs: {p.get_sub_images()}")
        print("---------------------------------------")

if __name__ == "__main__":
    sync_products()
