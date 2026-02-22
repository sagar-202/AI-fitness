from flask import Flask
from flask_cors import CORS
import os
from database import init_db
from services.analyzer import EnhancedExerciseAnalyzer
from routes.auth import auth_bp
from routes.api import api_bp
from routes.views import views_bp

def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True)
    
    app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_123')
    
    # Initialize database
    init_db()
    
    # Initialize Analyzer
    # We attach it to app.config for global access in routes
    app.config['ANALYZER'] = EnhancedExerciseAnalyzer()
    
    # Register Blueprints
    app.register_blueprint(views_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    
    return app
