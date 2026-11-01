from extensions import db
from models.activity_log import get_cambodia_now


class Category(db.Model):
    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=get_cambodia_now, nullable=False)

    products = db.relationship("Product", backref="category", lazy=True, cascade="all")

    def __init__(self, name, slug=None, description=None, image=None, created_at=None):
        self.name = name
        self.slug = slug or name.lower().replace(" ", "-").replace("/", "-")
        self.description = description
        self.image = image
        self.created_at = created_at or get_cambodia_now()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description or "",
            "image": self.image or "",
            "products_count": len(self.products) if self.products else 0,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
