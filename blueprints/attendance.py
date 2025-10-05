from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import User, Employee, Attendance, db
from datetime import datetime, date, time, timedelta
from sqlalchemy import func, extract

attendance_bp = Blueprint('attendance', __name__)

# Helper function to get CSRF token
def get_csrf_token():
    from flask_wtf.csrf import generate_csrf
    return generate_csrf()

@attendance_bp.route('/')
@login_required
def index():
    """View attendance - employees see their own, HR/admin see all"""
    if current_user.role == 'employee' and current_user.employee:
        # Employee sees only their attendance
        employee_id = current_user.employee.id
        today_attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=date.today()
        ).first()
        
        # Get recent attendance records
        recent_attendance = Attendance.query.filter_by(
            employee_id=employee_id
        ).order_by(Attendance.date.desc()).limit(30).all()
        
        return render_template('attendance/employee_attendance.html',
                             today=today_attendance,
                             recent=recent_attendance)
    else:
        # HR/Admin sees all attendance
        page = request.args.get('page', 1, type=int)
        employee_id = request.args.get('employee_id', '', type=str)
        date_from = request.args.get('date_from', '', type=str)
        date_to = request.args.get('date_to', '', type=str)
        
        query = Attendance.query
        
        if employee_id:
            query = query.filter(Attendance.employee_id == employee_id)
        
        if date_from:
            query = query.filter(Attendance.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
        
        if date_to:
            query = query.filter(Attendance.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
        
        attendances = query.order_by(Attendance.date.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        employees = Employee.query.filter_by(is_active=True).all()
        
        return render_template('attendance/admin_attendance.html',
                             attendances=attendances,
                             employees=employees,
                             employee_id=employee_id,
                             date_from=date_from,
                             date_to=date_to)

@attendance_bp.route('/clock-in', methods=['POST'])
@login_required
def clock_in():
    """Employee clocks in"""
    # Handle CSRF validation
    from flask_wtf.csrf import validate_csrf
    from wtforms import ValidationError
    
    try:
        # Try to validate CSRF token from form data
        validate_csrf(request.form.get('csrf_token'))
    except ValidationError:
        # If form validation fails, try header validation
        csrf_token = request.headers.get('X-CSRFToken')
        if not csrf_token:
            return jsonify({'success': False, 'message': 'CSRF token missing'}), 400
        try:
            validate_csrf(csrf_token)
        except ValidationError:
            return jsonify({'success': False, 'message': 'Invalid CSRF token'}), 400
    
    if not current_user.employee:
        return jsonify({'success': False, 'message': 'Employee record not found'}), 400
    
    today = date.today()
    
    # Check if already clocked in today
    existing = Attendance.query.filter_by(
        employee_id=current_user.employee.id,
        date=today
    ).first()
    
    if existing and existing.check_in:
        return jsonify({'success': False, 'message': 'Already clocked in today'}), 400
    
    # Create or update attendance record
    if not existing:
        attendance = Attendance(
            employee_id=current_user.employee.id,
            date=today,
            check_in=datetime.now().time(),
            status='present'
        )
        db.session.add(attendance)
    else:
        existing.check_in = datetime.now().time()
        existing.status = 'present'
    
    db.session.commit()
    
    flash('Clocked in successfully!', 'success')
    return jsonify({'success': True, 'time': datetime.now().strftime('%H:%M:%S')})

@attendance_bp.route('/clock-out', methods=['POST'])
@login_required
def clock_out():
    """Employee clocks out"""
    # Handle CSRF validation
    from flask_wtf.csrf import validate_csrf
    from wtforms import ValidationError
    
    try:
        # Try to validate CSRF token from form data
        validate_csrf(request.form.get('csrf_token'))
    except ValidationError:
        # If form validation fails, try header validation
        csrf_token = request.headers.get('X-CSRFToken')
        if not csrf_token:
            return jsonify({'success': False, 'message': 'CSRF token missing'}), 400
        try:
            validate_csrf(csrf_token)
        except ValidationError:
            return jsonify({'success': False, 'message': 'Invalid CSRF token'}), 400
    
    if not current_user.employee:
        return jsonify({'success': False, 'message': 'Employee record not found'}), 400
    
    today = date.today()
    
    # Get today's attendance
    attendance = Attendance.query.filter_by(
        employee_id=current_user.employee.id,
        date=today
    ).first()
    
    if not attendance or not attendance.check_in:
        return jsonify({'success': False, 'message': 'Please clock in first'}), 400
    
    if attendance.check_out:
        return jsonify({'success': False, 'message': 'Already clocked out today'}), 400
    
    # Update clock out time
    attendance.check_out = datetime.now().time()
    
    # Calculate hours worked
    check_in_dt = datetime.combine(today, attendance.check_in)
    check_out_dt = datetime.combine(today, attendance.check_out)
    hours_worked = (check_out_dt - check_in_dt).total_seconds() / 3600
    
    attendance.hours_worked = round(hours_worked, 2)
    
    # Calculate overtime (over 8 hours)
    if hours_worked > 8:
        attendance.overtime_hours = round(hours_worked - 8, 2)
    
    # Check if late (after 9:00 AM)
    if attendance.check_in > time(9, 0):
        attendance.status = 'late'
    
    db.session.commit()
    
    flash('Clocked out successfully!', 'success')
    return jsonify({
        'success': True,
        'time': datetime.now().strftime('%H:%M:%S'),
        'hours_worked': float(attendance.hours_worked)
    })

@attendance_bp.route('/status')
@login_required
def status():
    """Get current attendance status"""
    if not current_user.employee:
        return jsonify({'error': 'No employee record'}), 400
    
    today = date.today()
    attendance = Attendance.query.filter_by(
        employee_id=current_user.employee.id,
        date=today
    ).first()
    
    if not attendance:
        return jsonify({
            'clocked_in': False,
            'clocked_out': False
        })
    
    return jsonify({
        'clocked_in': attendance.check_in is not None,
        'clocked_out': attendance.check_out is not None,
        'check_in_time': attendance.check_in.strftime('%H:%M:%S') if attendance.check_in else None,
        'check_out_time': attendance.check_out.strftime('%H:%M:%S') if attendance.check_out else None,
        'hours_worked': float(attendance.hours_worked) if attendance.hours_worked else 0
    })

@attendance_bp.route('/export')
@login_required
def export():
    """Export attendance data to CSV"""
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to export attendance data', 'error')
        return redirect(url_for('attendance.index'))
    
    import csv
    from flask import make_response
    from io import StringIO
    
    # Get filter parameters
    employee_id = request.args.get('employee_id', '', type=str)
    date_from = request.args.get('date_from', '', type=str)
    date_to = request.args.get('date_to', '', type=str)
    
    query = Attendance.query.join(Employee)
    
    if employee_id:
        query = query.filter(Attendance.employee_id == employee_id)
    
    if date_from:
        query = query.filter(Attendance.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    
    if date_to:
        query = query.filter(Attendance.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    
    attendances = query.order_by(Attendance.date.desc()).all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Employee ID', 'Employee Name', 'Date', 'Check In', 'Check Out',
        'Hours Worked', 'Overtime Hours', 'Status', 'Notes'
    ])
    
    # Write data
    for att in attendances:
        writer.writerow([
            att.employee.employee_id,
            att.employee.full_name,
            att.date.strftime('%Y-%m-%d'),
            att.check_in.strftime('%H:%M:%S') if att.check_in else '',
            att.check_out.strftime('%H:%M:%S') if att.check_out else '',
            float(att.hours_worked) if att.hours_worked else 0,
            float(att.overtime_hours) if att.overtime_hours else 0,
            att.status,
            att.notes or ''
        ])
    
    # Create response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=attendance_export_{date.today().strftime("%Y%m%d")}.csv'
    
    return response

@attendance_bp.route('/api/stats')
@login_required
def api_stats():
    """Get attendance statistics for charts"""
    if current_user.role not in ['admin', 'hr']:
        return jsonify({'error': 'Access denied'}), 403
    
    # Get monthly attendance data
    monthly_data = db.session.query(
        extract('year', Attendance.date).label('year'),
        extract('month', Attendance.date).label('month'),
        func.count(Attendance.id).label('total_days'),
        func.avg(Attendance.hours_worked).label('avg_hours'),
        func.sum(Attendance.overtime_hours).label('total_overtime')
    ).filter(
        Attendance.check_in.isnot(None)
    ).group_by(
        extract('year', Attendance.date),
        extract('month', Attendance.date)
    ).order_by(
        extract('year', Attendance.date),
        extract('month', Attendance.date)
    ).all()
    
    # Get department attendance stats
    dept_stats = db.session.query(
        Employee.department,
        func.count(Attendance.id).label('total_attendance'),
        func.avg(Attendance.hours_worked).label('avg_hours')
    ).join(Attendance).filter(
        Attendance.check_in.isnot(None)
    ).group_by(Employee.department).all()
    
    return jsonify({
        'monthly_attendance': [
            {
                'month': f"{int(m.year)}-{int(m.month):02d}",
                'total_days': m.total_days,
                'avg_hours': float(m.avg_hours) if m.avg_hours else 0,
                'total_overtime': float(m.total_overtime) if m.total_overtime else 0
            } for m in monthly_data
        ],
        'department_stats': [
            {
                'department': d.department,
                'total_attendance': d.total_attendance,
                'avg_hours': float(d.avg_hours) if d.avg_hours else 0
            } for d in dept_stats
        ]
    })
