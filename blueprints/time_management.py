from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import OfficeHours, AttendancePolicy, Employee, Attendance, db
from datetime import datetime, time, timedelta
from sqlalchemy import func, extract

time_management_bp = Blueprint('time_management', __name__)

@time_management_bp.route('/')
@login_required
def index():
    """Time management dashboard"""
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to access time management', 'error')
        return redirect(url_for('admin.dashboard'))
    
    # Get office hours
    office_hours = OfficeHours.query.filter_by(is_active=True).all()
    default_hours = OfficeHours.query.filter_by(is_default=True, is_active=True).first()
    
    # Get attendance policies
    policies = AttendancePolicy.query.filter_by(is_active=True).all()
    default_policy = AttendancePolicy.query.filter_by(is_default=True, is_active=True).first()
    
    # Get today's attendance statistics
    today = datetime.now().date()
    total_employees = Employee.query.filter_by(is_active=True).count()
    clocked_in_today = Attendance.query.filter_by(date=today).filter(Attendance.check_in.isnot(None)).count()
    late_arrivals = 0
    early_departures = 0
    
    if default_hours:
        # Calculate late arrivals and early departures
        late_threshold = datetime.combine(today, default_hours.official_clock_in) + timedelta(minutes=default_hours.clock_in_grace_period)
        early_threshold = datetime.combine(today, default_hours.official_clock_out) - timedelta(minutes=default_hours.clock_out_grace_period)
        
        late_arrivals = Attendance.query.filter_by(date=today)\
            .filter(Attendance.check_in > late_threshold.time()).count()
        
        early_departures = Attendance.query.filter_by(date=today)\
            .filter(Attendance.check_out < early_threshold.time())\
            .filter(Attendance.check_out.isnot(None)).count()
    
    return render_template('time_management/index.html',
                         office_hours=office_hours,
                         default_hours=default_hours,
                         policies=policies,
                         default_policy=default_policy,
                         total_employees=total_employees,
                         clocked_in_today=clocked_in_today,
                         late_arrivals=late_arrivals,
                         early_departures=early_departures)

@time_management_bp.route('/office-hours')
@login_required
def office_hours():
    """Manage office hours"""
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to manage office hours', 'error')
        return redirect(url_for('time_management.index'))
    
    office_hours = OfficeHours.query.filter_by(is_active=True).all()
    return render_template('time_management/office_hours.html', office_hours=office_hours)

@time_management_bp.route('/office-hours/add', methods=['GET', 'POST'])
@login_required
def add_office_hours():
    """Add new office hours"""
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to add office hours', 'error')
        return redirect(url_for('time_management.index'))
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            description = request.form.get('description')
            official_clock_in = time.fromisoformat(request.form.get('official_clock_in'))
            official_clock_out = time.fromisoformat(request.form.get('official_clock_out'))
            clock_in_grace = int(request.form.get('clock_in_grace_period', 15))
            clock_out_grace = int(request.form.get('clock_out_grace_period', 15))
            break_duration = int(request.form.get('break_duration', 60))
            break_start = request.form.get('break_start_time')
            working_days = request.form.getlist('working_days')
            allow_early_clock_in = 'allow_early_clock_in' in request.form
            allow_late_clock_out = 'allow_late_clock_out' in request.form
            is_default = 'is_default' in request.form
            
            # If this is set as default, unset other defaults
            if is_default:
                OfficeHours.query.update({'is_default': False})
            
            # Create office hours
            office_hour = OfficeHours(
                name=name,
                description=description,
                official_clock_in=official_clock_in,
                official_clock_out=official_clock_out,
                clock_in_grace_period=clock_in_grace,
                clock_out_grace_period=clock_out_grace,
                break_duration=break_duration,
                break_start_time=time.fromisoformat(break_start) if break_start else None,
                working_days=','.join(working_days),
                allow_early_clock_in=allow_early_clock_in,
                allow_late_clock_out=allow_late_clock_out,
                is_default=is_default
            )
            
            db.session.add(office_hour)
            db.session.commit()
            
            flash('Office hours added successfully!', 'success')
            return redirect(url_for('time_management.office_hours'))
            
        except Exception as e:
            flash(f'Error adding office hours: {str(e)}', 'error')
            return redirect(url_for('time_management.add_office_hours'))
    
    return render_template('time_management/add_office_hours.html')

