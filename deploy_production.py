#!/usr/bin/env python3
"""
Production deployment script
Ensures HR and Admin users exist in production database
"""
import os
from dotenv import load_dotenv
from app import create_app, db
from models import User

def deploy_to_production():
    """Deploy and ensure users exist in production"""
    print("🚀 Starting production deployment...")
    
    # Load environment variables
    load_dotenv()
    
    # Create app
    app = create_app()
    
    with app.app_context():
        try:
            print("📊 Checking database connection...")
            
            # Test database connection
            db.session.execute("SELECT 1")
            print("✅ Database connection successful")
            
            # Ensure Admin user exists
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                print("👤 Creating Admin user...")
                admin_user = User(
                    username='admin',
                    email='admin@example.com',
                    role='admin'
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                print("✅ Admin user created")
            else:
                print("✅ Admin user already exists")
            
            # Ensure HR user exists
            hr_user = User.query.filter_by(username='hr').first()
            if not hr_user:
                print("👤 Creating HR user...")
                hr_user = User(
                    username='hr',
                    email='hr@company.com',
                    role='hr'
                )
                hr_user.set_password('hr123')
                db.session.add(hr_user)
                print("✅ HR user created")
            else:
                print("✅ HR user already exists")
            
            # Commit changes
            db.session.commit()
            print("💾 Database changes committed")
            
            # Verify users
            print("\n📋 User verification:")
            admin = User.query.filter_by(username='admin').first()
            hr = User.query.filter_by(username='hr').first()
            
            print(f"Admin: {admin.username} ({admin.email}) - Active: {admin.is_active}")
            print(f"HR: {hr.username} ({hr.email}) - Active: {hr.is_active}")
            
            print("\n🎉 Production deployment completed successfully!")
            print("\nLogin credentials:")
            print("Admin: admin@example.com / admin123")
            print("HR: hr@company.com / hr123")
            
        except Exception as e:
            print(f"❌ Deployment error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == '__main__':
    success = deploy_to_production()
    exit(0 if success else 1)
