from flask import Flask, redirect, url_for, render_template, request, flash
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import db and models
from models import db, User

# Initialize extensions
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    # Database: require DATABASE_URL (cloud Postgres)
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("⚠️  DATABASE_URL not set, using SQLite fallback")
        db_url = 'sqlite:///payroll_system.db'
    # Normalize postgres URI and ensure psycopg3 driver
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif db_url.startswith('postgresql://') and '+psycopg' not in db_url:
        db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # CSRF configuration
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = None  # No time limit for CSRF tokens
    
    # Email configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'samueloluwapelumi8@gmail.com'
    app.config['MAIL_PASSWORD'] = 'zgwv xctm atos lxzj'
    app.config['MAIL_DEFAULT_SENDER'] = 'samueloluwapelumi8@gmail.com'
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    
    # Expose csrf_token() in templates for non-FlaskForm forms
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)
    
    # Import additional models
    from models import Employee, Payroll, Attendance, Department
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Health check endpoint for debugging
    @app.route('/health')
    def health_check():
        try:
            # Test database connection
            db.session.execute("SELECT 1")
            db_status = "✅ Connected"
        except Exception as e:
            db_status = f"❌ Error: {str(e)}"
        
        try:
            # Test user query
            user_count = User.query.count()
            user_status = f"✅ {user_count} users found"
        except Exception as e:
            user_status = f"❌ Error: {str(e)}"
        
        try:
            # Test if tables exist
            from models import Employee, Payroll, Attendance, OfficeLocation
            tables_status = "✅ All tables accessible"
        except Exception as e:
            tables_status = f"❌ Table error: {str(e)}"
        
        return {
            "status": "ok",
            "database": db_status,
            "users": user_status,
            "tables": tables_status,
            "app_name": "ERP Payroll System"
        }
    
    # Setup route for production (no auth required)
    @app.route('/setup')
    def setup():
        """Setup route to create default users in production"""
        try:
            from models import User
            
            # Create Admin user if doesn't exist
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@example.com',
                    role='admin'
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                admin_created = True
            else:
                admin_created = False
            
            # Create HR user if doesn't exist
            hr_user = User.query.filter_by(username='hr').first()
            if not hr_user:
                hr_user = User(
                    username='hr',
                    email='hr@company.com',
                    role='hr'
                )
                hr_user.set_password('hr123')
                db.session.add(hr_user)
                hr_created = True
            else:
                hr_created = False
            
            db.session.commit()
            
            return {
                "status": "success",
                "message": "Setup completed",
                "admin_created": admin_created,
                "hr_created": hr_created,
                "login_credentials": {
                    "admin": "admin@example.com / admin123",
                    "hr": "hr@company.com / hr123"
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }, 500
    
    # Redirect routes for better UX
    @app.route('/attendance')
    def attendance_redirect():
        return redirect(url_for('admin.attendance'))
    
    @app.route('/dashboard')
    def dashboard_redirect():
        return redirect(url_for('admin.dashboard'))
    
    # Homepage route
    @app.route('/')
    def home():
        return render_template('home.html')
    
    # Contact page route
    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        from forms import ContactForm
        form = ContactForm()
        
        if request.method == 'POST':
            form = ContactForm(request.form)
            if form.validate_on_submit():
                try:
                    # Get form data
                    first_name = form.firstName.data
                    last_name = form.lastName.data
                    email = form.email.data
                    company = form.company.data or ''
                    phone = form.phone.data or ''
                    subject = form.subject.data
                    message = form.message.data
                    
                    # Create email message
                    msg = Message(
                        subject=f"Contact Form: {subject} - {first_name} {last_name}",
                        sender=app.config['MAIL_DEFAULT_SENDER'],
                        recipients=[app.config['MAIL_DEFAULT_SENDER']],
                        reply_to=email
                    )
                    
                    # Email body
                    msg.body = f"""
New Contact Form Submission

Name: {first_name} {last_name}
Email: {email}
Company: {company or 'Not provided'}
Phone: {phone or 'Not provided'}
Subject: {subject}

Message:
{message}

---
This message was sent from the ERP Payroll System contact form.
                    """
                    
                    # Send email
                    mail.send(msg)
                    
                    # Send confirmation email to user
                    confirmation_msg = Message(
                        subject="Thank you for contacting us - ERP Payroll System",
                        sender=app.config['MAIL_DEFAULT_SENDER'],
                        recipients=[email]
                    )
                    
                    confirmation_msg.body = f"""
Dear {first_name},

Thank you for contacting us regarding our ERP Payroll System. We have received your message and will get back to you within 24 hours.

Your inquiry details:
Subject: {subject}
Message: {message}

If you have any urgent questions, please don't hesitate to call us at +2347077705842.

Best regards,
SMI Web Solutions Team
                    """
                    
                    mail.send(confirmation_msg)
                    
                    flash('Thank you for your message! We have sent you a confirmation email and will get back to you within 24 hours.', 'success')
                    return redirect(url_for('contact'))
                    
                except Exception as e:
                    flash('Sorry, there was an error sending your message. Please try again or contact us directly.', 'error')
                    return render_template('contact.html', form=form)
            else:
                # Form validation failed
                flash('Please correct the errors below and try again.', 'error')
        
        return render_template('contact.html', form=form)
    
    # Register blueprints
    from blueprints.auth import auth_bp
    from blueprints.employees import employees_bp
    from blueprints.payroll import payroll_bp
    from blueprints.admin import admin_bp
    from blueprints.api import api_bp
    from blueprints.attendance import attendance_bp
    from blueprints.qr_attendance import qr_attendance_bp
    from blueprints.time_management import time_management_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(employees_bp, url_prefix='/employees')
    app.register_blueprint(payroll_bp, url_prefix='/payroll')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(qr_attendance_bp, url_prefix='/qr-attendance')
    app.register_blueprint(time_management_bp, url_prefix='/time-management')
    
    return app

# Create app instance for Gunicorn
try:
    app = create_app()
    print("✅ Flask app created successfully")
except Exception as e:
    print(f"❌ Error creating Flask app: {e}")
    import traceback
    traceback.print_exc()
    # Create a minimal app to prevent import errors
    from flask import Flask
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'fallback-secret-key'

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Database initialization error: {e}")
    app.run(debug=True)
