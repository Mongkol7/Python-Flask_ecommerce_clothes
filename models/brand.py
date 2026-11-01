from extensions import db
from models.activity_log import get_cambodia_now


class Brand(db.Model):
    __tablename__ = "brand"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    logo = db.Column(db.String(255), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=get_cambodia_now, nullable=False)

    products = db.relationship("Product", backref="brand", lazy=True, cascade="all")

    def __init__(self, name, slug=None, description=None, logo=None, website=None, created_at=None):
        self.name = name
        self.slug = slug or name.lower().replace(" ", "-").replace("/", "-")
        self.description = description
        self.logo = logo
        self.website = website
        self.created_at = created_at or get_cambodia_now()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description or "",
            "logo": self.logo or "",
            "website": self.website or "",
            "products_count": len(self.products) if self.products else 0,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
