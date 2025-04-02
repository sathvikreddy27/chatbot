import os
import logging
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from models import db, User, Chat, Message, Feedback

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
db.init_app(app)

# Set secret key from environment variable with fallback
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key-for-development")

# Create all database tables
with app.app_context():
    db.create_all()
    logger.info("Database tables created successfully")

# Import routes after app initialization to avoid circular imports
from routes.chat import chat_bp

# Register blueprints
app.register_blueprint(chat_bp)

# Root route redirect
@app.route('/')
def index():
    from flask import render_template
    return render_template('index.html')

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    from flask import jsonify
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    from flask import jsonify
    logger.error(f"Server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

# Rate limiting simple implementation using in-memory storage
# In production, consider using Redis or another distributed cache
app.config['RATE_LIMIT'] = {
    'window_seconds': 60,
    'max_requests': 20,
    'clients': {}
}
