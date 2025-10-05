#!/usr/bin/env python3
"""
ERP Payroll System - Run Script
This script initializes and runs the Flask application.
"""

import os
import sys
from datetime import date
from app import create_app, db

def create_sample_data():
    """Create sample data for testing purposes."""
    print("Creating sample data...")
    
    # Import models after app context is created
    from models import User, Employee, Payroll, Attendance, Department
    
    # Check if admin user already exists
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        # Create admin user
        admin_user = User(
            username='admin',
            email='admin@company.com',
            role='admin'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        print("✓ Admin user created (username: admin, password: admin123)")
    
    # Check if HR user exists
    hr_user = User.query.filter_by(username='hr').first()
    if not hr_user:
        # Create HR user
        hr_user = User(
            username='hr',
            email='hr@company.com',
            role='hr'
        )
        hr_user.set_password('hr123')
        db.session.add(hr_user)
        db.session.commit()
        print("✓ HR user created (username: hr, password: hr123)")
    
    # Check if sample employees exist
    if Employee.query.count() == 0:
        # Create sample employees
        employees_data = [
            {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john.doe@company.com',
                'phone': '+1-555-0101',
                'job_title': 'Software Engineer',
                'department': 'Engineering',
                'hire_date': date(2023, 1, 15),
                'salary': 75000,
                'tax_id': '123-45-6789',
                'bank_name': 'First National Bank',
                'bank_account': '1234567890',
                'address': '123 Main St, City, State 12345'
            },
            {
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'jane.smith@company.com',
                'phone': '+1-555-0102',
                'job_title': 'HR Manager',
                'department': 'Human Resources',
                'hire_date': date(2022, 6, 1),
                'salary': 65000,
                'tax_id': '987-65-4321',
                'bank_name': 'Second National Bank',
                'bank_account': '0987654321',
                'address': '456 Oak Ave, City, State 12345'
            },
            {
                'first_name': 'Mike',
                'last_name': 'Johnson',
                'email': 'mike.johnson@company.com',
                'phone': '+1-555-0103',
                'job_title': 'Accountant',
                'department': 'Finance',
                'hire_date': date(2023, 3, 10),
                'salary': 60000,
                'tax_id': '456-78-9012',
                'bank_name': 'Third National Bank',
                'bank_account': '1122334455',
                'address': '789 Pine St, City, State 12345'
            }
        ]
        
        for emp_data in employees_data:
            # Create user for employee
            user = User(
                username=emp_data['email'].split('@')[0],
                email=emp_data['email'],
                role='employee'
            )
            user.set_password('employee123')
            db.session.add(user)
            db.session.flush()  # Get the user ID
            
            # Create employee record
            employee = Employee(
                user_id=user.id,
                employee_id=f"EMP{user.id:04d}",
                first_name=emp_data['first_name'],
                last_name=emp_data['last_name'],
                email=emp_data['email'],
                phone=emp_data['phone'],
                job_title=emp_data['job_title'],
                department=emp_data['department'],
                hire_date=emp_data['hire_date'],
                salary=emp_data['salary'],
                tax_id=emp_data['tax_id'],
                bank_name=emp_data['bank_name'],
                bank_account=emp_data['bank_account'],
                address=emp_data['address']
            )
            db.session.add(employee)
        
        db.session.commit()
        print("✓ Sample employees created")
    
    print("Sample data creation completed!")

def main():
    """Main function to run the application."""
    app = create_app()
    
    with app.app_context():
        # Create all database tables
        db.create_all()
        print("✓ Database tables created")
        
        # Create sample data
        create_sample_data()
    
    # Run the application
    print("\n" + "="*50)
    print("🚀 ERP Payroll System is starting...")
    print("="*50)
    print("📱 Access the application at: http://localhost:5000")
    print("👤 Admin Login: admin / admin123")
    print("👤 HR Login: hr / hr123")
    print("👤 Employee Login: Use any employee email / employee123")
    print("="*50)
    print("Press Ctrl+C to stop the server")
    print("="*50 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
