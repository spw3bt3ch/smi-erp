from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from models import Payroll, Employee, db
from forms import PayrollForm
from datetime import datetime, date
from decimal import Decimal
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

payroll_bp = Blueprint('payroll', __name__)

@payroll_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    employee_id = request.args.get('employee_id', '', type=str)
    month = request.args.get('month', '', type=str)
    
    query = Payroll.query
    
    # If user is an employee, only show their own payrolls
    if current_user.role == 'employee':
        query = query.join(Employee).filter(Employee.user_id == current_user.id)
    else:
        # For admin/hr, allow filtering by employee
        if employee_id:
            query = query.filter(Payroll.employee_id == employee_id)
    
    if status:
        query = query.filter(Payroll.status == status)
    
    if month:
        query = query.filter(db.extract('month', Payroll.pay_period_start) == int(month))
    
    payrolls = query.order_by(db.desc('created_at')).paginate(
        page=page, per_page=10, error_out=False
    )
    
    # Get employees for filter (only for admin/hr)
    employees = []
    if current_user.role in ['admin', 'hr']:
        employees = Employee.query.filter_by(is_active=True).all()
    
    return render_template('payroll/index.html', 
                         payrolls=payrolls,
                         status=status,
                         employee_id=employee_id,
                         month=month,
                         employees=employees)

@payroll_bp.route('/process', methods=['GET', 'POST'])
@login_required
def process():
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to process payroll', 'error')
        return redirect(url_for('payroll.index'))
    
    form = PayrollForm()
    
    # Populate employee choices
    form.employee_id.choices = [(emp.id, f"{emp.full_name} ({emp.employee_id})") 
                               for emp in Employee.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        employee = Employee.query.get(form.employee_id.data)
        
        # Calculate gross salary
        gross_salary = form.basic_salary.data + form.allowances.data + form.overtime_pay.data
        
        # Calculate total deductions
        total_deductions = (form.tax_deduction.data or 0) + \
                          (form.pension_deduction.data or 0) + \
                          (form.loan_deduction.data or 0) + \
                          (form.other_deductions.data or 0)
        
        # Calculate net salary
        net_salary = gross_salary - total_deductions
        
        # Create payroll record
        payroll = Payroll(
            employee_id=form.employee_id.data,
            pay_period_start=form.pay_period_start.data,
            pay_period_end=form.pay_period_end.data,
            basic_salary=form.basic_salary.data,
            allowances=form.allowances.data or 0,
            overtime_pay=form.overtime_pay.data or 0,
            gross_salary=gross_salary,
            tax_deduction=form.tax_deduction.data or 0,
            pension_deduction=form.pension_deduction.data or 0,
            loan_deduction=form.loan_deduction.data or 0,
            other_deductions=form.other_deductions.data or 0,
            total_deductions=total_deductions,
            net_salary=net_salary,
            processed_by=current_user.id,
            processed_at=datetime.utcnow(),
            status='processed'
        )
        
        db.session.add(payroll)
        db.session.commit()
        
        flash('Payroll processed successfully!', 'success')
        return redirect(url_for('payroll.index'))
    
    return render_template('payroll/process.html', form=form)

@payroll_bp.route('/view/<int:id>')
@login_required
def view(id):
    payroll = Payroll.query.get_or_404(id)
    
    # Check if user has permission to view this payroll
    if current_user.role == 'employee' and payroll.employee.user_id != current_user.id:
        flash('You do not have permission to view this payroll', 'error')
        return redirect(url_for('payroll.index'))
    
    return render_template('payroll/view.html', payroll=payroll)

@payroll_bp.route('/payslip/<int:id>')
@login_required
def payslip(id):
    payroll = Payroll.query.get_or_404(id)
    
    # Check if user has permission to view this payslip
    if current_user.role == 'employee' and payroll.employee.user_id != current_user.id:
        flash('You do not have permission to view this payslip', 'error')
        return redirect(url_for('payroll.index'))
    
    return render_template('payroll/payslip.html', payroll=payroll)

@payroll_bp.route('/download_pdf/<int:id>')
@login_required
def download_pdf(id):
    payroll = Payroll.query.get_or_404(id)
    
    # Check if user has permission to download this payslip
    if current_user.role == 'employee' and payroll.employee.user_id != current_user.id:
        flash('You do not have permission to download this payslip', 'error')
        return redirect(url_for('payroll.index'))
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title = Paragraph("PAYSLIP", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Employee details
    employee_data = [
        ['Employee ID:', payroll.employee.employee_id],
        ['Name:', payroll.employee.full_name],
        ['Department:', payroll.employee.department],
        ['Pay Period:', f"{payroll.pay_period_start} to {payroll.pay_period_end}"],
        ['Pay Date:', payroll.processed_at.strftime('%Y-%m-%d') if payroll.processed_at else 'N/A']
    ]
    
    employee_table = Table(employee_data, colWidths=[150, 200])
    employee_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
    ]))
    
    story.append(employee_table)
    story.append(Spacer(1, 20))
    
    # Payroll details
    payroll_data = [
        ['Earnings', 'Amount'],
        ['Basic Salary', f"${payroll.basic_salary:,.2f}"],
        ['Allowances', f"${payroll.allowances:,.2f}"],
        ['Overtime Pay', f"${payroll.overtime_pay:,.2f}"],
        ['', ''],
        ['Total Gross', f"${payroll.gross_salary:,.2f}"],
        ['', ''],
        ['Deductions', 'Amount'],
        ['Tax Deduction', f"${payroll.tax_deduction:,.2f}"],
        ['Pension Deduction', f"${payroll.pension_deduction:,.2f}"],
        ['Loan Deduction', f"${payroll.loan_deduction:,.2f}"],
        ['Other Deductions', f"${payroll.other_deductions:,.2f}"],
        ['', ''],
        ['Total Deductions', f"${payroll.total_deductions:,.2f}"],
        ['', ''],
        ['NET SALARY', f"${payroll.net_salary:,.2f}"]
    ]
    
    payroll_table = Table(payroll_data, colWidths=[200, 150])
    payroll_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 6), (-1, 6), 'Helvetica-Bold'),
        ('FONTNAME', (0, 13), (-1, 13), 'Helvetica-Bold'),
        ('FONTNAME', (0, 15), (-1, 15), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 15), (-1, 15), 14),
    ]))
    
    story.append(payroll_table)
    
    doc.build(story)
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=payslip_{payroll.employee.employee_id}_{payroll.pay_period_start}.pdf'
    
    return response

