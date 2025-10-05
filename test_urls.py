#!/usr/bin/env python3
"""Test URL generation for QR attendance routes"""

from app import create_app
from flask import url_for

def test_urls():
    app = create_app()
    
    # Configure app for URL generation
    app.config['SERVER_NAME'] = 'localhost:5000'
    app.config['APPLICATION_ROOT'] = '/'
    app.config['PREFERRED_URL_SCHEME'] = 'http'
    
    with app.app_context():
        try:
            print("Testing URL generation...")
            print("qr_attendance.index:", url_for('qr_attendance.index'))
            print("qr_attendance.manage_locations:", url_for('qr_attendance.manage_locations'))
            print("✅ All URLs generated successfully")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_urls()
