from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import User, Employee, Payroll, Attendance, OfficeLocation, db
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract
import traceback

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get basic statistics
        total_employees = Employee.query.filter_by(is_active=True).count()
        total_users = User.query.count()
        
        # Get payroll statistics
        total_payrolls = Payroll.query.count()
        processed_payrolls = Payroll.query.filter_by(status='processed').count()
        pending_payrolls = Payroll.query.filter_by(status='pending').count()
        
        # Get salary statistics
        total_salary_payout = db.session.query(func.sum(Payroll.net_salary)).filter_by(status='processed').scalar() or 0
        
        # Get recent payrolls
        recent_payrolls = Payroll.query.join(Employee).order_by(db.desc('created_at')).limit(5).all()
        
        # Get department statistics
        dept_stats = db.session.query(
            Employee.department,
            func.count(Employee.id).label('count'),
            func.avg(Employee.salary).label('avg_salary')
        ).filter_by(is_active=True).group_by(Employee.department).all()
        
        # Convert to list of dictionaries for JSON serialization
        dept_stats = [{'department': dept.department, 'count': dept.count, 'avg_salary': float(dept.avg_salary)} for dept in dept_stats]
        
        # Get monthly payroll trends (last 6 months)
        six_months_ago = date.today() - timedelta(days=180)
        monthly_trends = db.session.query(
            extract('year', Payroll.pay_period_start).label('year'),
            extract('month', Payroll.pay_period_start).label('month'),
            func.count(Payroll.id).label('count'),
            func.sum(Payroll.net_salary).label('total_salary')
        ).filter(
            Payroll.pay_period_start >= six_months_ago,
            Payroll.status == 'processed'
        ).group_by(
            extract('year', Payroll.pay_period_start),
            extract('month', Payroll.pay_period_start)
        ).order_by(
            extract('year', Payroll.pay_period_start),
            extract('month', Payroll.pay_period_start)
        ).all()
        
        # Convert to list of dictionaries for JSON serialization
        monthly_trends = [{'year': int(trend.year), 'month': int(trend.month), 'count': trend.count, 'total_salary': float(trend.total_salary)} for trend in monthly_trends]
        
        # Get attendance statistics for today
        today_attendance = Attendance.query.filter_by(date=date.today()).count()
        today_present = Attendance.query.filter_by(date=date.today(), status='present').count()
        today_absent = Attendance.query.filter_by(date=date.today(), status='absent').count()
        
        # Get office locations
        office_locations = OfficeLocation.query.filter_by(active=True).all()
        
        stats = {
            'total_employees': total_employees,
            'total_users': total_users,
            'total_payrolls': total_payrolls,
            'processed_payrolls': processed_payrolls,
            'pending_payrolls': pending_payrolls,
            'total_salary_payout': float(total_salary_payout),
            'dept_stats': dept_stats,
            'monthly_trends': monthly_trends,
            'today_attendance': today_attendance,
            'today_present': today_present,
            'today_absent': today_absent
        }
    
        return render_template('admin/dashboard.html', stats=stats, recent_payrolls=recent_payrolls, office_locations=office_locations)
    except Exception as e:
        print(f"Dashboard error: {e}")
        import traceback
        traceback.print_exc()
        flash('An error occurred while loading the dashboard. Please try again.', 'error')
        return render_template('admin/dashboard.html', stats={}, recent_payrolls=[], office_locations=[])

@admin_bp.route('/create-users')
@login_required
def create_users():
    """Create default users if they don't exist (for production setup)"""
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
            flash('Admin user created successfully!', 'success')
        else:
            flash('Admin user already exists', 'info')
        
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
            flash('HR user created successfully!', 'success')
        else:
            flash('HR user already exists', 'info')
        
        db.session.commit()
        return redirect(url_for('admin.dashboard'))
        
    except Exception as e:
        flash(f'Error creating users: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/test')
def test():
    """Simple test route without authentication"""
    return jsonify({
        "status": "ok",
        "message": "Admin blueprint is working",
        "current_user_authenticated": current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False
    })

