# ERP Payroll System

A comprehensive Flask-based ERP Payroll System with modern UI, role-based authentication, and full payroll management capabilities.

## Features

### 🔐 Authentication & Authorization
- User registration and login system
- Role-based access control (Admin, HR, Employee)
- Secure password hashing
- Session management

### 👥 Employee Management
- Add, edit, and manage employee records
- Employee profiles with personal and job information
- Department and salary management
- Employee search and filtering
- CSV export functionality

### 💰 Payroll Processing
- Process individual and bulk payrolls
- Calculate gross salary, allowances, and deductions
- Generate professional payslips
- PDF export for payslips
- Payroll history tracking
- Status management (pending, processed, paid)

### 📊 Dashboard & Reporting
- Interactive dashboard with key metrics
- Visual charts and statistics
- Department-wise analytics
- Monthly payroll trends
- Comprehensive reporting system
- Date-range filtering

### ⏰ Attendance Management
- Record employee attendance
- Track check-in/check-out times
- Calculate hours worked and overtime
- Attendance status tracking
- Daily attendance reports

### 🎨 Modern UI/UX
- Responsive design with Tailwind CSS
- Clean dashboard layout
- Interactive components
- Mobile-friendly interface
- Professional payslip design

### 🔌 API Endpoints
- RESTful API for all major functions
- JSON responses
- Role-based API access
- Employee and payroll data endpoints

## Technology Stack

- **Backend**: Flask (Python 3.10+)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Jinja2 templates with Tailwind CSS
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF with CSRF protection
- **PDF Generation**: ReportLab
- **Charts**: Chart.js
- **Database Migrations**: Flask-Migrate

## Installation

### Prerequisites
- Python 3.10 or higher
- pip (Python package installer)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd erp-payroll-system
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize the database**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   Open your browser and navigate to `http://localhost:5000`

## Project Structure

```
erp-payroll-system/
├── app.py                 # Main application file
├── models.py              # Database models
├── forms.py               # WTForms definitions
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── README.md             # This file
├── blueprints/           # Flask blueprints
│   ├── __init__.py
│   ├── auth.py           # Authentication routes
│   ├── employees.py      # Employee management
│   ├── payroll.py        # Payroll processing
│   ├── admin.py          # Admin dashboard
│   └── api.py            # API endpoints
├── templates/            # Jinja2 templates
│   ├── base.html         # Base template
│   ├── auth/             # Authentication templates
│   ├── employees/        # Employee templates
│   ├── payroll/          # Payroll templates
│   └── admin/            # Admin templates
└── static/               # Static files (CSS, JS, images)
```

## Usage

### First Time Setup

1. **Register an Admin Account**
   - Navigate to the registration page
   - Select "Admin" as the role
   - Complete the registration form

2. **Login and Access Dashboard**
   - Login with your admin credentials
   - Access the dashboard to view system overview

### Managing Employees

1. **Add Employees**
   - Navigate to Employees section
   - Click "Add Employee"
   - Fill in employee details
   - Save the employee record

2. **Edit Employee Information**
   - Go to employee list
   - Click "Edit" next to any employee
   - Update information as needed

### Processing Payroll

1. **Individual Payroll**
   - Go to Payroll section
   - Click "Process Payroll"
   - Select employee and pay period
   - Enter salary details and deductions
   - Process the payroll

2. **Bulk Payroll Processing**
   - Use the bulk processing feature
   - Select multiple employees
   - Set pay period dates
   - Process all payrolls at once

### Viewing Reports

1. **Dashboard Reports**
   - View key metrics on the dashboard
   - Analyze department statistics
   - Check monthly trends

2. **Detailed Reports**
   - Go to Reports section
   - Filter by date range and department
   - Export data as needed

## API Usage

The system provides RESTful API endpoints for integration:

### Authentication Required
All API endpoints require authentication. Include the session cookie or implement proper authentication.

### Key Endpoints

- `GET /api/employees` - Get all employees
- `GET /api/employees/{id}` - Get specific employee
- `GET /api/payrolls` - Get payroll records
- `POST /api/payrolls` - Create new payroll
- `GET /api/stats` - Get dashboard statistics

### Example API Call

```bash
curl -X GET http://localhost:5000/api/employees \
  -H "Content-Type: application/json"
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///payroll_system.db
FLASK_ENV=development
```

### Database Configuration

The system uses SQLite by default. To use PostgreSQL or MySQL:

1. Install the appropriate database driver
2. Update the `DATABASE_URL` in your `.env` file
3. Run database migrations

## Security Features

- CSRF protection on all forms
- Secure password hashing
- Role-based access control
- Input validation and sanitization
- SQL injection prevention through ORM

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the code comments

## Roadmap

- [ ] Email notifications for payroll processing
- [ ] Advanced reporting with more chart types
- [ ] Mobile app integration
- [ ] Multi-currency support
- [ ] Advanced attendance tracking with GPS
- [ ] Integration with external HR systems
- [ ] Advanced user management features
- [ ] Audit logging
- [ ] Backup and restore functionality

## Changelog

### Version 1.0.0
- Initial release
- Basic payroll management
- Employee management
- Authentication system
- Dashboard and reporting
- PDF payslip generation
- API endpoints
