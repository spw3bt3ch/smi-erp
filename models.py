from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Create a separate db instance for models
db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # admin, hr, employee
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationship
    employee = db.relationship('Employee', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Employee(db.Model):
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    job_title = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    hire_date = db.Column(db.Date, nullable=False)
    salary = db.Column(db.Numeric(10, 2), nullable=False)
    tax_id = db.Column(db.String(20))
    bank_name = db.Column(db.String(100))
    bank_account = db.Column(db.String(50))
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    payrolls = db.relationship('Payroll', backref='employee', lazy='dynamic')
    attendances = db.relationship('Attendance', backref='employee', lazy='dynamic')
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<Employee {self.full_name}>'

class Payroll(db.Model):
    __tablename__ = 'payrolls'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    pay_period_start = db.Column(db.Date, nullable=False)
    pay_period_end = db.Column(db.Date, nullable=False)
    basic_salary = db.Column(db.Numeric(10, 2), nullable=False)
    allowances = db.Column(db.Numeric(10, 2), default=0)
    overtime_pay = db.Column(db.Numeric(10, 2), default=0)
    gross_salary = db.Column(db.Numeric(10, 2), nullable=False)
    tax_deduction = db.Column(db.Numeric(10, 2), default=0)
    pension_deduction = db.Column(db.Numeric(10, 2), default=0)
    loan_deduction = db.Column(db.Numeric(10, 2), default=0)
    other_deductions = db.Column(db.Numeric(10, 2), default=0)
    total_deductions = db.Column(db.Numeric(10, 2), default=0)
    net_salary = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, processed, paid
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    processed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    processor = db.relationship('User', backref='processed_payrolls')
    
    def __repr__(self):
        return f'<Payroll {self.employee.full_name} - {self.pay_period_start}>'

class Attendance(db.Model):
    __tablename__ = 'attendances'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.Time)
    check_out = db.Column(db.Time)
    hours_worked = db.Column(db.Numeric(4, 2), default=0)
    overtime_hours = db.Column(db.Numeric(4, 2), default=0)
    status = db.Column(db.String(20), default='present')  # present, absent, late, half_day
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Attendance {self.employee.full_name} - {self.date}>'

class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    manager = db.relationship('Employee', backref='managed_department')
    
    def __repr__(self):
        return f'<Department {self.name}>'

class OfficeHours(db.Model):
    __tablename__ = 'office_hours'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Standard Hours", "Flexible Hours"
    description = db.Column(db.Text)
    
    # Official times
    official_clock_in = db.Column(db.Time, nullable=False)  # e.g., 09:00
    official_clock_out = db.Column(db.Time, nullable=False)  # e.g., 17:00
    
    # Grace periods (in minutes)
    clock_in_grace_period = db.Column(db.Integer, default=15)  # 15 minutes late is acceptable
    clock_out_grace_period = db.Column(db.Integer, default=15)  # 15 minutes early is acceptable
    
    # Break times
    break_duration = db.Column(db.Integer, default=60)  # 1 hour break
    break_start_time = db.Column(db.Time)  # e.g., 12:00 for lunch break
    
    # Working days (comma-separated: 1=Monday, 2=Tuesday, etc.)
    working_days = db.Column(db.String(20), default='1,2,3,4,5')  # Monday to Friday
    
    # Policy settings
    allow_early_clock_in = db.Column(db.Boolean, default=True)  # Can clock in before official time
    allow_late_clock_out = db.Column(db.Boolean, default=True)  # Can clock out after official time
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)  # Only one can be default
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<OfficeHours {self.name}: {self.official_clock_in} - {self.official_clock_out}>'
    
    def get_working_days_list(self):
        """Convert working_days string to list of integers"""
        if not self.working_days:
            return []
        return [int(day.strip()) for day in self.working_days.split(',') if day.strip()]
    
    def set_working_days_list(self, days_list):
        """Set working_days from list of integers"""
        self.working_days = ','.join(map(str, days_list))
    
    def is_working_day(self, weekday):
        """Check if given weekday (1=Monday, 7=Sunday) is a working day"""
        return weekday in self.get_working_days_list()

class OfficeLocation(db.Model):
    __tablename__ = 'office_locations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, nullable=True)  # Made optional
    longitude = db.Column(db.Float, nullable=True)  # Made optional
    radius_meters = db.Column(db.Integer, nullable=False, default=100)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_brief_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'address': self.address,
            'coordinates': {'lat': self.latitude, 'lng': self.longitude} if self.latitude and self.longitude else None,
            'radius': self.radius_meters,
            'active': self.active
        }

class AttendancePolicy(db.Model):
    __tablename__ = 'attendance_policies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Late arrival penalties
    late_penalty_type = db.Column(db.String(20), default='warning')  # warning, deduction, none
    late_penalty_amount = db.Column(db.Float, default=0.0)  # Amount to deduct for being late
    late_penalty_threshold = db.Column(db.Integer, default=30)  # Minutes late before penalty applies
    
    # Early departure penalties
    early_departure_penalty_type = db.Column(db.String(20), default='warning')
    early_departure_penalty_amount = db.Column(db.Float, default=0.0)
    early_departure_threshold = db.Column(db.Integer, default=30)  # Minutes early before penalty
    
    # Absence penalties
    absence_penalty_type = db.Column(db.String(20), default='deduction')
    absence_penalty_amount = db.Column(db.Float, default=500.0)  # Amount to deduct for absence
    
    # Overtime rewards
    overtime_rate = db.Column(db.Float, default=1.5)  # 1.5x normal rate for overtime
    overtime_threshold = db.Column(db.Integer, default=480)  # Minutes (8 hours) before overtime
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<AttendancePolicy {self.name}>'
