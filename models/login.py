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

            if not user.get('is_active', True):
                return {'success': False, 'message': 'Your account has been deactivated. Please contact the administrator.'}
            
            if check_password_hash(user['password'], password):
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
        """Get user's access information including departments and schemes"""
        try:
            from bson import ObjectId
            user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            
            if not user:
                return None
            
            # Check if user is superadmin (has all access)
            is_superadmin = user.get('is_superadmin', False)
            is_admin = user.get('is_admin', False)
            
            # Get department access
            department_access = user.get('department_access', [])
            if not isinstance(department_access, list):
                department_access = [department_access] if department_access else []
            
            # Get scheme access
            scheme_access = user.get('scheme_access', [])
            if not isinstance(scheme_access, list):
                scheme_access = [scheme_access] if scheme_access else []
            
            # Determine if user has all access
            has_all_access = is_superadmin or 'all' in department_access or 'all' in scheme_access
            
            # If superadmin or has 'all' access, get all departments and schemes
            if is_superadmin or 'all' in department_access:
                departments = list(mongo.db.departments.find({'is_active': True}).sort('name', 1))
                department_ids = [str(dept['_id']) for dept in departments]
            else:
                # Get specific departments user has access to
                departments = []
                if department_access:
                    try:
                        departments = list(mongo.db.departments.find({
                            '_id': {'$in': [ObjectId(dep_id) for dep_id in department_access if dep_id != 'all']},
                            'is_active': True
                        }).sort('name', 1))
                    except Exception as e:
                        print(f"ERROR - Getting departments: {e}")
                        departments = []
                department_ids = department_access if department_access and 'all' not in department_access else [str(dept['_id']) for dept in departments]
            
            # If superadmin or has 'all' scheme access, get all schemes
            if is_superadmin or 'all' in scheme_access:
                schemes = list(mongo.db.schemes.find({'is_active': True}).sort('name', 1))
                scheme_ids = [str(scheme['_id']) for scheme in schemes]
            else:
                # Get specific schemes user has access to
                schemes = []
                if scheme_access:
                    try:
                        schemes = list(mongo.db.schemes.find({
                            '_id': {'$in': [ObjectId(scheme_id) for scheme_id in scheme_access if scheme_id != 'all']},
                            'is_active': True
                        }).sort('name', 1))
                    except Exception as e:
                        print(f"ERROR - Getting schemes: {e}")
                        schemes = []
                scheme_ids = scheme_access if scheme_access and 'all' not in scheme_access else [str(scheme['_id']) for scheme in schemes]
            
            # Populate department names for schemes
            for scheme in schemes:
                department = mongo.db.departments.find_one({'_id': scheme.get('department_id')})
                scheme['department_name'] = department['name'] if department else 'Unknown'
            
            result = {
                'user_id': str(user['_id']),
                'username': user.get('username'),
                'role': user.get('role', 'user'),
                'is_superadmin': is_superadmin,
                'is_admin': is_admin,
                'has_all_access': has_all_access,
                'departments': departments,
                'schemes': schemes,
                'department_access': department_ids,
                'scheme_access': scheme_ids,
                'department_ids': department_ids,
                'scheme_ids': scheme_ids
            }
            
            return result
            
        except Exception as e:
            print(f"ERROR in get_user_access_info: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def can_access_department(mongo, user_id, department_id):
        """Check if user can access a specific department"""
        try:
            user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            if not user:
                return False
            
            # Superadmin has access to all departments
            if user.get('is_superadmin', False):
                return True
            
            # Check if department is in user's access list
            department_access = user.get('department_access', [])
            if not isinstance(department_access, list):
                department_access = [department_access] if department_access else []

            if 'all' in department_access:
                return True
            
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
            if user.get('is_superadmin', False):
                return True
            
            # Check if scheme is in user's access list
            scheme_access = user.get('scheme_access', [])
            if not isinstance(scheme_access, list):
                scheme_access = [scheme_access] if scheme_access else []

            if 'all' in scheme_access:
                return True

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