@time_management_bp.route('/office-hours/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_office_hours(id):
    """Edit office hours"""
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to edit office hours', 'error')
        return redirect(url_for('time_management.index'))
    
    office_hour = OfficeHours.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Update office hours
            office_hour.name = request.form.get('name')
            office_hour.description = request.form.get('description')
            office_hour.official_clock_in = time.fromisoformat(request.form.get('official_clock_in'))
            office_hour.official_clock_out = time.fromisoformat(request.form.get('official_clock_out'))
            office_hour.clock_in_grace_period = int(request.form.get('clock_in_grace_period', 15))
            office_hour.clock_out_grace_period = int(request.form.get('clock_out_grace_period', 15))
            office_hour.break_duration = int(request.form.get('break_duration', 60))
            break_start = request.form.get('break_start_time')
            office_hour.break_start_time = time.fromisoformat(break_start) if break_start else None
            office_hour.working_days = ','.join(request.form.getlist('working_days'))
            office_hour.allow_early_clock_in = 'allow_early_clock_in' in request.form
            office_hour.allow_late_clock_out = 'allow_late_clock_out' in request.form
            is_default = 'is_default' in request.form
            
            # If this is set as default, unset other defaults
            if is_default:
                OfficeHours.query.filter(OfficeHours.id != id).update({'is_default': False})
            
            office_hour.is_default = is_default
            office_hour.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('Office hours updated successfully!', 'success')
            return redirect(url_for('time_management.office_hours'))
            
        except Exception as e:
            flash(f'Error updating office hours: {str(e)}', 'error')
            return redirect(url_for('time_management.edit_office_hours', id=id))
    
    return render_template('time_management/edit_office_hours.html', office_hour=office_hour)

@time_management_bp.route('/office-hours/delete/<int:id>', methods=['POST'])
@login_required
def delete_office_hours(id):
    """Delete office hours"""
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to delete office hours', 'error')
        return redirect(url_for('time_management.index'))
    
    office_hour = OfficeHours.query.get_or_404(id)
    
    # Don't allow deleting default office hours
    if office_hour.is_default:
        flash('Cannot delete default office hours', 'error')
        return redirect(url_for('time_management.office_hours'))
    
    office_hour.is_active = False
    db.session.commit()
    
    flash('Office hours deleted successfully!', 'success')
    return redirect(url_for('time_management.office_hours'))

@time_management_bp.route('/attendance-policies')
@login_required
def attendance_policies():
    """Manage attendance policies"""
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to manage attendance policies', 'error')
        return redirect(url_for('time_management.index'))
    
    policies = AttendancePolicy.query.filter_by(is_active=True).all()
    return render_template('time_management/attendance_policies.html', policies=policies)

@time_management_bp.route('/attendance-policies/add', methods=['GET', 'POST'])
@login_required
def add_attendance_policy():
    """Add new attendance policy"""
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to add attendance policies', 'error')
        return redirect(url_for('time_management.index'))
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            description = request.form.get('description')
            
            # Late arrival settings
            late_penalty_type = request.form.get('late_penalty_type', 'warning')
            late_penalty_amount = float(request.form.get('late_penalty_amount', 0))
            late_penalty_threshold = int(request.form.get('late_penalty_threshold', 30))
            
            # Early departure settings
            early_departure_penalty_type = request.form.get('early_departure_penalty_type', 'warning')
            early_departure_penalty_amount = float(request.form.get('early_departure_penalty_amount', 0))
            early_departure_threshold = int(request.form.get('early_departure_threshold', 30))
            
            # Absence settings
            absence_penalty_type = request.form.get('absence_penalty_type', 'deduction')
            absence_penalty_amount = float(request.form.get('absence_penalty_amount', 500))
            
            # Overtime settings
            overtime_rate = float(request.form.get('overtime_rate', 1.5))
            overtime_threshold = int(request.form.get('overtime_threshold', 480))
            
            is_default = 'is_default' in request.form
            
            # If this is set as default, unset other defaults
            if is_default:
                AttendancePolicy.query.update({'is_default': False})
            
            # Create policy
            policy = AttendancePolicy(
                name=name,
                description=description,
                late_penalty_type=late_penalty_type,
                late_penalty_amount=late_penalty_amount,
                late_penalty_threshold=late_penalty_threshold,
                early_departure_penalty_type=early_departure_penalty_type,
                early_departure_penalty_amount=early_departure_penalty_amount,
                early_departure_threshold=early_departure_threshold,
                absence_penalty_type=absence_penalty_type,
                absence_penalty_amount=absence_penalty_amount,
                overtime_rate=overtime_rate,
                overtime_threshold=overtime_threshold,
                is_default=is_default
            )
            
            db.session.add(policy)
            db.session.commit()
            
            flash('Attendance policy added successfully!', 'success')
            return redirect(url_for('time_management.attendance_policies'))
            
        except Exception as e:
            flash(f'Error adding attendance policy: {str(e)}', 'error')
            return redirect(url_for('time_management.add_attendance_policy'))
    
    return render_template('time_management/add_attendance_policy.html')

@time_management_bp.route('/reports')
@login_required
def reports():
    """Attendance reports and analytics"""
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to view reports', 'error')
        return redirect(url_for('time_management.index'))
    
    # Get date range
    date_from = request.args.get('date_from', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.args.get('date_to', datetime.now().strftime('%Y-%m-%d'))
    
    # Convert to date objects
    try:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    except:
        date_from = (datetime.now() - timedelta(days=30)).date()
        date_to = datetime.now().date()
    
    # Get attendance data
    attendances = Attendance.query.filter(
        Attendance.date >= date_from,
        Attendance.date <= date_to
    ).all()
    
    # Calculate statistics
    total_days = (date_to - date_from).days + 1
    total_attendance_records = len(attendances)
    
    # Late arrivals and early departures
    default_hours = OfficeHours.query.filter_by(is_default=True, is_active=True).first()
    late_arrivals = 0
    early_departures = 0
    
    if default_hours:
        for att in attendances:
            if att.check_in and att.check_in > default_hours.official_clock_in:
                late_arrivals += 1
            if att.check_out and att.check_out < default_hours.official_clock_out:
                early_departures += 1
    
    return render_template('time_management/reports.html',
                         attendances=attendances,
                         date_from=date_from,
                         date_to=date_to,
                         total_days=total_days,
                         total_attendance_records=total_attendance_records,
                         late_arrivals=late_arrivals,
                         early_departures=early_departures,
                         default_hours=default_hours)

@time_management_bp.route('/api/attendance-stats')
@login_required
def attendance_stats_api():
    """API endpoint for attendance statistics"""
    if current_user.role not in ['admin', 'hr']:
        return jsonify({'error': 'Access denied'}), 403
    
    # Get statistics for the last 30 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Daily attendance counts
    daily_stats = db.session.query(
        Attendance.date,
        func.count(Attendance.id).label('total_attendance'),
        func.count(Attendance.check_in).label('clocked_in'),
        func.count(Attendance.check_out).label('clocked_out')
    ).filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).group_by(Attendance.date).all()
    
    # Convert to list of dictionaries
    stats = []
    for stat in daily_stats:
        stats.append({
            'date': stat.date.strftime('%Y-%m-%d'),
            'total_attendance': stat.total_attendance,
            'clocked_in': stat.clocked_in,
            'clocked_out': stat.clocked_out
        })
    
    return jsonify({
        'success': True,
        'stats': stats
    })
