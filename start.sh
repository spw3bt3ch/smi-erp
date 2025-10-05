#!/bin/bash
# Start script for Render deployment

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Database initialized successfully')
"

# Start the application
gunicorn app:app --bind 0.0.0.0:$PORT
