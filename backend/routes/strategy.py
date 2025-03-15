from datetime import datetime, timedelta

from app import db
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from models.product import PerformanceRecord, Product, UserProduct
from services.strategy_service import run_strategy_simulation

strategy_bp = Blueprint("strategy", __name__)


@strategy_bp.route("/products", methods=["GET"])
def get_available_products():
    """
    Get all active strategy products available for subscription
    """
    products = Product.query.filter_by(is_active=True).all()

    return jsonify({"products": [product.to_dict() for product in products]}), 200


@strategy_bp.route("/product/<int:product_id>", methods=["GET"])
def get_product_details(product_id):
    """Get detailed information about a specific product"""
    product = Product.query.get(product_id)

    if not product:
        return jsonify({"error": "Product not found"}), 404

    return jsonify(product.to_dict()), 200


@strategy_bp.route("/performance/<int:user_product_id>", methods=["GET"])
@jwt_required()
def get_performance_history(user_product_id):
    """Get the performance history for a user's subscribed product"""
    user_id = get_jwt_identity()

    # Verify ownership
    user_product = UserProduct.query.filter_by(id=user_product_id, user_id=user_id).first()

    if not user_product:
        return jsonify({"error": "Subscription not found or not authorized"}), 404

    # Get performance records, ordered by date
    records = PerformanceRecord.query.filter_by(user_product_id=user_product_id).order_by(PerformanceRecord.date).all()

    return (
        jsonify(
            {
                "product_name": user_product.product.name,
                "start_balance": user_product.start_balance,
                "current_balance": user_product.current_balance,
                "performance": round(
                    (user_product.current_balance - user_product.start_balance) / user_product.start_balance * 100,
                    2,
                ),
                "history": [record.to_dict() for record in records],
            }
        ),
        200,
    )


@strategy_bp.route("/run/<int:user_product_id>", methods=["POST"])
@jwt_required()
def run_strategy(user_product_id):
    """Run or update the strategy simulation for a specific subscription"""
    user_id = get_jwt_identity()

    # Verify ownership
    user_product = UserProduct.query.filter_by(id=user_product_id, user_id=user_id).first()

    if not user_product:
        return jsonify({"error": "Subscription not found or not authorized"}), 404

    # Get simulation parameters from request
    data = request.get_json() or {}
    start_date = data.get("start_date")
    end_date = data.get("end_date", datetime.now().strftime("%Y-%m-%d"))

    # If no start date provided, use the latest record date + 1 day or purchase date
    if not start_date:
        latest_record = (
            PerformanceRecord.query.filter_by(user_product_id=user_product_id)
            .order_by(PerformanceRecord.date.desc())
            .first()
        )

        if latest_record:
            start_date = (latest_record.date + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            start_date = user_product.purchase_date.strftime("%Y-%m-%d")

    # Get strategy configuration
    strategy_config = user_product.product.config

    # Run strategy simulation
    results = run_strategy_simulation(
        strategy_type=user_product.product.strategy_type,
        config=strategy_config,
        start_date=start_date,
        end_date=end_date,
        initial_balance=user_product.current_balance,
    )

    # Update database with results
    if results and len(results) > 0:
        # Update the performance records
        for date_str, data in results.items():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

            # Check if a record for this date already exists
            record = PerformanceRecord.query.filter_by(user_product_id=user_product_id, date=date_obj).first()

            if record:
                # Update existing record
                record.balance = data["balance"]
                record.trades_count = data["trades_count"]
                record.profit_loss = data["profit_loss"]
            else:
                # Create new record
                record = PerformanceRecord(
                    user_product_id=user_product_id,
                    date=date_obj,
                    balance=data["balance"],
                    trades_count=data["trades_count"],
                    profit_loss=data["profit_loss"],
                )
                db.session.add(record)

        # Update the current balance in the UserProduct
        last_date = max(results.keys())
        user_product.current_balance = results[last_date]["balance"]

        db.session.commit()

    return (
        jsonify(
            {
                "message": "Strategy simulation completed successfully",
                "current_balance": user_product.current_balance,
                "performance": round(
                    (user_product.current_balance - user_product.start_balance) / user_product.start_balance * 100,
                    2,
                ),
                "days_processed": len(results) if results else 0,
            }
        ),
        200,
    )
