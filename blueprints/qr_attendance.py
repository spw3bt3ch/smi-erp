from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from models import User, Employee, Attendance, OfficeHours, OfficeLocation, db
from datetime import datetime, date, time, timedelta
from sqlalchemy import func, extract
import qrcode
import io
import base64
import secrets
import json

qr_attendance_bp = Blueprint('qr_attendance', __name__)

@qr_attendance_bp.route('/locations/manage', methods=['POST'])
@login_required
def manage_locations():
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to manage locations', 'error')
        return redirect(url_for('qr_attendance.index'))
    
    action = request.form.get('action')
    if action == 'create':
        try:
            name = request.form.get('name')
            address = request.form.get('address')
            radius = int(request.form.get('radius_meters') or 100)
            if not all([name, address]):
                raise ValueError('Name and address are required')
            loc = OfficeLocation(name=name, address=address, radius_meters=radius)
            db.session.add(loc)
            db.session.commit()
            flash('Office location added', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to add location: {str(e)}', 'error')
    elif action == 'deactivate':
        try:
            loc_id = request.form.get('id')
            loc = OfficeLocation.query.get(int(loc_id))
            if not loc:
                raise ValueError('Location not found')
            loc.active = False
            db.session.commit()
            flash('Office location deactivated', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update location: {str(e)}', 'error')
    return redirect(url_for('qr_attendance.index'))

def _load_locations_dict():
    locations = {}
    for loc in OfficeLocation.query.filter_by(active=True).all():
        locations[str(loc.id)] = loc.to_brief_dict()
    return locations

@qr_attendance_bp.route('/')
@login_required
def index():
    """QR Code attendance interface"""
    if current_user.role == 'employee' and current_user.employee:
        # Employee sees QR scanner interface
        active_locations = OfficeLocation.query.filter_by(active=True).all()
        return render_template('qr_attendance/employee_scanner.html', office_locations=active_locations)
    else:
        # Admin/HR sees QR code management
        return render_template('qr_attendance/admin_management.html', 
                             locations=_load_locations_dict())

@qr_attendance_bp.route('/generate-qr/<location_id>')
@login_required
def generate_qr(location_id):
    """Generate QR code for specific office location"""
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to generate QR codes', 'error')
        return redirect(url_for('qr_attendance.index'))
    
    locations = _load_locations_dict()
    if location_id not in locations:
        flash('Invalid location', 'error')
        return redirect(url_for('qr_attendance.index'))
    
    # Generate QR code data
    qr_data = {
        'location_id': location_id,
        'location_name': locations[location_id]['name'],
        'timestamp': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(hours=24)).isoformat(),
        'token': secrets.token_urlsafe(32)
    }
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(json.dumps(qr_data))
    qr.make(fit=True)
    
    # Generate QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 for embedding in HTML
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    return render_template('qr_attendance/qr_display.html',
                         qr_code=img_base64,
                         location=locations[location_id],
                         qr_data=qr_data)

@qr_attendance_bp.route('/scan', methods=['POST'])
@login_required
def scan_qr():
    """Process QR code scan for clock in/out"""
    if not current_user.employee:
        return jsonify({'success': False, 'message': 'Employee record not found'}), 400
    
    try:
        # Get QR code data from request
        qr_data = request.json.get('qr_data')
        if not qr_data:
            return jsonify({'success': False, 'message': 'QR code data missing'}), 400
        
        # Parse QR code data
        qr_info = json.loads(qr_data)
        
        # Validate QR code
        if not validate_qr_code(qr_info):
            return jsonify({'success': False, 'message': 'Invalid or expired QR code'}), 400
        
        # Check if employee is at correct location
        # For locations without coordinates, we skip GPS validation
        location_id = qr_info['location_id']
        locations = _load_locations_dict()
        if location_id not in locations:
            return jsonify({'success': False, 'message': 'Invalid location'}), 400
        
        # Process clock in/out
        today = date.today()
        existing_attendance = Attendance.query.filter_by(
            employee_id=current_user.employee.id,
            date=today
        ).first()
        
        if existing_attendance and existing_attendance.check_in and not existing_attendance.check_out:
            # Clock out
            return process_clock_out(existing_attendance, qr_info)
        else:
            # Clock in
            return process_clock_in(current_user.employee, qr_info, today)
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error processing QR code: {str(e)}'}), 400

def validate_qr_code(qr_info):
    """Validate QR code data"""
    try:
        # Check if QR code has expired
        expires_at = datetime.fromisoformat(qr_info['expires_at'])
        if datetime.now() > expires_at:
            return False
        
        # Check if location exists
        locations = _load_locations_dict()
        if qr_info['location_id'] not in locations:
            return False
        
        # Additional validation can be added here
        return True
    except:
        return False

def process_clock_in(employee, qr_info, today):
    """Process clock in with QR code validation"""
    # Check if already clocked in today
    existing = Attendance.query.filter_by(
        employee_id=employee.id,
        date=today
    ).first()
    
    if existing and existing.check_in:
        return jsonify({'success': False, 'message': 'Already clocked in today'}), 400
    
    # Get official office hours
    office_hours = OfficeHours.query.filter_by(is_default=True, is_active=True).first()
    current_time = datetime.now().time()
    status = 'present'
    notes = f"QR Clock-in at {qr_info['location_name']}"
    
    # Check if late arrival
    if office_hours:
        late_threshold = (datetime.combine(today, office_hours.official_clock_in) + 
                         timedelta(minutes=office_hours.clock_in_grace_period)).time()
        
        if current_time > late_threshold:
            status = 'late'
            minutes_late = int((datetime.combine(today, current_time) - 
                               datetime.combine(today, office_hours.official_clock_in)).total_seconds() / 60)
            notes += f" (Late by {minutes_late} minutes)"
    
    # Create or update attendance record
    if not existing:
        attendance = Attendance(
            employee_id=employee.id,
            date=today,
            check_in=current_time,
            status=status,
            notes=notes
        )
        db.session.add(attendance)
    else:
        existing.check_in = current_time
        existing.status = status
        existing.notes = notes
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'action': 'clock_in',
        'time': current_time.strftime('%H:%M:%S'),
        'location': qr_info['location_name'],
        'status': status
    })

