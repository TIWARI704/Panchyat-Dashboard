"""
Department Model

This module defines the Department model for the Panchayat Management System.
It handles department management and organization structure.
"""

from datetime import datetime
from bson import ObjectId
from models.audit_log import AuditLog

class Department:
    """
    Department model for managing organizational departments.
    
    Departments contain multiple schemes and provide organizational structure.
    """
    def __init__(self, name, description=None, is_active=True):
        self.name = name
        self.description = description
        self.is_active = is_active
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def create_department(mongo, department_data, username=None):
        """Create a new department"""
        try:
            # Check if department name already exists
            existing_department = mongo.db.departments.find_one({
                'name': department_data.get('name')
            })
            
            if existing_department:
                return {'success': False, 'message': 'Department name already exists'}
            
            # Create new department
            department = Department(
                name=department_data.get('name'),
                description=department_data.get('description'),
                is_active=department_data.get('is_active', True)
            )
            
            result = mongo.db.departments.insert_one(department.to_dict())
            
            if result.inserted_id:
                # Log the creation
                AuditLog.log_action(
                    mongo=mongo,
                    username=username or 'System',
                    model_type='department',
                    model_id=str(result.inserted_id),
                    action='created',
                    changed_fields={'name': department_data.get('name'), 'description': department_data.get('description')}
                )
                
                return {'success': True, 'message': 'Department created successfully', 'department_id': str(result.inserted_id)}
            else:
                return {'success': False, 'message': 'Failed to create department'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error creating department: {str(e)}'}

    @staticmethod
    def get_all_departments(mongo, active_only=True):
        """Get all departments"""
        try:
            query = {}
            if active_only:
                query['is_active'] = True
            
            departments = list(mongo.db.departments.find(query).sort('name', 1))
            return {
                'success': True,
                'departments': departments
            }
        except Exception as e:
            return {'success': False, 'message': f'Error fetching departments: {str(e)}'}

    @staticmethod
    def get_department_by_id(mongo, department_id):
        """Get department by ID"""
        try:
            department = mongo.db.departments.find_one({'_id': ObjectId(department_id)})
            return department
        except Exception as e:
            return None

    @staticmethod
    def update_department(mongo, department_id, update_data, username=None):
        """Update department"""
        try:
            # Get old data for audit log
            old_department = mongo.db.departments.find_one({'_id': ObjectId(department_id)})
            if not old_department:
                return {'success': False, 'message': 'Department not found'}
            
            # Check if name is being updated and if it already exists
            if 'name' in update_data:
                existing_department = mongo.db.departments.find_one({
                    'name': update_data['name'],
                    '_id': {'$ne': ObjectId(department_id)}
                })
                if existing_department:
                    return {'success': False, 'message': 'Department name already exists'}
            
            # Track changed fields
            changed_fields = {}
            for key, new_value in update_data.items():
                if key in old_department and old_department[key] != new_value:
                    changed_fields[key] = {
                        'old': old_department[key],
                        'new': new_value
                    }
            
            update_data['updated_at'] = datetime.utcnow()
            result = mongo.db.departments.update_one(
                {'_id': ObjectId(department_id)},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                # Log the update
                AuditLog.log_action(
                    mongo=mongo,
                    username=username or 'System',
                    model_type='department',
                    model_id=str(department_id),
                    action='updated',
                    changed_fields=changed_fields
                )
                
                return {'success': True, 'message': 'Department updated successfully'}
            else:
                return {'success': False, 'message': 'No changes made to department'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error updating department: {str(e)}'}

    @staticmethod
    def delete_department(mongo, department_id, username=None):
        """Soft delete department"""
        try:
            # Get department data before deletion
            department = mongo.db.departments.find_one({'_id': ObjectId(department_id)})
            if not department:
                return {'success': False, 'message': 'Department not found'}
            
            # Check if department has schemes
            schemes_count = mongo.db.schemes.count_documents({'department_id': ObjectId(department_id), 'is_active': True})
            if schemes_count > 0:
                return {'success': False, 'message': f'Cannot delete department. It has {schemes_count} active scheme(s).'}
            
            result = mongo.db.departments.update_one(
                {'_id': ObjectId(department_id)},
                {'$set': {'is_active': False, 'updated_at': datetime.utcnow()}}
            )
            
            if result.modified_count > 0:
                # Log the deletion
                AuditLog.log_action(
                    mongo=mongo,
                    username=username or 'System',
                    model_type='department',
                    model_id=str(department_id),
                    action='deleted',
                    changed_fields={'department_name': department.get('name'), 'is_active': {'old': True, 'new': False}}
                )
                
                return {'success': True, 'message': 'Department deleted successfully'}
            else:
                return {'success': False, 'message': 'Department not found or could not be deleted'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error deleting department: {str(e)}'}
