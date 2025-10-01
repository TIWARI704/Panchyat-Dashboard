#!/usr/bin/env python3
"""
Script to create a default superadmin user for the Panchayat Dashboard
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from bson import ObjectId
from models.login import User

def create_default_user(mongo):
    """Create a default superadmin user if none exists"""
    try:
        print("🔍 Checking for existing users...")
        
        # Check if any users exist
        user_count = mongo.db.users.count_documents({})
        print(f"📊 Found {user_count} users")
        
        if user_count == 0:
            print("👤 Creating default superadmin user...")
            
            # Create default superadmin user
            user_data = {
                'username': 'superadmin',
                'password': 'admin123',  # Default password - should be changed
                'email': 'admin@panchayat.gov.in',
                'full_name': 'System Administrator',
                'role': 'superadmin',
                'is_active': True,
                'is_admin': True,
                'is_superadmin': True,
                'department_access': ['all'],  # Access to all departments
                'scheme_access': ['all'],      # Access to all schemes
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            result = User.create_user(mongo, user_data)
            
            if result['success']:
                print("✅ Default superadmin user created successfully!")
                print("📋 Login Credentials:")
                print("   Username: superadmin")
                print("   Password: admin123")
                print("⚠️  Please change the password after first login!")
                return True
            else:
                print(f"❌ Error creating user: {result['message']}")
                return False
        else:
            print("✅ Users already exist, skipping user creation")
            return True
            
    except Exception as e:
        print(f"❌ Error creating default user: {e}")
        return False

if __name__ == "__main__":
    print("This script should be imported and called with a mongo instance")
