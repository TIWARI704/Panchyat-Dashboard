#!/usr/bin/env python3
"""
Manual script to create a default user
"""

import sys
import os
sys.path.append('.')

from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_user():
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client['panchayat_management']
        
        # Check if user exists
        existing_user = db.users.find_one({'username': 'superadmin'})
        if existing_user:
            print("✅ User 'superadmin' already exists")
            return True
        
        # Create user data
        user_data = {
            'username': 'superadmin',
            'password': generate_password_hash('admin123'),
            'email': 'admin@panchayat.gov.in',
            'full_name': 'System Administrator',
            'role': 'superadmin',
            'is_active': True,
            'is_admin': True,
            'is_superadmin': True,
            'department_access': ['all'],
            'scheme_access': ['all'],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'last_login': None
        }
        
        # Insert user
        result = db.users.insert_one(user_data)
        
        if result.inserted_id:
            print("✅ Default superadmin user created successfully!")
            print("📋 Login Credentials:")
            print("   Username: superadmin")
            print("   Password: admin123")
            return True
        else:
            print("❌ Failed to create user")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    create_user()
