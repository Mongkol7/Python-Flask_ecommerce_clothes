from flask import request, jsonify
from extensions import db
from models.category import Category
from . import api_bp
from .jwt_auth import jwt_admin_required


@api_bp.route("/categories", methods=["GET"])
def get_categories():
    """List all categories with products count."""
    categories = Category.query.order_by(Category.name.asc()).all()
    return jsonify([c.to_dict() for c in categories]), 200


@api_bp.route("/categories/<int:cat_id>", methods=["GET"])
def get_category_detail(cat_id):
    """Get single category details and associated products."""
    cat = Category.query.get(cat_id)
    if not cat:
        return jsonify({"success": False, "error": "Category not found"}), 404

    data = cat.to_dict()
    data["products"] = [p.to_dict() for p in cat.products] if cat.products else []
    return jsonify(data), 200


@api_bp.route("/categories", methods=["POST"])
@jwt_admin_required
def create_category():
    """Create a new category (Requires Admin JWT)."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    slug = (data.get("slug") or name.lower().replace(" ", "-")).strip()
    description = (data.get("description") or "").strip()
    image = data.get("image")

    if not name:
        return jsonify({"success": False, "error": "Category name is required"}), 400

    if Category.query.filter((Category.name == name) | (Category.slug == slug)).first():
        return jsonify({"success": False, "error": "Category name or slug already exists"}), 409

    new_cat = Category(name=name, slug=slug, description=description, image=image)
    db.session.add(new_cat)
    db.session.commit()

    return jsonify({"success": True, "message": "Category created successfully", "category": new_cat.to_dict()}), 201


@api_bp.route("/categories/<int:cat_id>", methods=["PUT", "PATCH"])
@jwt_admin_required
def update_category(cat_id):
    """Update an existing category (Requires Admin JWT)."""
    cat = Category.query.get(cat_id)
    if not cat:
        return jsonify({"success": False, "error": "Category not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"].strip():
        cat.name = data["name"].strip()
    if "slug" in data and data["slug"].strip():
        cat.slug = data["slug"].strip()
    if "description" in data:
        cat.description = data["description"]
    if "image" in data:
        cat.image = data["image"]

    db.session.commit()
    return jsonify({"success": True, "message": "Category updated successfully", "category": cat.to_dict()}), 200


@api_bp.route("/categories/<int:cat_id>", methods=["DELETE"])
@jwt_admin_required
def delete_category(cat_id):
    """Delete a category (Requires Admin JWT)."""
    cat = Category.query.get(cat_id)
    if not cat:
        return jsonify({"success": False, "error": "Category not found"}), 404

    db.session.delete(cat)
    db.session.commit()
    return jsonify({"success": True, "message": f"Category #{cat_id} deleted successfully"}), 200
