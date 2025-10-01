#!/usr/bin/env python3
"""
Script to check if departments and schemes exist, and initialize them if they don't
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import json

# MongoDB connection - use same config as app
from config import config
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use the same DATABASE_URL as the app
DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017/panchayat_management")

def check_and_init_data():
    """Check if departments and schemes exist, initialize if they don't"""
    try:
        # Connect to MongoDB with timeout
        print(f"🔌 Connecting to MongoDB: {DATABASE_URL}")
        client = MongoClient(DATABASE_URL, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful")
        
        # Extract database name from URL
        db_name = DATABASE_URL.split('/')[-1] if '/' in DATABASE_URL else 'panchayat_management'
        db = client[db_name]
        
        print("🔍 Checking database for departments and schemes...")
        
        # Check if departments exist
        dept_count = db.departments.count_documents({})
        print(f"📊 Found {dept_count} departments in database")
        
        # Check if schemes exist
        scheme_count = db.schemes.count_documents({})
        print(f"📊 Found {scheme_count} schemes in database")
        
        # If no departments exist, create sample ones
        if dept_count == 0:
            print("🏢 No departments found. Creating sample departments...")
            
            sample_departments = [
                {
                    "name": "Education",
                    "description": "Education department for school and literacy programs",
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                },
                {
                    "name": "Agriculture",
                    "description": "Agriculture department for farming and rural development",
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                },
                {
                    "name": "Women & Child Development",
                    "description": "Women and child development programs",
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                },
                {
                    "name": "Forest & Environment",
                    "description": "Forest conservation and environment protection",
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                },
                {
                    "name": "Health & Sanitation",
                    "description": "Health services and sanitation programs",
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            ]
            
            result = db.departments.insert_many(sample_departments)
            print(f"✅ Created {len(result.inserted_ids)} departments")
            
            # Get the created departments for scheme creation
            departments = list(db.departments.find({}))
        else:
            departments = list(db.departments.find({}))
        
        # If no schemes exist, create sample ones
        if scheme_count == 0:
            print("📋 No schemes found. Creating sample schemes...")
            
            # Create schemes for each department
            sample_schemes = []
            
            for dept in departments:
                dept_name = dept['name']
                dept_id = dept['_id']
                
                if dept_name == "Education":
                    schemes = [
                        {
                            "name": "Mid Day Meal Scheme",
                            "description": "Free meal program for school children",
                            "department_id": dept_id,
                            "attributes": [
                                {"name": "student_count", "label": "Number of Students", "type": "int", "required": True},
                                {"name": "meal_type", "label": "Type of Meal", "type": "enum", "options": ["Vegetarian", "Non-Vegetarian"], "required": True},
                                {"name": "school_type", "label": "School Type", "type": "enum", "options": ["Primary", "Secondary", "Higher Secondary"], "required": True}
                            ],
                            "is_active": True,
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        },
                        {
                            "name": "Digital Education Initiative",
                            "description": "Digital learning tools and infrastructure",
                            "department_id": dept_id,
                            "attributes": [
                                {"name": "device_count", "label": "Number of Devices", "type": "int", "required": True},
                                {"name": "internet_available", "label": "Internet Available", "type": "boolean", "required": True},
                                {"name": "teacher_trained", "label": "Teachers Trained", "type": "int", "required": False}
                            ],
                            "is_active": True,
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    ]
                elif dept_name == "Agriculture":
                    schemes = [
                        {
                            "name": "PM Kisan Samman Nidhi",
                            "description": "Direct income support for farmers",
                            "department_id": dept_id,
                            "attributes": [
                                {"name": "land_area", "label": "Land Area (acres)", "type": "float", "required": True},
                                {"name": "crop_type", "label": "Primary Crop", "type": "enum", "options": ["Rice", "Wheat", "Cotton", "Sugarcane", "Vegetables"], "required": True},
                                {"name": "irrigation_type", "label": "Irrigation Type", "type": "enum", "options": ["Tube Well", "Canal", "Rain-fed", "Drip"], "required": True}
                            ],
                            "is_active": True,
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    ]
                elif dept_name == "Women & Child Development":
                    schemes = [
                        {
                            "name": "Mukhyamantri Nari Yojna",
                            "description": "Women empowerment and development scheme",
                            "department_id": dept_id,
                            "attributes": [
                                {"name": "age", "label": "Age", "type": "int", "required": True},
                                {"name": "education_level", "label": "Education Level", "type": "enum", "options": ["Illiterate", "Primary", "Secondary", "Graduate", "Post Graduate"], "required": True},
                                {"name": "family_income", "label": "Family Income (₹)", "type": "float", "required": True},
                                {"name": "skill_training", "label": "Skill Training Required", "type": "boolean", "required": False}
                            ],
                            "is_active": True,
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    ]
                elif dept_name == "Forest & Environment":
                    schemes = [
                        {
                            "name": "Van Vikas Yojna",
                            "description": "Forest development and conservation",
                            "department_id": dept_id,
                            "attributes": [
                                {"name": "tree_species", "label": "Tree Species", "type": "string", "required": True},
                                {"name": "area_planted", "label": "Area Planted (hectares)", "type": "float", "required": True},
                                {"name": "survival_rate", "label": "Survival Rate (%)", "type": "float", "required": False}
                            ],
                            "is_active": True,
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    ]
                elif dept_name == "Health & Sanitation":
                    schemes = [
                        {
                            "name": "Swachh Bharat Mission",
                            "description": "Clean India mission for sanitation",
                            "department_id": dept_id,
                            "attributes": [
                                {"name": "toilet_constructed", "label": "Toilets Constructed", "type": "int", "required": True},
                                {"name": "household_count", "label": "Number of Households", "type": "int", "required": True},
                                {"name": "open_defecation_free", "label": "Open Defecation Free", "type": "boolean", "required": True}
                            ],
                            "is_active": True,
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    ]
                else:
                    schemes = []
                
                sample_schemes.extend(schemes)
            
            if sample_schemes:
                result = db.schemes.insert_many(sample_schemes)
                print(f"✅ Created {len(result.inserted_ids)} schemes")
        
        # Final count
        final_dept_count = db.departments.count_documents({})
        final_scheme_count = db.schemes.count_documents({})
        
        print(f"\n📊 Final Status:")
        print(f"   Departments: {final_dept_count}")
        print(f"   Schemes: {final_scheme_count}")
        
        # Check if we have any users
        user_count = db.users.count_documents({})
        print(f"   Users: {user_count}")
        
        if user_count == 0:
            print("\n⚠️  No users found. You may need to create a superadmin user.")
            print("   Run: python scripts/create_superadmin.py")
        
        client.close()
        print("\n✅ Database check and initialization completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure MongoDB is running: brew services start mongodb-community")
        print("   2. Check if MongoDB is installed: brew install mongodb-community")
        print("   3. Verify the connection string in your .env file")
        print("   4. Try starting MongoDB manually: mongod --config /usr/local/etc/mongod.conf")
        return False
    
    return True

if __name__ == "__main__":
    check_and_init_data()
