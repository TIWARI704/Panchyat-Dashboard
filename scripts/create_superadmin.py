import sys
import os
import getpass
from werkzeug.security import generate_password_hash
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_pymongo import PyMongo
from config import config
from datetime import datetime

# Initialize Flask app and MongoDB
app = Flask(__name__)
app.config["MONGO_URI"] = config.DATABASE_URL
app.config["SECRET_KEY"] = config.SECRET_KEY_BASE
mongo = PyMongo(app)

def create_superadmin():
    """Interactive script to create a superadmin user"""
    print("🏛️  Panchayat Dashboard - Superadmin Creation")
    print("=" * 50)
    
    # Get user input
    username = input("Enter superadmin username: ").strip()
    if not username:
        print("❌ Username cannot be empty!")
        return
    
    password = getpass.getpass("Enter password (hidden): ")
    if len(password) < 8:
        print("❌ Password must be at least 8 characters long!")
        return
    
    confirm_password = getpass.getpass("Confirm password (hidden): ")
    if password != confirm_password:
        print("❌ Passwords do not match!")
        return
    
    with app.app_context():
        # Check if user already exists
        existing_user = mongo.db.users.find_one({'username': username})
        if existing_user:
            print(f"❌ Username '{username}' already exists!")
            return
        
        # Create superadmin user
        user_data = {
            'username': username,
            'password': generate_password_hash(password),
            'role': 'superadmin',
            'is_admin': True,
            'is_superadmin': True,
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'last_login': None
        }
        
        try:
            result = mongo.db.users.insert_one(user_data)
            if result.inserted_id:
                print("✅ Superadmin account created successfully!")
                print(f"   Username: {username}")
                print(f"   User ID: {result.inserted_id}")
                print("\n🔐 Please keep these credentials secure!")
            else:
                print("❌ Failed to create superadmin account!")
        except Exception as e:
            print(f"❌ Error creating superadmin: {e}")

if __name__ == "__main__":
    create_superadmin()