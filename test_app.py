#!/usr/bin/env python3
"""
Simple test script for ERP Payroll System
This script tests basic functionality of the application.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from datetime import datetime, date

def test_database_connection():
    """Test database connection and basic operations."""
    print("Testing database connection...")
    
    app = create_app()
    with app.app_context():
        try:
            # Import models after app context
            from models import User, Employee, Payroll
            
            # Test database connection
            db.create_all()
            print("✓ Database connection successful")
            
            # Test user creation
            test_user = User(
                username='test_user',
                email='test@example.com',
                role='employee'
            )
            test_user.set_password('test123')
            db.session.add(test_user)
            db.session.commit()
            print("✓ User creation successful")
            
            # Test employee creation
            test_employee = Employee(
                user_id=test_user.id,
                employee_id='TEST001',
                first_name='Test',
                last_name='User',
                email='test@example.com',
                job_title='Test Engineer',
                department='Testing',
                hire_date=date.today(),
                salary=50000
            )
            db.session.add(test_employee)
            db.session.commit()
            print("✓ Employee creation successful")
            
            # Test payroll creation
            test_payroll = Payroll(
                employee_id=test_employee.id,
                pay_period_start=date.today(),
                pay_period_end=date.today(),
                basic_salary=50000,
                allowances=5000,
                gross_salary=55000,
                tax_deduction=8250,
                pension_deduction=2750,
                total_deductions=11000,
                net_salary=44000,
                status='processed'
            )
            db.session.add(test_payroll)
            db.session.commit()
            print("✓ Payroll creation successful")
            
            # Clean up test data
            db.session.delete(test_payroll)
            db.session.delete(test_employee)
            db.session.delete(test_user)
            db.session.commit()
            print("✓ Test data cleanup successful")
            
            return True
            
        except Exception as e:
            print(f"✗ Database test failed: {e}")
            return False

def test_authentication():
    """Test authentication functionality."""
    print("Testing authentication...")
    
    app = create_app()
    with app.app_context():
        try:
            # Import models after app context
            from models import User
            
            # Test password hashing
            user = User(username='auth_test', email='auth@test.com', role='employee')
            user.set_password('test_password')
            
            if user.check_password('test_password'):
                print("✓ Password hashing and verification successful")
            else:
                print("✗ Password verification failed")
                return False
            
            # Test user properties
            if user.role == 'employee':
                print("✓ User role assignment successful")
            else:
                print("✗ User role assignment failed")
                return False
            
            return True
            
        except Exception as e:
            print(f"✗ Authentication test failed: {e}")
            return False

def test_models():
    """Test model relationships and properties."""
    print("Testing models...")
    
    app = create_app()
    with app.app_context():
        try:
            # Import models after app context
            from models import User, Employee
            
            # Test User model
            user = User(username='model_test', email='model@test.com', role='employee')
            user.set_password('test123')
            db.session.add(user)
            db.session.flush()
            
            # Test Employee model
            employee = Employee(
                user_id=user.id,
                employee_id='MODEL001',
                first_name='Model',
                last_name='Test',
                email='model@test.com',
                job_title='Test Engineer',
                department='Testing',
                hire_date=date.today(),
                salary=60000
            )
            db.session.add(employee)
            db.session.flush()
            
            # Test relationships
            if employee.user == user:
                print("✓ User-Employee relationship successful")
            else:
                print("✗ User-Employee relationship failed")
                return False
            
            # Test employee properties
            if employee.full_name == 'Model Test':
                print("✓ Employee full_name property successful")
            else:
                print("✗ Employee full_name property failed")
                return False
            
            # Clean up
            db.session.delete(employee)
            db.session.delete(user)
            db.session.commit()
            
            return True
            
        except Exception as e:
            print(f"✗ Model test failed: {e}")
            return False

def main():
    """Run all tests."""
    print("=" * 50)
    print("🧪 ERP Payroll System - Test Suite")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Authentication", test_authentication),
        ("Models", test_models)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} test...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} test passed")
        else:
            print(f"❌ {test_name} test failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("🎉 All tests passed! The application is ready to run.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
