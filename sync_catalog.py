import json
import sys
from app import app
from extensions import db
from models.product import Product
from models.category import Category
from models.brand import Brand
from models.users import User
from werkzeug.security import generate_password_hash
from api.product import static_products

def sync_all(admin_password="123456"):
    with app.app_context():
        db.create_all()

        # 1. Sync Categories & Brands
        cat_map = {c.slug.lower(): c.id for c in Category.query.all()}
        brand_map = {b.slug.lower(): b.id for b in Brand.query.all()}

        # 2. Sync all 12 products with exact images from local DB
        print("\n[1/2] Syncing 12 products with exact matching images...")
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
        print("[OK] Products updated successfully.")

        # 3. Sync Admin & User Accounts from Local DB
        print("\n[2/2] Syncing Admin and User Accounts...")
        accounts = [
            {"username": "admin", "email": "admin@gmail.com", "role": "admin", "profile": "Frog_standing.jpg"},
            {"username": "admin_test", "email": "admin_test@mk7.com", "role": "admin", "profile": "space17.jpg"},
            {"username": "admin02", "email": "admin02@gmail.com", "role": "admin", "profile": None},
            {"username": "mongkol009", "email": "mongkol009@gmail.com", "role": "user", "profile": "002.jpg"},
            {"username": "Test", "email": "test@gmail.com", "role": "user", "profile": "FinalCutPro.png"},
        ]

        for acc in accounts:
            user = User.query.filter((User.username == acc["username"]) | (User.email == acc["email"])).first()
            if not user:
                user = User(
                    username=acc["username"],
                    email=acc["email"],
                    password=generate_password_hash(admin_password),
                    role=acc["role"],
                    profile=acc.get("profile"),
                )
                db.session.add(user)
                print(f" + Created account '{acc['username']}' ({acc['role']}).")
            else:
                user.role = acc["role"]
                user.password = generate_password_hash(admin_password)
                if acc.get("profile"):
                    user.profile = acc["profile"]
                print(f" ~ Updated account '{acc['username']}' ({acc['role']}) password.")

        db.session.commit()
        print(f"[OK] All accounts synchronized. Default password for all: '{admin_password}'")

        print("\n=======================================================")
        print("SUCCESS: FULL DATABASE SYNC COMPLETE!")
        print("Admin Login Portal: /admin/login")
        print(f"Admin Username:     admin (or admin@gmail.com)")
        print(f"Admin Password:     {admin_password}")
        print("=======================================================\n")

if __name__ == "__main__":
    pwd = sys.argv[1] if len(sys.argv) > 1 else "123456"
    sync_all(pwd)
