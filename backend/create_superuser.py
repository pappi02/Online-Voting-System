#!/usr/bin/env python
"""
Script to create a superuser for the application
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ivs_backend.settings')
django.setup()

from accounts.models import User

# Create superuser if it doesn't exist
email = 'admin@ivotesystems.com'
if not User.objects.filter(email=email).exists():
    user = User.objects.create_superuser(
        email=email,
        password='Admin@12345',
        first_name='Admin',
        last_name='User'
    )
    print(f"✓ Superuser created successfully: {email}")
    print(f"  Password: Admin@12345")
else:
    print(f"✗ Superuser already exists: {email}")
