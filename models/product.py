import json
from extensions import db
from models.activity_log import get_cambodia_now


class Product(db.Model):
    __tablename__ = "product"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id", ondelete="SET NULL"), nullable=True)
    brand_id = db.Column(db.Integer, db.ForeignKey("brand.id", ondelete="SET NULL"), nullable=True)
    image = db.Column(db.String(255), nullable=False)
    sub_images = db.Column(db.Text, nullable=True)  # JSON-encoded array of URLs
    stock = db.Column(db.Integer, default=50, nullable=False)
    rating_rate = db.Column(db.Float, default=4.8, nullable=False)
    rating_count = db.Column(db.Integer, default=120, nullable=False)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    gender = db.Column(db.String(50), nullable=True, default="woman")
    created_at = db.Column(db.DateTime, default=get_cambodia_now, nullable=False)

    def __init__(
        self,
        title,
        price,
        description=None,
        category_id=None,
        brand_id=None,
        image="/static/image/product/Man_Brown01.jpg",
        sub_images=None,
        stock=50,
        rating_rate=4.8,
        rating_count=120,
        is_featured=False,
        gender="woman",
        created_at=None,
    ):
        self.title = title
        self.price = float(price) if price is not None else 0.0
        self.description = description
        self.category_id = category_id
        self.brand_id = brand_id
        self.image = image
        self.set_sub_images(sub_images or [])
        self.stock = int(stock) if stock is not None else 50
        self.rating_rate = float(rating_rate) if rating_rate is not None else 4.8
        self.rating_count = int(rating_count) if rating_count is not None else 120
        self.is_featured = bool(is_featured)
        self.gender = gender or "woman"
        self.created_at = created_at or get_cambodia_now()

    @property
    def thumbnail(self):
        """Returns the low-quality / compressed thumbnail URL for listing cards, falling back to full image."""
        if not self.image:
            return "/static/image/product/Man_Brown01.jpg"

        parts = self.image.rsplit("/", 1)
        if len(parts) == 2:
            filename = parts[1]
            if filename.startswith("thum_"):
                return self.image
            thum_rel_path = f"{parts[0]}/thum_{filename}"
            import os
            from config import Config
            disk_path = os.path.join(Config.UPLOAD_PRODUCT_FOLDER, f"thum_{filename}")
            if os.path.exists(disk_path):
                return thum_rel_path
        return self.image

    def get_sub_images(self):
        if not self.sub_images:
            return []
        try:
            parsed = json.loads(self.sub_images)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return []

    def set_sub_images(self, images_list):
        if isinstance(images_list, list):
            self.sub_images = json.dumps(images_list)
        elif isinstance(images_list, str):
            self.sub_images = images_list
        else:
            self.sub_images = "[]"

    def get_all_images(self):
        subs = self.get_sub_images()
        if self.image:
            return [self.image] + [img for img in subs if img != self.image]
        return subs

    def to_dict(self):
        category_slug = self.category.slug if self.category else "tops"
        category_name = self.category.name if self.category else "General"
        brand_name = self.brand.name if self.brand else "MK7 Studio"
        subs = self.get_sub_images()
        all_imgs = self.get_all_images()

        return {
            "id": self.id,
            "title": self.title,
            "price": round(float(self.price), 2),
            "description": self.description or "",
            "category": category_slug,
            "category_id": self.category_id,
            "category_name": category_name,
            "brand": brand_name,
            "brand_id": self.brand_id,
            "image": self.image,
            "thumbnail": self.thumbnail,
            "sub_images": subs,
            "images": all_imgs,
            "rating": {"rate": self.rating_rate, "count": self.rating_count},
            "stock": self.stock,
            "gender": self.gender,
            "is_featured": self.is_featured,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
