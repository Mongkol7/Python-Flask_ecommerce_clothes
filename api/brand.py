from flask import request, jsonify
from extensions import db
from models.brand import Brand
from . import api_bp
from .jwt_auth import jwt_admin_required


@api_bp.route("/brands", methods=["GET"])
def get_brands():
    """List all fashion brands with product counts."""
    brands = Brand.query.order_by(Brand.name.asc()).all()
    return jsonify([b.to_dict() for b in brands]), 200


@api_bp.route("/brands/<int:brand_id>", methods=["GET"])
def get_brand_detail(brand_id):
    """Get single brand details and its products."""
    brand = Brand.query.get(brand_id)
    if not brand:
        return jsonify({"success": False, "error": "Brand not found"}), 404

    data = brand.to_dict()
    data["products"] = [p.to_dict() for p in brand.products] if brand.products else []
    return jsonify(data), 200


@api_bp.route("/brands", methods=["POST"])
@jwt_admin_required
def create_brand():
    """Create a new brand (Requires Admin JWT)."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    slug = (data.get("slug") or name.lower().replace(" ", "-")).strip()
    description = (data.get("description") or "").strip()
    logo = data.get("logo")
    website = (data.get("website") or "").strip()

    if not name:
        return jsonify({"success": False, "error": "Brand name is required"}), 400

    if Brand.query.filter((Brand.name == name) | (Brand.slug == slug)).first():
        return jsonify({"success": False, "error": "Brand name or slug already exists"}), 409

    new_brand = Brand(name=name, slug=slug, description=description, logo=logo, website=website)
    db.session.add(new_brand)
    db.session.commit()

    return jsonify({"success": True, "message": "Brand created successfully", "brand": new_brand.to_dict()}), 201


@api_bp.route("/brands/<int:brand_id>", methods=["PUT", "PATCH"])
@jwt_admin_required
def update_brand(brand_id):
    """Update an existing brand (Requires Admin JWT)."""
    brand = Brand.query.get(brand_id)
    if not brand:
        return jsonify({"success": False, "error": "Brand not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"].strip():
        brand.name = data["name"].strip()
    if "slug" in data and data["slug"].strip():
        brand.slug = data["slug"].strip()
    if "description" in data:
        brand.description = data["description"]
    if "logo" in data:
        brand.logo = data["logo"]
    if "website" in data:
        brand.website = data["website"]

    db.session.commit()
    return jsonify({"success": True, "message": "Brand updated successfully", "brand": brand.to_dict()}), 200


@api_bp.route("/brands/<int:brand_id>", methods=["DELETE"])
@jwt_admin_required
def delete_brand(brand_id):
    """Delete a brand (Requires Admin JWT)."""
    brand = Brand.query.get(brand_id)
    if not brand:
        return jsonify({"success": False, "error": "Brand not found"}), 404

    db.session.delete(brand)
    db.session.commit()
    return jsonify({"success": True, "message": f"Brand #{brand_id} deleted successfully"}), 200