@admin_bp.route('/debug')
def debug():
    """Debug endpoint to check admin dashboard issues"""
    try:
        from models import User, Employee, Payroll, Attendance, OfficeLocation
        
        debug_info = {
            "status": "ok",
            "current_user": {
                "authenticated": current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False,
                "username": getattr(current_user, 'username', 'None'),
                "role": getattr(current_user, 'role', 'None')
            },
            "database": {
                "users_count": User.query.count(),
                "employees_count": Employee.query.count(),
                "payrolls_count": Payroll.query.count(),
                "attendance_count": Attendance.query.count(),
                "office_locations_count": OfficeLocation.query.count()
            }
        }
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": str(traceback.format_exc())
        }), 500

@admin_bp.route('/reports')
@login_required
def reports():
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to view reports', 'error')
        return redirect(url_for('admin.dashboard'))
    
    # Get filter parameters
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))
    department = request.args.get('department', '')
    
    # Convert string dates to date objects
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
    
    # Build query
    query = Payroll.query.join(Employee).filter(
        Payroll.pay_period_start >= start_date,
        Payroll.pay_period_start <= end_date
    )
    
    if department:
        query = query.filter(Employee.department == department)
    
    payrolls = query.order_by(db.desc('created_at')).all()
    
    # Get departments for filter
    departments = db.session.query(Employee.department).distinct().all()
    departments = [dept[0] for dept in departments if dept[0]]
    
    # Calculate summary statistics
    total_payrolls = len(payrolls)
    total_gross = sum(float(p.gross_salary) for p in payrolls)
    total_deductions = sum(float(p.total_deductions) for p in payrolls)
    total_net = sum(float(p.net_salary) for p in payrolls)
    
    summary = {
        'total_payrolls': total_payrolls,
        'total_gross': total_gross,
        'total_deductions': total_deductions,
        'total_net': total_net
    }
    
    return render_template('admin/reports.html', 
                         payrolls=payrolls,
                         summary=summary,
                         start_date=start_date.strftime('%Y-%m-%d'),
                         end_date=end_date.strftime('%Y-%m-%d'),
                         department=department,
                         departments=departments)

