from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import Employee, Payroll, User, db
from datetime import datetime, date

api_bp = Blueprint('api', __name__)

@api_bp.route('/employees')
@login_required
def get_employees():
    """Get all employees (filtered by role)"""
    if current_user.role == 'employee':
        employee = Employee.query.filter_by(user_id=current_user.id).first()
        if not employee:
            return jsonify({'error': 'Employee record not found'}), 404
        
        return jsonify({
            'id': employee.id,
            'employee_id': employee.employee_id,
            'name': employee.full_name,
            'email': employee.email,
            'department': employee.department,
            'job_title': employee.job_title,
            'salary': float(employee.salary)
        })
    
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

@api_bp.route('/employees/<int:employee_id>')
@login_required
def get_employee(employee_id):
    """Get specific employee details"""
    employee = Employee.query.get_or_404(employee_id)
    
    # Check permissions
    if current_user.role == 'employee' and employee.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'id': employee.id,
        'employee_id': employee.employee_id,
        'name': employee.full_name,
        'email': employee.email,
        'phone': employee.phone,
        'department': employee.department,
        'job_title': employee.job_title,
        'salary': float(employee.salary),
        'hire_date': employee.hire_date.isoformat(),
        'tax_id': employee.tax_id,
        'bank_name': employee.bank_name,
        'bank_account': employee.bank_account,
        'address': employee.address
    })

@api_bp.route('/payrolls')
@login_required
def get_payrolls():
    """Get payrolls (filtered by role)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status = request.args.get('status', '')
    employee_id = request.args.get('employee_id', type=int)
    
    query = Payroll.query
    
    if current_user.role == 'employee':
        employee = Employee.query.filter_by(user_id=current_user.id).first()
        if not employee:
            return jsonify({'error': 'Employee record not found'}), 404
        query = query.filter_by(employee_id=employee.id)
    
    if status:
        query = query.filter_by(status=status)
    
    if employee_id and current_user.role in ['admin', 'hr']:
        query = query.filter_by(employee_id=employee_id)
    
    payrolls = query.order_by(db.desc('created_at')).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'payrolls': [{
            'id': p.id,
            'employee_name': p.employee.full_name,
            'employee_id': p.employee.employee_id,
            'pay_period_start': p.pay_period_start.isoformat(),
            'pay_period_end': p.pay_period_end.isoformat(),
            'basic_salary': float(p.basic_salary),
            'allowances': float(p.allowances),
            'overtime_pay': float(p.overtime_pay),
            'gross_salary': float(p.gross_salary),
            'total_deductions': float(p.total_deductions),
            'net_salary': float(p.net_salary),
            'status': p.status,
            'processed_at': p.processed_at.isoformat() if p.processed_at else None
        } for p in payrolls.items],
        'total': payrolls.total,
        'pages': payrolls.pages,
        'current_page': payrolls.page,
        'per_page': payrolls.per_page
    })

@api_bp.route('/payrolls/<int:payroll_id>')
@login_required
def get_payroll(payroll_id):
    """Get specific payroll details"""
    payroll = Payroll.query.get_or_404(payroll_id)
    
    # Check permissions
    if current_user.role == 'employee' and payroll.employee.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'id': payroll.id,
        'employee': {
            'id': payroll.employee.id,
            'employee_id': payroll.employee.employee_id,
            'name': payroll.employee.full_name,
            'department': payroll.employee.department
        },
        'pay_period_start': payroll.pay_period_start.isoformat(),
        'pay_period_end': payroll.pay_period_end.isoformat(),
        'basic_salary': float(payroll.basic_salary),
        'allowances': float(payroll.allowances),
        'overtime_pay': float(payroll.overtime_pay),
        'gross_salary': float(payroll.gross_salary),
        'tax_deduction': float(payroll.tax_deduction),
        'pension_deduction': float(payroll.pension_deduction),
        'loan_deduction': float(payroll.loan_deduction),
        'other_deductions': float(payroll.other_deductions),
        'total_deductions': float(payroll.total_deductions),
        'net_salary': float(payroll.net_salary),
        'status': payroll.status,
        'processed_at': payroll.processed_at.isoformat() if payroll.processed_at else None
    })

@api_bp.route('/payrolls', methods=['POST'])
@login_required
def create_payroll():
    """Create new payroll (admin/hr only)"""
    if current_user.role not in ['admin', 'hr']:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.get_json()
    
    try:
        # Validate required fields
        required_fields = ['employee_id', 'pay_period_start', 'pay_period_end', 'basic_salary']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if employee exists
        employee = Employee.query.get(data['employee_id'])
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        # Check if payroll already exists for this period
        existing = Payroll.query.filter(
            Payroll.employee_id == data['employee_id'],
            Payroll.pay_period_start == datetime.strptime(data['pay_period_start'], '%Y-%m-%d').date(),
            Payroll.pay_period_end == datetime.strptime(data['pay_period_end'], '%Y-%m-%d').date()
        ).first()
        
        if existing:
            return jsonify({'error': 'Payroll already exists for this period'}), 400
        
        # Calculate payroll
        basic_salary = float(data['basic_salary'])
        allowances = float(data.get('allowances', 0))
        overtime_pay = float(data.get('overtime_pay', 0))
        gross_salary = basic_salary + allowances + overtime_pay
        
        tax_deduction = float(data.get('tax_deduction', 0))
        pension_deduction = float(data.get('pension_deduction', 0))
        loan_deduction = float(data.get('loan_deduction', 0))
        other_deductions = float(data.get('other_deductions', 0))
        total_deductions = tax_deduction + pension_deduction + loan_deduction + other_deductions
        
        net_salary = gross_salary - total_deductions
        
        payroll = Payroll(
            employee_id=data['employee_id'],
            pay_period_start=datetime.strptime(data['pay_period_start'], '%Y-%m-%d').date(),
            pay_period_end=datetime.strptime(data['pay_period_end'], '%Y-%m-%d').date(),
            basic_salary=basic_salary,
            allowances=allowances,
            overtime_pay=overtime_pay,
            gross_salary=gross_salary,
            tax_deduction=tax_deduction,
            pension_deduction=pension_deduction,
            loan_deduction=loan_deduction,
            other_deductions=other_deductions,
            total_deductions=total_deductions,
            net_salary=net_salary,
            processed_by=current_user.id,
            processed_at=datetime.utcnow(),
            status='processed'
        )
        
        db.session.add(payroll)
        db.session.commit()
        
        return jsonify({
            'id': payroll.id,
            'message': 'Payroll created successfully'
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/stats')
@login_required
def get_stats():
    """Get dashboard statistics"""
    if current_user.role not in ['admin', 'hr']:
        return jsonify({'error': 'Permission denied'}), 403
    
    total_employees = Employee.query.filter_by(is_active=True).count()
    total_payrolls = Payroll.query.count()
    processed_payrolls = Payroll.query.filter_by(status='processed').count()
    pending_payrolls = Payroll.query.filter_by(status='pending').count()
    
    total_salary_payout = db.session.query(db.func.sum(Payroll.net_salary)).filter_by(status='processed').scalar() or 0
    
    return jsonify({
        'total_employees': total_employees,
        'total_payrolls': total_payrolls,
        'processed_payrolls': processed_payrolls,
        'pending_payrolls': pending_payrolls,
        'total_salary_payout': float(total_salary_payout)
    })

@api_bp.route('/departments')
@login_required
def get_departments():
    """Get all departments"""
    departments = db.session.query(Employee.department).distinct().all()
    departments = [dept[0] for dept in departments if dept[0]]
    
    return jsonify(departments)
