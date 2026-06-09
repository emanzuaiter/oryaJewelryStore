from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
import os
from dotenv import load_dotenv
from flask_mail import Mail

load_dotenv() # Load variables from .env

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
mail = Mail()
login_manager.login_view = 'auth.login'
login_manager.refresh_view = 'auth.admin_login'
login_manager.needs_refresh_message = "To protect your account, please re-authenticate to access this page."
login_manager.needs_refresh_message_category = "info"

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = 'orya-secret-key-123'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orya.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Mail Configuration (Gmail SMTP)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # Register Blueprints
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.products import products_bp
    app.register_blueprint(products_bp)

    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp)

    from app.routes.api import api_bp
    app.register_blueprint(api_bp)

    from app.routes.chatbot import chatbot_bp
    app.register_blueprint(chatbot_bp)

    @app.context_processor
    def inject_global_data():
        from flask_login import current_user
        from app.models import SiteSetting, Announcement
        settings_list = SiteSetting.query.all()
        
        # We create a dictionary that returns an empty string if the key is missing
        class SettingsDict(dict):
            def __getattr__(self, key):
                return self.get(key, '')
            def __getitem__(self, key):
                return self.get(key, '')

        settings_dict = SettingsDict()
        for s in settings_list:
            # Add both generic and specific lang values
            settings_dict[s.key] = s.value_ar if session.get('lang', 'ar') == 'ar' else s.value_en
            # Also add raw lang values to be safe
            settings_dict[f"{s.key}_ar"] = s.value_ar
            settings_dict[f"{s.key}_en"] = s.value_en
        
        # Add raw values for WhatsApp etc if needed
        whatsapp = SiteSetting.query.filter_by(key='whatsapp_number').first()
        if whatsapp:
            settings_dict['whatsapp_number'] = whatsapp.value_en
            
        from app.models import Notification, Order, SupportTicket
        
        announcement = Announcement.query.filter_by(is_active=True).first()
        
        ctx = {
            'site_settings': settings_dict,
            'announcement': announcement,
        }

        if current_user.is_authenticated and current_user.role in ['admin', 'super_admin']:
            # Only show support ticket notifications (Talk to human)
            admin_notifications = Notification.query.filter_by(type='support_ticket').order_by(Notification.created_at.desc()).limit(5).all()
            unread_notifications_count = Notification.query.filter_by(type='support_ticket', is_read=False).count()
            ctx['unread_notifications_count'] = unread_notifications_count
            ctx['admin_notifications'] = admin_notifications
            ctx['pending_count'] = Order.query.filter_by(status='pending').count()

        return ctx

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import request, redirect, url_for
        if request.path.startswith('/admin'):
            return redirect(url_for('auth.admin_login', next=request.path))
        return redirect(url_for('auth.login', next=request.path))

    with app.app_context():
        db.create_all()

    # Build RAG vector store on startup if it doesn't exist
    try:
        from app.chatbot.rag_pipeline import build_vector_store, CHROMA_DIR
        if not CHROMA_DIR.exists():
            print("[Startup] Building RAG vector store...")
            build_vector_store()
    except Exception as e:
        print(f"[Startup] Error building RAG store: {e}")

    return app
