from app import db
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from models.product import Product, UserProduct
from models.user import User

account_bp = Blueprint("account", __name__)


@account_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user.to_dict()), 200


@account_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()

    # Update allowed fields
    if "first_name" in data:
        user.first_name = data["first_name"]
    if "last_name" in data:
        user.last_name = data["last_name"]
    if "email" in data and data["email"] != user.email:
        # Check if email already exists
        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"error": "Email already registered"}), 409
        user.email = data["email"]
    if "password" in data:
        user.set_password(data["password"])

    db.session.commit()

    return jsonify({"message": "Profile updated successfully", "user": user.to_dict()}), 200


@account_bp.route("/products", methods=["GET"])
@jwt_required()
def get_user_products():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    user_products = UserProduct.query.filter_by(user_id=user_id).all()

    return jsonify({"products": [up.to_dict() for up in user_products]}), 200


@account_bp.route("/subscribe", methods=["POST"])
@jwt_required()
def subscribe_to_product():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    product_id = data.get("product_id")
    initial_balance = data.get("initial_balance", 10000.0)  # Default starting balance

    # Verify product exists
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    # Check if user is already subscribed
    existing_subscription = UserProduct.query.filter_by(user_id=user_id, product_id=product_id, is_active=True).first()

    if existing_subscription:
        return jsonify({"error": "Already subscribed to this product"}), 409

    # Create new subscription
    subscription = UserProduct(
        user_id=user_id,
        product_id=product_id,
        start_balance=initial_balance,
        current_balance=initial_balance,  # Initially set to starting balance
    )

    db.session.add(subscription)
    db.session.commit()

    return jsonify({"message": "Successfully subscribed to product", "subscription": subscription.to_dict()}), 201
