#!/usr/bin/env python3
"""
Simple script to run the Django development server.
Usage: python run.py
"""

import os
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'receipt_processor.settings')

# Add project to path
project_path = os.path.dirname(os.path.abspath(__file__))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

def setup_django():
    """Initialize Django."""
    import django
    django.setup()

def create_admin_user():
    """Create default admin user if not exists."""
    setup_django()
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if not User.objects.filter(username='admin').exists():
        print("=" * 50)
        print("Creating default admin user...")
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("Admin user created!")
        print("  Username: admin")
        print("  Password: admin123")
        print("=" * 50)

def run_server():
    """Run the Django development server."""
    from django.core.management import execute_from_command_line
    
    print("\n" + "=" * 50)
    print("Smart Receipt Processor")
    print("=" * 50)
    print("Starting server at: http://127.0.0.1:8000")
    print("Admin panel at: http://127.0.0.1:8000/admin/")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 50 + "\n")
    
    execute_from_command_line(['manage.py', 'runserver', '8000'])

if __name__ == '__main__':
    try:
        create_admin_user()
        run_server()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        sys.exit(0)
