"""
Audit Log Model

This module defines the Audit Log model for tracking all changes in the system.
It records username, changed fields, and timestamps.
"""

from datetime import datetime
from bson import ObjectId

class AuditLog:
    """
    Audit Log model for tracking changes to models.
    
    Tracks:
    - Username who made the change
    - Changed fields with old and new values
    - Action type (created, updated, deleted)
    - Timestamp
    """
    
    def __init__(self, username, model_type, model_id, action, changed_fields=None):
        self.username = username
        self.model_type = model_type  # e.g., 'department', 'scheme', 'user'
        self.model_id = model_id
        self.action = action  # 'created', 'updated', 'deleted'
        self.changed_fields = changed_fields or {}
        self.created_at = datetime.utcnow()

    def to_dict(self):
        return {
            'username': self.username,
            'model_type': self.model_type,
            'model_id': self.model_id,
            'action': self.action,
            'changed_fields': self.changed_fields,
            'created_at': self.created_at
        }

    @staticmethod
    def log_action(mongo, username, model_type, model_id, action, changed_fields=None):
        """Create an audit log entry"""
        try:
            audit_log = AuditLog(
                username=username,
                model_type=model_type,
                model_id=model_id,
                action=action,
                changed_fields=changed_fields
            )
            
            mongo.db.audit_logs.insert_one(audit_log.to_dict())
            return {'success': True}
        except Exception as e:
            print(f'Error creating audit log: {str(e)}')
            return {'success': False, 'message': str(e)}

    @staticmethod
    def get_logs(mongo, filters=None, limit=100, skip=0):
        """Get audit logs with optional filters"""
        try:
            query = {}
            
            if filters:
                if 'username' in filters:
                    query['username'] = {'$regex': filters['username'], '$options': 'i'}
                if 'model_type' in filters:
                    query['model_type'] = filters['model_type']
                if 'action' in filters:
                    query['action'] = filters['action']
                if 'start_date' in filters:
                    query['created_at'] = {'$gte': filters['start_date']}
                if 'end_date' in filters:
                    if 'created_at' in query:
                        query['created_at']['$lte'] = filters['end_date']
                    else:
                        query['created_at'] = {'$lte': filters['end_date']}
            
            logs = list(mongo.db.audit_logs.find(query)
                       .sort('created_at', -1)
                       .skip(skip)
                       .limit(limit))
            
            total = mongo.db.audit_logs.count_documents(query)
            
            return {
                'success': True,
                'logs': logs,
                'total': total
            }
        except Exception as e:
            return {'success': False, 'message': f'Error fetching audit logs: {str(e)}'}

    @staticmethod
    def get_model_history(mongo, model_type, model_id):
        """Get all audit logs for a specific model"""
        try:
            logs = list(mongo.db.audit_logs.find({
                'model_type': model_type,
                'model_id': model_id
            }).sort('created_at', -1))
            
            return {
                'success': True,
                'logs': logs
            }
        except Exception as e:
            return {'success': False, 'message': f'Error fetching model history: {str(e)}'}