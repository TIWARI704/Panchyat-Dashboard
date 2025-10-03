#!/usr/bin/env python3
"""
Script to initialize sample departments and schemes for testing
Run this script to populate the database with sample data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, mongo
from models.department import Department
from models.scheme import Scheme

def initialize_sample_data():
    """Initialize sample departments and schemes"""
    
    with app.app_context():
        print("Initializing sample departments and schemes...")
        
        # Sample departments
        departments_data = [
            {
                'name': 'Education',
                'description': 'Department responsible for educational schemes and programs'
            },
            {
                'name': 'Women & Child Development',
                'description': 'Department for women empowerment and child welfare schemes'
            },
            {
                'name': 'Agriculture',
                'description': 'Department for agricultural development and farmer welfare'
            },
            {
                'name': 'Forest & Environment',
                'description': 'Department for forest conservation and environmental protection'
            },
            {
                'name': 'Health',
                'description': 'Department for health and medical welfare schemes'
            }
        ]
        
        # Create departments
        created_departments = {}
        for dept_data in departments_data:
            result = Department.create_department(mongo, dept_data)
            if result['success']:
                dept_id = result['department_id']
                created_departments[dept_data['name']] = dept_id
                print(f"✓ Created department: {dept_data['name']}")
            else:
                print(f"✗ Failed to create department {dept_data['name']}: {result['message']}")
        
        # Sample schemes
        schemes_data = [
            {
                'name': 'Mukhyamantri Nari Yojna',
                'department_name': 'Women & Child Development',
                'description': 'Scheme for women empowerment and financial assistance',
                'attributes': [
                    {
                        'name': 'beneficiary_age',
                        'label': 'Beneficiary Age',
                        'type': 'int'
                    },
                    {
                        'name': 'family_income',
                        'label': 'Family Annual Income',
                        'type': 'float'
                    },
                    {
                        'name': 'education_level',
                        'label': 'Education Level',
                        'type': 'enum',
                        'options': ['Primary', 'Secondary', 'Higher Secondary', 'Graduate', 'Post Graduate']
                    },
                    {
                        'name': 'marital_status',
                        'label': 'Marital Status',
                        'type': 'enum',
                        'options': ['Single', 'Married', 'Widowed', 'Divorced']
                    }
                ]
            },
            {
                'name': 'Vann Vikas Yojna',
                'department_name': 'Forest & Environment',
                'description': 'Scheme for forest development and conservation',
                'attributes': [
                    {
                        'name': 'land_area',
                        'label': 'Land Area (in acres)',
                        'type': 'float'
                    },
                    {
                        'name': 'tree_species',
                        'label': 'Tree Species',
                        'type': 'string'
                    },
                    {
                        'name': 'planting_date',
                        'label': 'Planting Date',
                        'type': 'date'
                    },
                    {
                        'name': 'survival_rate',
                        'label': 'Survival Rate (%)',
                        'type': 'float'
                    }
                ]
            },
            {
                'name': 'Kisan Credit Card',
                'department_name': 'Agriculture',
                'description': 'Credit facility for farmers',
                'attributes': [
                    {
                        'name': 'crop_type',
                        'label': 'Crop Type',
                        'type': 'enum',
                        'options': ['Wheat', 'Rice', 'Cotton', 'Sugarcane', 'Vegetables', 'Fruits']
                    },
                    {
                        'name': 'land_holding',
                        'label': 'Land Holding (in acres)',
                        'type': 'float'
                    },
                    {
                        'name': 'credit_limit',
                        'label': 'Credit Limit (₹)',
                        'type': 'float'
                    }
                ]
            },
            {
                'name': 'Mid Day Meal',
                'department_name': 'Education',
                'description': 'Nutritional support for school children',
                'attributes': [
                    {
                        'name': 'school_name',
                        'label': 'School Name',
                        'type': 'string'
                    },
                    {
                        'name': 'student_count',
                        'label': 'Number of Students',
                        'type': 'int'
                    },
                    {
                        'name': 'meal_type',
                        'label': 'Meal Type',
                        'type': 'enum',
                        'options': ['Breakfast', 'Lunch', 'Both']
                    }
                ]
            },
            {
                'name': 'Ayushman Bharat',
                'department_name': 'Health',
                'description': 'Health insurance scheme for poor families',
                'attributes': [
                    {
                        'name': 'family_size',
                        'label': 'Family Size',
                        'type': 'int'
                    },
                    {
                        'name': 'annual_income',
                        'label': 'Annual Family Income (₹)',
                        'type': 'float'
                    },
                    {
                        'name': 'insurance_coverage',
                        'label': 'Insurance Coverage (₹)',
                        'type': 'float'
                    }
                ]
            }
        ]
        
        # Create schemes
        for scheme_data in schemes_data:
            dept_name = scheme_data['department_name']
            if dept_name in created_departments:
                scheme_data['department_id'] = created_departments[dept_name]
                del scheme_data['department_name']  # Remove this key as it's not needed for creation
                
                result = Scheme.create_scheme(mongo, scheme_data)
                if result['success']:
                    print(f"✓ Created scheme: {scheme_data['name']} in {dept_name}")
                else:
                    print(f"✗ Failed to create scheme {scheme_data['name']}: {result['message']}")
            else:
                print(f"✗ Department {dept_name} not found for scheme {scheme_data['name']}")
        
        print("\nSample data initialization completed!")
        print("You can now:")
        print("1. Login as superadmin")
        print("2. Go to 'Departments & Schemes' in the sidebar")
        print("3. View and manage the created departments and schemes")
        print("4. Assign department/scheme access to users in 'Manage Users'")

if __name__ == '__main__':
    initialize_sample_data()
