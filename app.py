from flask import Flask
from flask_login import LoginManager
import logging
import os
from datetime import datetime

from config import Config
from managers.database_manager import DatabaseManager
from managers.auth_manager import AuthManager
from services.routes import create_routes

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Setup logging
    setup_logging()
    
    # Initialize database
    db_manager = DatabaseManager()
    
    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Initialize auth manager
    auth_manager = AuthManager(db_manager)
    
    @login_manager.user_loader
    def load_user(user_id):
        return auth_manager.get_user_by_id(int(user_id))
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Register routes
    create_routes(app, db_manager, auth_manager)
    
    return app

def setup_logging():
    log_filename = f"logs/app_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # Only for app startup info
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

if __name__ == '__main__':
    app = create_app()
    print("🎤 Gamified Public Speaking App Starting...")
    print("🌐 Visit: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)