#!/usr/bin/env python3
"""
Simple script to create sample departments and schemes
This script will be run when the Flask app starts to ensure data exists
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from bson import ObjectId

def create_sample_data(mongo):
    """Create sample departments and schemes if they don't exist"""
    try:
        print("🔍 Checking for sample data...")
        
        # Check if departments exist
        dept_count = mongo.db.departments.count_documents({})
        print(f"📊 Found {dept_count} departments")
        
        if dept_count == 0:
            print("🏢 Creating sample departments...")
            
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
            
            result = mongo.db.departments.insert_many(sample_departments)
            print(f"✅ Created {len(result.inserted_ids)} departments")
            
            # Get the created departments for scheme creation
            departments = list(mongo.db.departments.find({}))
        else:
            departments = list(mongo.db.departments.find({}))
        
        # Check if schemes exist
        scheme_count = mongo.db.schemes.count_documents({})
        print(f"📊 Found {scheme_count} schemes")
        
        if scheme_count == 0:
            print("📋 Creating sample schemes...")
            
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
                result = mongo.db.schemes.insert_many(sample_schemes)
                print(f"✅ Created {len(result.inserted_ids)} schemes")
        
        # Final count
        final_dept_count = mongo.db.departments.count_documents({})
        final_scheme_count = mongo.db.schemes.count_documents({})
        
        print(f"📊 Final Status: {final_dept_count} departments, {final_scheme_count} schemes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        return False

if __name__ == "__main__":
    print("This script should be imported and called with a mongo instance")
