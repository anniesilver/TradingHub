from datetime import datetime

from app import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    strategy_type = db.Column(db.String(50), nullable=False)  # e.g., "SPY_POWER_CASHFLOW"
    config = db.Column(db.JSON)  # Strategy configuration
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    users = db.relationship("UserProduct", back_populates="product")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "strategy_type": self.strategy_type,
            "config": self.config,
            "is_active": self.is_active,
        }


class UserProduct(db.Model):
    __tablename__ = "user_products"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    start_balance = db.Column(db.Float, nullable=False)
    current_balance = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    user = db.relationship("User", back_populates="products")
    product = db.relationship("Product", back_populates="users")
    performance_records = db.relationship("PerformanceRecord", back_populates="user_product")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "product_name": self.product.name,
            "purchase_date": self.purchase_date.isoformat(),
            "start_balance": self.start_balance,
            "current_balance": self.current_balance,
            "performance": round((self.current_balance - self.start_balance) / self.start_balance * 100, 2),
            "is_active": self.is_active,
        }


class PerformanceRecord(db.Model):
    __tablename__ = "performance_records"

    id = db.Column(db.Integer, primary_key=True)
    user_product_id = db.Column(db.Integer, db.ForeignKey("user_products.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    balance = db.Column(db.Float, nullable=False)
    trades_count = db.Column(db.Integer, default=0)
    profit_loss = db.Column(db.Float, default=0.0)

    # Relationships
    user_product = db.relationship("UserProduct", back_populates="performance_records")

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "balance": self.balance,
            "trades_count": self.trades_count,
            "profit_loss": self.profit_loss,
        }