def process_clock_out(attendance, qr_info):
    """Process clock out with QR code validation"""
    if attendance.check_out:
        return jsonify({'success': False, 'message': 'Already clocked out today'}), 400
    
    # Update clock out time
    current_time = datetime.now().time()
    attendance.check_out = current_time
    
    # Calculate hours worked
    check_in_dt = datetime.combine(attendance.date, attendance.check_in)
    check_out_dt = datetime.combine(attendance.date, current_time)
    hours_worked = (check_out_dt - check_in_dt).total_seconds() / 3600
    
    attendance.hours_worked = round(hours_worked, 2)
    
    # Get official office hours for overtime calculation
    office_hours = OfficeHours.query.filter_by(is_default=True, is_active=True).first()
    
    # Calculate overtime based on official hours
    if office_hours:
        official_hours = (datetime.combine(attendance.date, office_hours.official_clock_out) - 
                         datetime.combine(attendance.date, office_hours.official_clock_in)).total_seconds() / 3600
        
        if hours_worked > official_hours:
            attendance.overtime_hours = round(hours_worked - official_hours, 2)
        
        # Check for early departure
        early_threshold = (datetime.combine(attendance.date, office_hours.official_clock_out) - 
                          timedelta(minutes=office_hours.clock_out_grace_period)).time()
        
        if current_time < early_threshold:
            minutes_early = int((datetime.combine(attendance.date, office_hours.official_clock_out) - 
                                datetime.combine(attendance.date, current_time)).total_seconds() / 60)
            if attendance.notes:
                attendance.notes += f" | QR Clock-out at {qr_info['location_name']} (Early by {minutes_early} minutes)"
            else:
                attendance.notes = f"QR Clock-out at {qr_info['location_name']} (Early by {minutes_early} minutes)"
        else:
            if attendance.notes:
                attendance.notes += f" | QR Clock-out at {qr_info['location_name']}"
            else:
                attendance.notes = f"QR Clock-out at {qr_info['location_name']}"
    else:
        # Fallback to 8-hour calculation
        if hours_worked > 8:
            attendance.overtime_hours = round(hours_worked - 8, 2)
        
        if attendance.notes:
            attendance.notes += f" | QR Clock-out at {qr_info['location_name']}"
        else:
            attendance.notes = f"QR Clock-out at {qr_info['location_name']}"
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'action': 'clock_out',
        'time': current_time.strftime('%H:%M:%S'),
        'hours_worked': float(attendance.hours_worked),
        'overtime_hours': float(attendance.overtime_hours) if attendance.overtime_hours else 0,
        'location': qr_info['location_name']
    })

