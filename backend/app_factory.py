import os

from dotenv import load_dotenv
from flask import Flask

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "services", ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
else:
    # Try loading from project root
    root_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(root_env_path):
        load_dotenv(dotenv_path=root_env_path)
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Create extensions first (but don't initialize them)
db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()
migrate = Migrate()


def create_app():
    app = Flask(__name__)

    # Configure the app
    app.config["SECRET_KEY"] = "your-secret-key"  # Change in production
    # Database configuration from environment variables
    db_name = os.environ.get("DB_NAME", "tradinghub")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "your_password")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", database_url)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = "your-jwt-secret-key"  # Change in production

    # Initialize extensions with app
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    # Enable CORS
    CORS(
        app,
        origins=["http://localhost:3000"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Origin"],
        supports_credentials=True,
        max_age=3600,
    )

    with app.app_context():
        # Import models (must be after db definition)
        from routes.account import account_bp

        # Import and register blueprints
        from routes.auth import auth_bp
        from routes.strategy import strategy_bp

        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(account_bp, url_prefix="/api/account")
        app.register_blueprint(strategy_bp, url_prefix="/api/strategy")

        # Import strategy service
        from services.strategy_service import run_strategy_simulation

        # Create all tables
        db.create_all()

        @app.route("/api/health")
        def health_check():
            return {"status": "healthy"}

        # Add FastAPI-like routes for strategy simulation
        @app.route("/", methods=["GET"])
        def read_root():
            return {"message": "Welcome to TradingHub API"}

        @app.route("/api/strategies", methods=["GET"])
        def get_strategies():
            return {"strategies": [{"id": "SPY_POWER_CASHFLOW", "name": "SPY Power Cashflow"}]}

        @app.route("/api/simulate", methods=["POST"])
        def run_simulation():
            from flask import request

            data = request.get_json()

            results = run_strategy_simulation(
                data["strategy_type"],
                data["config"],
                data["start_date"],
                data["end_date"],
                data.get("initial_balance", 10000.0),
            )

            if not results:
                return {"error": "Simulation failed"}, 500

            return results

    return app