@payroll_bp.route('/bulk_process', methods=['POST'])
@login_required
def bulk_process():
    if current_user.role not in ['admin', 'hr']:
        return jsonify({'success': False, 'message': 'Permission denied'})
    
    data = request.get_json()
    employee_ids = data.get('employee_ids', [])
    pay_period_start = datetime.strptime(data.get('pay_period_start'), '%Y-%m-%d').date()
    pay_period_end = datetime.strptime(data.get('pay_period_end'), '%Y-%m-%d').date()
    
    processed_count = 0
    
    for emp_id in employee_ids:
        employee = Employee.query.get(emp_id)
        if not employee:
            continue
        
        # Check if payroll already exists for this period
        existing_payroll = Payroll.query.filter(
            Payroll.employee_id == emp_id,
            Payroll.pay_period_start == pay_period_start,
            Payroll.pay_period_end == pay_period_end
        ).first()
        
        if existing_payroll:
            continue
        
        # Calculate payroll (simplified calculation)
        basic_salary = employee.salary
        allowances = basic_salary * Decimal('0.1')  # 10% allowance
        gross_salary = basic_salary + allowances
        tax_deduction = gross_salary * Decimal('0.15')  # 15% tax
        pension_deduction = gross_salary * Decimal('0.05')  # 5% pension
        total_deductions = tax_deduction + pension_deduction
        net_salary = gross_salary - total_deductions
        
        payroll = Payroll(
            employee_id=emp_id,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end,
            basic_salary=basic_salary,
            allowances=allowances,
            gross_salary=gross_salary,
            tax_deduction=tax_deduction,
            pension_deduction=pension_deduction,
            total_deductions=total_deductions,
            net_salary=net_salary,
            processed_by=current_user.id,
            processed_at=datetime.utcnow(),
            status='processed'
        )
        
        db.session.add(payroll)
        processed_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'Successfully processed {processed_count} payrolls'
    })

@payroll_bp.route('/export')
@login_required
def export():
    if current_user.role not in ['admin', 'hr']:
        flash('You do not have permission to export payroll data', 'error')
        return redirect(url_for('payroll.index'))
    
    payrolls = Payroll.query.join(Employee).all()
    
    # Create CSV data
    csv_data = "Employee ID,Name,Pay Period,Basic Salary,Allowances,Gross Salary,Total Deductions,Net Salary,Status\n"
    for payroll in payrolls:
        csv_data += f"{payroll.employee.employee_id},{payroll.employee.full_name},{payroll.pay_period_start} to {payroll.pay_period_end},{payroll.basic_salary},{payroll.allowances},{payroll.gross_salary},{payroll.total_deductions},{payroll.net_salary},{payroll.status}\n"
    
    return csv_data, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=payroll_export.csv'
    }
