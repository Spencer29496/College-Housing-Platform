"""
Main Flask application entry point
"""
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
import logging

from server.models import db
from server.routes.auth import auth_bp

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application"""
    # Load environment variables
    load_dotenv()
    logger.info("Environment variables loaded")
    
    # Check critical environment variables
    if not os.getenv('SENDGRID_API_KEY'):
        logger.warning("SENDGRID_API_KEY environment variable not set!")
    
    app = Flask(__name__)
    CORS(app)
    logger.info("Flask app created with CORS enabled")
    
    # Configure database
    db_uri = f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'team13')}@{os.getenv('POSTGRES_HOST', 'localhost')}/{os.getenv('POSTGRES_DB', 'test_db')}"
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    logger.info(f"Database configured: {db_uri}")
    
    # Initialize database
    db.init_app(app)
    logger.info("Database initialized")
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    logger.info("Auth blueprint registered")
    
    # Create all database tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created")
    
    @app.route('/')
    def index():
        return {'message': 'Binghamton Housing Portal API'}
    
    logger.info("Application setup complete")
    return app

app = create_app()

if __name__ == '__main__':
    logger.info("Starting Flask development server")
    app.run(debug=True) 