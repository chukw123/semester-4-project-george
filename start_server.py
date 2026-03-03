#!/usr/bin/env python
"""
Simple script to start the Django development server.
Also creates a default admin user if none exists.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'receipt_processor.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from django.core.management import call_command

User = get_user_model()

# Create default admin user if none exists
if not User.objects.filter(username='admin').exists():
    print("Creating default admin user...")
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Admin user created!")
    print("Username: admin")
    print("Password: admin123")

print("\nStarting Smart Receipt Processor server...")
print("Access the app at: http://127.0.0.1:8000")
print("Admin panel at: http://127.0.0.1:8000/admin/")
print("\nPress Ctrl+C to stop the server\n")

# Start the server
call_command('runserver', '0.0.0.0:8000')
