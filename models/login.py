"""
User Model

This module defines the User model for the Panchayat Management System.
It handles user authentication, role management, and access control.
"""

from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from bson.objectid import ObjectId

class User:
    """
    User model for managing user accounts and permissions.
    
    Supports role-based access control with department and scheme-level permissions.
    """
    def __init__(self, username, password, email=None, role='user', is_admin=False, is_superadmin=False, 
                 department_access=None, scheme_access=None):
        self.username = username
        self.password = generate_password_hash(password)
        self.email = email
        self.role = role
        self.is_admin = is_admin
        self.is_superadmin = is_superadmin
        self.department_access = department_access or []  # List of department IDs user can access
        self.scheme_access = scheme_access or []  # List of scheme IDs user can access
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.is_active = True
        self.last_login = None

    def to_dict(self):
        return {
            "username": self.username,
            "password": self.password,
            "email": self.email,
            "role": self.role,
            "is_admin": self.is_admin,
            "is_superadmin": self.is_superadmin,
            "department_access": self.department_access,
            "scheme_access": self.scheme_access,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
            "last_login": self.last_login
        }

    @staticmethod
    def create_user(mongo, user_data):
        """Create a new user in the database"""
        try:
            # Extract data from dictionary
            username = user_data.get('username')
            password = user_data.get('password')
            email = user_data.get('email')
            role = user_data.get('role', 'user')
            is_admin = user_data.get('is_admin', role in ['admin', 'superadmin'])
            is_superadmin = user_data.get('is_superadmin', role == 'superadmin')
            
            
            # Check if user already exists
            existing_user = mongo.db.users.find_one({'username': username})
            if existing_user:
                return {'success': False, 'message': 'Username already exists'}
            
            # Check if email already exists (if provided)
            if email:
                existing_email = mongo.db.users.find_one({'email': email})
                if existing_email:
                    return {'success': False, 'message': 'Email already registered'}
            
            # Create new user
            user = User(username, password, email, role, is_admin, is_superadmin,
                       user_data.get('department_access'), user_data.get('scheme_access'))
            user_dict = user.to_dict()
            
            # Add additional fields from user_data
            if user_data.get('full_name'):
                user_dict['full_name'] = user_data['full_name']
            if user_data.get('is_active') is not None:
                user_dict['is_active'] = user_data['is_active']
            
            result = mongo.db.users.insert_one(user_dict)
            
            if result.inserted_id:
                return {'success': True, 'message': 'User created successfully', 'user_id': str(result.inserted_id)}
            else:
                return {'success': False, 'message': 'Failed to create user'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error creating user: {str(e)}'}

    @staticmethod
    def authenticate(mongo, username, password):
        """Authenticate user login"""
        try:
            user = mongo.db.users.find_one({'username': username})
            if user and check_password_hash(user['password'], password):
                # Update last login
                mongo.db.users.update_one(
                    {'_id': user['_id']},
                    {'$set': {'last_login': datetime.utcnow()}}
                )
                return {'success': True, 'user': user}
            else:
                return {'success': False, 'message': 'Invalid username or password'}
        except Exception as e:
            return {'success': False, 'message': f'Authentication error: {str(e)}'}

    @staticmethod
    def get_user_by_id(mongo, user_id):
        """Get user by ID"""
        try:
            user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            return user
        except Exception as e:
            return None

    @staticmethod
    def update_user(mongo, user_id, update_data):
        """Update user information"""
        try:
            update_data['updated_at'] = datetime.utcnow()
            result = mongo.db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            return False

    @staticmethod
    def get_user_access_info(mongo, user_id):
        """Get user's department and scheme access information"""
        try:
            user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            if not user:
                return None
            
            # If user is superadmin, they have access to all departments and schemes
            if user.get('is_superadmin'):
                departments = list(mongo.db.departments.find({'is_active': True}).sort('name', 1))
                schemes = list(mongo.db.schemes.find({'is_active': True}).sort('name', 1))
                
                # Populate department names for schemes
                for scheme in schemes:
                    department = mongo.db.departments.find_one({'_id': scheme['department_id']})
                    scheme['department_name'] = department['name'] if department else 'Unknown'
                
                return {
                    'has_all_access': True,
                    'departments': departments,
                    'schemes': schemes,
                    'department_access': [str(dept['_id']) for dept in departments],
                    'scheme_access': [str(scheme['_id']) for scheme in schemes],
                    'department_ids': [str(dept['_id']) for dept in departments],
                    'scheme_ids': [str(scheme['_id']) for scheme in schemes]
                }
            
            # Get user's specific access
            department_access = user.get('department_access', [])
            scheme_access = user.get('scheme_access', [])
            
            # Get departments user has access to
            departments = []
            if department_access:
                departments = list(mongo.db.departments.find({
                    '_id': {'$in': [ObjectId(dep_id) for dep_id in department_access]},
                    'is_active': True
                }).sort('name', 1))
            
            # Get schemes user has access to
            schemes = []
            if scheme_access:
                schemes = list(mongo.db.schemes.find({
                    '_id': {'$in': [ObjectId(scheme_id) for scheme_id in scheme_access]},
                    'is_active': True
                }).sort('name', 1))
                
                # Populate department names for schemes
                for scheme in schemes:
                    department = mongo.db.departments.find_one({'_id': scheme['department_id']})
                    scheme['department_name'] = department['name'] if department else 'Unknown'
            
            return {
                'has_all_access': False,
                'departments': departments,
                'schemes': schemes,
                'department_access': department_access,
                'scheme_access': scheme_access,
                'department_ids': department_access,
                'scheme_ids': scheme_access
            }
            
        except Exception as e:
            return None

    @staticmethod
    def can_access_department(mongo, user_id, department_id):
        """Check if user can access a specific department"""
        try:
            user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            if not user:
                return False
            
            # Superadmin has access to all departments
            if user.get('is_superadmin'):
                return True
            
            # Check if department is in user's access list
            department_access = user.get('department_access', [])
            return str(department_id) in department_access
            
        except Exception as e:
            return False

    @staticmethod
    def can_access_scheme(mongo, user_id, scheme_id):
        """Check if user can access a specific scheme"""
        try:
            user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            if not user:
                return False
            
            # Superadmin has access to all schemes
            if user.get('is_superadmin'):
                return True
            
            # Check if scheme is in user's access list
            scheme_access = user.get('scheme_access', [])
            return str(scheme_id) in scheme_access
            
        except Exception as e:
            return False

    @staticmethod
    def get_accessible_schemes_for_department(mongo, user_id, department_id):
        """Get schemes user can access within a specific department"""
        try:
            user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            if not user:
                return []
            
            # Superadmin has access to all schemes
            if user.get('is_superadmin'):
                schemes = list(mongo.db.schemes.find({
                    'department_id': ObjectId(department_id),
                    'is_active': True
                }).sort('name', 1))
            else:
                # Get user's scheme access
                scheme_access = user.get('scheme_access', [])
                if not scheme_access:
                    return []
                
                schemes = list(mongo.db.schemes.find({
                    '_id': {'$in': [ObjectId(scheme_id) for scheme_id in scheme_access]},
                    'department_id': ObjectId(department_id),
                    'is_active': True
                }).sort('name', 1))
            
            return schemes
            
        except Exception as e:
            return []