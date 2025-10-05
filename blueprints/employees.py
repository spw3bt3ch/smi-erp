from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import Employee, User, db
from forms import EmployeeForm
from datetime import datetime
import uuid
import secrets

employees_bp = Blueprint('employees', __name__)

def generate_employee_username(first_name: str, last_name: str) -> str:
    base_username = f"{(first_name or 'user').strip().lower()}.{(last_name or 'user').strip().lower()}"
    username = base_username
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_username}{counter}"
        counter += 1
    return username

@employees_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    department = request.args.get('department', '', type=str)
    
    query = Employee.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            db.or_(
                Employee.first_name.contains(search),
                Employee.last_name.contains(search),
                Employee.employee_id.contains(search),
                Employee.email.contains(search)
            )
        )
    
    if department:
        query = query.filter(Employee.department == department)
    
    employees = query.paginate(
        page=page, per_page=10, error_out=False
    )
    
    # Get unique departments for filter
    departments = db.session.query(Employee.department).distinct().all()
    departments = [dept[0] for dept in departments if dept[0]]
    
    return render_template('employees/index.html', 
                         employees=employees, 
                         search=search, 
                         department=department,
                         departments=departments)

@employees_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to add employees', 'error')
        return redirect(url_for('employees.index'))
    
    form = EmployeeForm()
    if form.validate_on_submit():
        # Check if email already exists
        if Employee.query.filter_by(email=form.email.data).first():
            flash('Email already exists', 'error')
            return render_template('employees/add.html', form=form)
        
        # Check if user with this email already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('User account with this email already exists', 'error')
            return render_template('employees/add.html', form=form)
        
        # Create user account for the employee
        generated_username = generate_employee_username(form.first_name.data, form.last_name.data)
        user = User(
            username=generated_username,
            email=form.email.data,
            role='employee',
            is_active=True
        )
        user.set_password('employee123')  # Default password
        
        db.session.add(user)
        db.session.flush()  # Get the user ID
        
        # Create employee linked to the user
        employee = Employee(
            user_id=user.id,  # Link to the created user
            employee_id=f"EMP{str(uuid.uuid4())[:8].upper()}",
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            job_title=form.job_title.data,
            department=form.department.data,
            hire_date=form.hire_date.data,
            salary=form.salary.data,
            tax_id=form.tax_id.data,
            bank_name=form.bank_name.data,
            bank_account=form.bank_account.data,
            address=form.address.data
        )
        
        db.session.add(employee)
        db.session.commit()
        
        flash(f'Employee added successfully! Username: {generated_username}  Password: employee123', 'success')
        return redirect(url_for('employees.index'))
    
    return render_template('employees/add.html', form=form)

@employees_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to edit employees', 'error')
        return redirect(url_for('employees.index'))
    
    employee = Employee.query.get_or_404(id)
    form = EmployeeForm(obj=employee)
    
    if form.validate_on_submit():
        # Check if email already exists (excluding current employee)
        existing_employee = Employee.query.filter(
            Employee.email == form.email.data,
            Employee.id != id
        ).first()
        
        if existing_employee:
            flash('Email already exists', 'error')
            return render_template('employees/edit.html', form=form, employee=employee)
        
        # Update employee
        form.populate_obj(employee)
        employee.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('employees.index'))
    
    return render_template('employees/edit.html', form=form, employee=employee)

@employees_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to delete employees', 'error')
        return redirect(url_for('employees.index'))
    
    employee = Employee.query.get_or_404(id)
    employee.is_active = False
    db.session.commit()
    
    flash('Employee deactivated successfully!', 'success')
    return redirect(url_for('employees.index'))

@employees_bp.route('/view/<int:id>')
@login_required
def view(id):
    employee = Employee.query.get_or_404(id)
    
    # Get recent payrolls
    recent_payrolls = employee.payrolls.order_by(db.desc('created_at')).limit(5).all()
    
    # Get recent attendance
    recent_attendance = employee.attendances.order_by(db.desc('date')).limit(10).all()
    
    return render_template('employees/view.html', 
                         employee=employee,
                         recent_payrolls=recent_payrolls,
                         recent_attendance=recent_attendance)

@employees_bp.route('/reset-password/<int:id>', methods=['POST'])
@login_required
def reset_password(id):
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to reset passwords', 'error')
        return redirect(url_for('employees.view', id=id))

    employee = Employee.query.get_or_404(id)
    user = employee.user
    if not user:
        flash('No user account associated with this employee', 'error')
        return redirect(url_for('employees.view', id=id))

    # Generate a secure temporary password
    temp_password = 'Emp!' + secrets.token_urlsafe(6)
    user.set_password(temp_password)
    user.last_login = None
    db.session.commit()

    flash(f"Password has been reset. Temporary password: {temp_password}", 'success')
    return redirect(url_for('employees.view', id=id))

@employees_bp.route('/set-password/<int:id>', methods=['POST'])
@login_required
def set_password(id):
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to set passwords', 'error')
        return redirect(url_for('employees.view', id=id))

    employee = Employee.query.get_or_404(id)
    user = employee.user
    if not user:
        flash('No user account associated with this employee', 'error')
        return redirect(url_for('employees.view', id=id))

    new_password = request.form.get('new_password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    if not new_password or not confirm_password:
        flash('Please provide and confirm the new password', 'error')
        return redirect(url_for('employees.view', id=id))

    if new_password != confirm_password:
        flash('Passwords do not match', 'error')
        return redirect(url_for('employees.view', id=id))

    if len(new_password) < 8:
        flash('Password must be at least 8 characters', 'error')
        return redirect(url_for('employees.view', id=id))

    user.set_password(new_password)
    db.session.commit()
    flash('Password updated successfully', 'success')
    return redirect(url_for('employees.view', id=id))

@employees_bp.route('/api/employees')
@login_required
def api_employees():
    employees = Employee.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': emp.id,
        'employee_id': emp.employee_id,
        'name': emp.full_name,
        'email': emp.email,
        'department': emp.department,
        'job_title': emp.job_title,
        'salary': float(emp.salary)
    } for emp in employees])

@employees_bp.route('/export')
@login_required
def export():
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to export employee data', 'error')
        return redirect(url_for('employees.index'))
    
    employees = Employee.query.filter_by(is_active=True).all()
    
    # Create CSV data
    csv_data = "Employee ID,Name,Email,Department,Job Title,Salary,Hire Date\n"
    for emp in employees:
        csv_data += f"{emp.employee_id},{emp.full_name},{emp.email},{emp.department},{emp.job_title},{emp.salary},{emp.hire_date}\n"
    
    return csv_data, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=employees.csv'
    }