@admin_bp.route('/attendance')
@login_required
def attendance():
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to view attendance', 'error')
        return redirect(url_for('admin.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    employee_id = request.args.get('employee_id', '', type=str)
    
    try:
        date_filter = datetime.strptime(date_filter, '%Y-%m-%d').date()
    except ValueError:
        date_filter = date.today()
    
    query = Attendance.query.filter_by(date=date_filter)
    
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    
    attendances = query.join(Employee).order_by(Employee.first_name).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get employees for filter
    employees = Employee.query.filter_by(is_active=True).all()
    
    return render_template('admin/attendance.html',
                         attendances=attendances,
                         date_filter=date_filter.strftime('%Y-%m-%d'),
                         employee_id=employee_id,
                         employees=employees)

@admin_bp.route('/attendance/add', methods=['POST'])
@login_required
def add_attendance():
    if current_user.role not in ['admin', 'hr']:
        return jsonify({'success': False, 'message': 'Permission denied'})
    
    data = request.get_json()
    
    try:
        # Check if attendance already exists
        existing = Attendance.query.filter_by(
            employee_id=data['employee_id'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date()
        ).first()
        
        if existing:
            return jsonify({'success': False, 'message': 'Attendance already recorded for this date'})
        
        # Parse times
        check_in = None
        check_out = None
        hours_worked = 0
        
        if data.get('check_in'):
            check_in = datetime.strptime(data['check_in'], '%H:%M').time()
        if data.get('check_out'):
            check_out = datetime.strptime(data['check_out'], '%H:%M').time()
        
        # Calculate hours worked
        if check_in and check_out:
            check_in_dt = datetime.combine(datetime.strptime(data['date'], '%Y-%m-%d').date(), check_in)
            check_out_dt = datetime.combine(datetime.strptime(data['date'], '%Y-%m-%d').date(), check_out)
            hours_worked = (check_out_dt - check_in_dt).total_seconds() / 3600
            
            # Calculate overtime (assuming 8 hours is normal)
            if hours_worked > 8:
                overtime_hours = hours_worked - 8
            else:
                overtime_hours = 0
        else:
            overtime_hours = 0
        
        attendance = Attendance(
            employee_id=data['employee_id'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            check_in=check_in,
            check_out=check_out,
            hours_worked=hours_worked,
            overtime_hours=overtime_hours,
            status=data['status'],
            notes=data.get('notes', '')
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Attendance recorded successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/users')
@login_required
def users():
    if current_user.role != 'admin':
        flash('You do not have permission to view users', 'error')
        return redirect(url_for('admin.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role', '', type=str)
    
    query = User.query
    
    if role_filter:
        query = query.filter_by(role=role_filter)
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html', users=users, role_filter=role_filter)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('You do not have permission to delete users', 'error')
        return redirect(url_for('admin.users'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin.users'))
    
    # Prevent deleting the last admin
    if user.role == 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            flash('Cannot delete the last admin user', 'error')
            return redirect(url_for('admin.users'))
    
    try:
        # Delete associated employee record if exists
        if user.employee:
            db.session.delete(user.employee)
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User {user.username} has been deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_users():
    if current_user.role != 'admin':
        flash('You do not have permission to delete users', 'error')
        return redirect(url_for('admin.users'))
    
    user_ids = request.form.getlist('user_ids')
    
    if not user_ids:
        flash('No users selected for deletion', 'error')
        return redirect(url_for('admin.users'))
    
    # Prevent admin from deleting themselves
    if str(current_user.id) in user_ids:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin.users'))
    
    # Check if trying to delete all admins
    selected_users = User.query.filter(User.id.in_(user_ids)).all()
    admin_users = [u for u in selected_users if u.role == 'admin']
    remaining_admins = User.query.filter_by(role='admin').filter(~User.id.in_(user_ids)).count()
    
    if admin_users and remaining_admins == 0:
        flash('Cannot delete all admin users', 'error')
        return redirect(url_for('admin.users'))
    
    deleted_count = 0
    try:
        for user in selected_users:
            # Delete associated employee record if exists
            if user.employee:
                db.session.delete(user.employee)
            
            # Delete the user
            db.session.delete(user)
            deleted_count += 1
        
        db.session.commit()
        flash(f'{deleted_count} users have been deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting users: {str(e)}', 'error')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/delete-all', methods=['POST'])
@login_required
def delete_all_users():
    if current_user.role != 'admin':
        flash('You do not have permission to delete users', 'error')
        return redirect(url_for('admin.users'))
    
    # Get all users except the current admin
    users_to_delete = User.query.filter(User.id != current_user.id).all()
    
    if not users_to_delete:
        flash('No users to delete', 'info')
        return redirect(url_for('admin.users'))
    
    deleted_count = 0
    try:
        for user in users_to_delete:
            # Delete associated employee record if exists
            if user.employee:
                db.session.delete(user.employee)
            
            # Delete the user
            db.session.delete(user)
            deleted_count += 1
        
        db.session.commit()
        flash(f'All {deleted_count} users have been deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting users: {str(e)}', 'error')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/api/stats')
@login_required
def api_stats():
    # Get monthly payroll data for charts
    monthly_data = db.session.query(
        extract('year', Payroll.pay_period_start).label('year'),
        extract('month', Payroll.pay_period_start).label('month'),
        func.count(Payroll.id).label('count'),
        func.sum(Payroll.net_salary).label('total_salary')
    ).filter(
        Payroll.status == 'processed'
    ).group_by(
        extract('year', Payroll.pay_period_start),
        extract('month', Payroll.pay_period_start)
    ).order_by(
        extract('year', Payroll.pay_period_start),
        extract('month', Payroll.pay_period_start)
    ).all()
    
    # Get department distribution
    dept_data = db.session.query(
        Employee.department,
        func.count(Employee.id).label('count')
    ).filter_by(is_active=True).group_by(Employee.department).all()
    
    return jsonify({
        'monthly_payrolls': [{'month': f"{int(m.year)}-{int(m.month):02d}", 'count': m.count, 'total': float(m.total_salary)} for m in monthly_data],
        'department_distribution': [{'department': d.department, 'count': d.count} for d in dept_data]
    })