@qr_attendance_bp.route('/locations')
@login_required
def locations():
    """Get office locations for mobile app"""
    if current_user.role not in ['admin', 'hr']:
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify({
        'locations': OFFICE_LOCATIONS,
        'success': True
    })

@qr_attendance_bp.route('/validate-location', methods=['POST'])
@login_required
def validate_location():
    """Validate employee location (for future GPS integration)"""
    if not current_user.employee:
        return jsonify({'error': 'Employee record not found'}), 400
    
    try:
        data = request.json
        user_lat = data.get('latitude')
        user_lng = data.get('longitude')
        location_id = data.get('location_id')
        
        if not all([user_lat, user_lng, location_id]):
            return jsonify({'error': 'Missing location data'}), 400
        
        # Check if location exists
        locations = _load_locations_dict()
        if location_id not in locations:
            return jsonify({'error': 'Invalid location'}), 400
        
        # Calculate distance for GPS-enabled locations
        office = locations[location_id]
        
        # If location has no coordinates, skip GPS validation
        if not office['coordinates'] or not office['coordinates']['lat'] or not office['coordinates']['lng']:
            return jsonify({
                'success': True,
                'is_within_radius': True,
                'distance_meters': 0,
                'required_radius': office['radius'],
                'location_name': office['name'],
                'message': 'Location does not require GPS validation'
            })
        
        office_lat = office['coordinates']['lat']
        office_lng = office['coordinates']['lng']
        radius = office['radius']
        
        # Simple distance calculation (not accurate for real distances)
        distance = ((user_lat - office_lat) ** 2 + (user_lng - office_lng) ** 2) ** 0.5
        distance_meters = distance * 111000  # Rough conversion to meters
        
        is_within_radius = distance_meters <= radius
        
        return jsonify({
            'success': True,
            'is_within_radius': is_within_radius,
            'distance_meters': round(distance_meters, 2),
            'required_radius': radius,
            'location_name': office['name']
        })
        
    except Exception as e:
        return jsonify({'error': f'Location validation failed: {str(e)}'}), 400

@qr_attendance_bp.route('/attendance-history')
@login_required
def attendance_history():
    """Get employee attendance history with QR code info"""
    if current_user.role == 'employee' and current_user.employee:
        # Employee sees their own history
        employee_id = current_user.employee.id
    else:
        # Admin/HR can specify employee
        employee_id = request.args.get('employee_id', type=int)
        if not employee_id:
            return jsonify({'error': 'Employee ID required'}), 400
    
    # Get attendance records
    attendances = Attendance.query.filter_by(employee_id=employee_id)\
        .order_by(Attendance.date.desc()).limit(30).all()
    
    history = []
    for att in attendances:
        history.append({
            'date': att.date.strftime('%Y-%m-%d'),
            'check_in': att.check_in.strftime('%H:%M:%S') if att.check_in else None,
            'check_out': att.check_out.strftime('%H:%M:%S') if att.check_out else None,
            'hours_worked': float(att.hours_worked) if att.hours_worked else 0,
            'status': att.status,
            'notes': att.notes,
            'is_qr_attendance': 'QR' in (att.notes or '')
        })
    
    return jsonify({
        'success': True,
        'attendance_history': history
    })
