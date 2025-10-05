from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from models import User, Employee, db
from forms import LoginForm, RegisterForm
from datetime import datetime
import uuid
import random
import string

auth_bp = Blueprint('auth', __name__)

def generate_username(first_name, last_name):
    """Generate a unique username based on first and last name."""
    base_username = f"{first_name.lower()}.{last_name.lower()}"
    username = base_username
    
    # Check if username exists and add number if needed
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_username}{counter}"
        counter += 1
    
    return username

def generate_password():
    """Generate a secure random password."""
    # Generate a password with letters, numbers, and special characters
    letters = string.ascii_letters
    digits = string.digits
    special_chars = "!@#$%^&*"
    
    # Ensure at least one of each type
    password = [
        random.choice(letters),
        random.choice(digits),
        random.choice(special_chars)
    ]
    
    # Fill the rest with random characters
    all_chars = letters + digits + special_chars
    for _ in range(5):  # Total length will be 8
        password.append(random.choice(all_chars))
    
    # Shuffle the password
    random.shuffle(password)
    return ''.join(password)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('admin.dashboard')
            
            flash('Login successful!', 'success')
            return redirect(next_page)
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    # Only HR and Admin can register new users
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to register users', 'error')
        return redirect(url_for('admin.dashboard'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        # Check if email already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists', 'error')
            return render_template('auth/register.html', form=form)
        
        # Generate username and password for employees
        if form.role.data == 'employee':
            username = generate_username(form.first_name.data, form.last_name.data)
            password = generate_password()
        else:
            # For admin and HR, use provided credentials
            username = form.username.data
            password = form.password.data
            
            # Check if username already exists for admin/HR
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return render_template('auth/register.html', form=form)
        
        # Create new user
        user = User(
            username=username,
            email=form.email.data,
            role=form.role.data
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Create employee record if role is not admin
        if form.role.data != 'admin':
            employee = Employee(
                user_id=user.id,
                employee_id=f"EMP{str(uuid.uuid4())[:8].upper()}",
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data,
                job_title=form.job_title.data,
                department=form.department.data,
                hire_date=form.hire_date.data,
                salary=form.salary.data
            )
            db.session.add(employee)
            db.session.commit()
        
        # Show generated credentials for employees
        if form.role.data == 'employee':
            flash(f'Employee registered successfully! Username: {username}, Password: {password}', 'success')
        else:
            flash('User registered successfully!', 'success')
        
        return redirect(url_for('admin.users'))
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')

@auth_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    
    try:
        current_user.email = data.get('email', current_user.email)
        
        if current_user.employee:
            current_user.employee.first_name = data.get('first_name', current_user.employee.first_name)
            current_user.employee.last_name = data.get('last_name', current_user.employee.last_name)
            current_user.employee.phone = data.get('phone', current_user.employee.phone)
            current_user.employee.address = data.get('address', current_user.employee.address)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    # Validate input
    if not current_password or not new_password or not confirm_password:
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    if new_password != confirm_password:
        return jsonify({'success': False, 'message': 'New passwords do not match'})
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters long'})
    
    # Verify current password
    if not current_user.check_password(current_password):
        return jsonify({'success': False, 'message': 'Current password is incorrect'})
    
    try:
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Password changed successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
