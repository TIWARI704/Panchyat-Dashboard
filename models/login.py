from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from bson.objectid import ObjectId

class User:
    def __init__(self, username, password, email=None, role='user', is_admin=False, is_superadmin=False):
        self.username = username
        self.password = generate_password_hash(password)
        self.email = email
        self.role = role
        self.is_admin = is_admin
        self.is_superadmin = is_superadmin
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
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
            "last_login": self.last_login
        }

    @staticmethod
    def create_user(mongo, username, password, email=None, role='user', is_admin=False, is_superadmin=False):
        """Create a new user in the database"""
        try:
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
            user = User(username, password, email, role, is_admin, is_superadmin)
            result = mongo.db.users.insert_one(user.to_dict())
            
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
            print(f"Error getting user by ID: {e}")
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
            print(f"Error updating user: {e}")
            return False