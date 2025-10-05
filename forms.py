from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DateField, DecimalField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Optional
from datetime import date

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[Optional(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[Optional(), EqualTo('password')])
    role = SelectField('Role', choices=[('admin', 'Admin'), ('hr', 'HR'), ('employee', 'Employee')], validators=[DataRequired()])
    
    # Employee fields
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    job_title = StringField('Job Title', validators=[DataRequired(), Length(min=2, max=100)])
    department = StringField('Department', validators=[DataRequired(), Length(min=2, max=100)])
    hire_date = DateField('Hire Date', validators=[DataRequired()], default=date.today)
    salary = DecimalField('Salary', validators=[DataRequired(), NumberRange(min=0)])
    
    submit = SubmitField('Register')
    
    def validate(self, extra_validators=None):
        # Custom validation based on role
        if not super().validate(extra_validators):
            return False
        
        # For admin and HR, username and password are required
        if self.role.data in ['admin', 'hr']:
            if not self.username.data:
                self.username.errors.append('Username is required for Admin and HR users')
                return False
            if not self.password.data:
                self.password.errors.append('Password is required for Admin and HR users')
                return False
            if not self.password2.data:
                self.password2.errors.append('Please confirm the password')
                return False
        
        return True

class EmployeeForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    job_title = StringField('Job Title', validators=[DataRequired(), Length(min=2, max=100)])
    department = StringField('Department', validators=[DataRequired(), Length(min=2, max=100)])
    hire_date = DateField('Hire Date', validators=[DataRequired()], default=date.today)
    salary = DecimalField('Salary', validators=[DataRequired(), NumberRange(min=0)])
    tax_id = StringField('Tax ID', validators=[Optional(), Length(max=20)])
    bank_name = StringField('Bank Name', validators=[Optional(), Length(max=100)])
    bank_account = StringField('Bank Account', validators=[Optional(), Length(max=50)])
    address = TextAreaField('Address', validators=[Optional()])
    submit = SubmitField('Save Employee')

class PayrollForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    pay_period_start = DateField('Pay Period Start', validators=[DataRequired()])
    pay_period_end = DateField('Pay Period End', validators=[DataRequired()])
    basic_salary = DecimalField('Basic Salary', validators=[DataRequired(), NumberRange(min=0)])
    allowances = DecimalField('Allowances', validators=[Optional(), NumberRange(min=0)], default=0)
    overtime_pay = DecimalField('Overtime Pay', validators=[Optional(), NumberRange(min=0)], default=0)
    tax_deduction = DecimalField('Tax Deduction', validators=[Optional(), NumberRange(min=0)], default=0)
    pension_deduction = DecimalField('Pension Deduction', validators=[Optional(), NumberRange(min=0)], default=0)
    loan_deduction = DecimalField('Loan Deduction', validators=[Optional(), NumberRange(min=0)], default=0)
    other_deductions = DecimalField('Other Deductions', validators=[Optional(), NumberRange(min=0)], default=0)
    submit = SubmitField('Process Payroll')

class AttendanceForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()], default=date.today)
    check_in = StringField('Check In Time (HH:MM)', validators=[Optional()])
    check_out = StringField('Check Out Time (HH:MM)', validators=[Optional()])
    status = SelectField('Status', choices=[('present', 'Present'), ('absent', 'Absent'), ('late', 'Late'), ('half_day', 'Half Day')], validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Record Attendance')

class ContactForm(FlaskForm):
    firstName = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    lastName = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    company = StringField('Company', validators=[Optional(), Length(max=100)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    subject = SelectField('Subject', choices=[
        ('', 'Select a subject'),
        ('demo', 'Request a Demo'),
        ('pricing', 'Pricing Information'),
        ('support', 'Technical Support'),
        ('partnership', 'Partnership Inquiry'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10, max=1000)])
    submit = SubmitField('Send Message')