"""
Import History Model

This module defines the ImportHistory model for tracking bulk import operations.
It handles import status, progress tracking, and batch operations.
"""

from datetime import datetime
from bson import ObjectId
from enum import Enum

class ImportStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

class ImportHistory:
    """
    ImportHistory model for managing bulk import operations.
    
    Tracks import progress, status, and provides batch operations for performance.
    """
    
    @staticmethod
    def create_import_record(mongo, file_name, scheme_id, department_id, imported_by, total_records=0):
        """Create a new import history record"""
        try:
            import_record = {
                'file_name': file_name,
                'scheme_id': ObjectId(scheme_id),
                'department_id': ObjectId(department_id),
                'imported_by': imported_by,
                'status': ImportStatus.PENDING.value,
                'total_records': total_records,
                'imported_count': 0,
                'failed_count': 0,
                'duplicate_count': 0,
                'created_at': datetime.utcnow(),
                'started_at': None,
                'completed_at': None,
                'failed_at': None,
                'stopped_at': None,
                'stopped_by': None,
                'error_message': None,
                'batch_size': 100,
                'current_batch': 0,
                'total_batches': 0,
                'is_active': True
            }
            
            result = mongo.db.import_history.insert_one(import_record)
            return {'success': True, 'import_id': str(result.inserted_id)}
            
        except Exception as e:
            return {'success': False, 'message': f'Error creating import record: {str(e)}'}
    
    @staticmethod
    def update_import_status(mongo, import_id, status, **kwargs):
        """Update import status and related fields"""
        try:
            update_data = {'status': status.value if isinstance(status, ImportStatus) else status}
            
            # Add timestamp based on status
            if status == ImportStatus.IN_PROGRESS.value or (isinstance(status, ImportStatus) and status == ImportStatus.IN_PROGRESS):
                update_data['started_at'] = datetime.utcnow()
            elif status == ImportStatus.COMPLETED.value or (isinstance(status, ImportStatus) and status == ImportStatus.COMPLETED):
                update_data['completed_at'] = datetime.utcnow()
            elif status == ImportStatus.FAILED.value or (isinstance(status, ImportStatus) and status == ImportStatus.FAILED):
                update_data['failed_at'] = datetime.utcnow()
            elif status == ImportStatus.STOPPED.value or (isinstance(status, ImportStatus) and status == ImportStatus.STOPPED):
                update_data['stopped_at'] = datetime.utcnow()
            
            # Add any additional fields
            update_data.update(kwargs)
            
            result = mongo.db.import_history.update_one(
                {'_id': ObjectId(import_id)},
                {'$set': update_data}
            )
            
            return {'success': True, 'modified_count': result.modified_count}
            
        except Exception as e:
            return {'success': False, 'message': f'Error updating import status: {str(e)}'}
    
    @staticmethod
    def update_import_progress(mongo, import_id, imported_count, failed_count, duplicate_count, current_batch):
        """Update import progress with batch information"""
        try:
            result = mongo.db.import_history.update_one(
                {'_id': ObjectId(import_id)},
                {'$set': {
                    'imported_count': imported_count,
                    'failed_count': failed_count,
                    'duplicate_count': duplicate_count,
                    'current_batch': current_batch,
                    'updated_at': datetime.utcnow()
                }}
            )
            
            return {'success': True, 'modified_count': result.modified_count}
            
        except Exception as e:
            return {'success': False, 'message': f'Error updating import progress: {str(e)}'}
    
    @staticmethod
    def get_import_history(mongo, username=None, limit=50, skip=0):
        """Get import history with optional user filtering"""
        try:
            query = {'is_active': True}
            
            # Filter by user if provided
            if username:
                query['imported_by'] = username
            
            # Get imports with department and scheme names
            pipeline = [
                {'$match': query},
                {'$lookup': {
                    'from': 'departments',
                    'localField': 'department_id',
                    'foreignField': '_id',
                    'as': 'department'
                }},
                {'$lookup': {
                    'from': 'schemes',
                    'localField': 'scheme_id',
                    'foreignField': '_id',
                    'as': 'scheme'
                }},
                {'$addFields': {
                    'department_name': {'$arrayElemAt': ['$department.name', 0]},
                    'scheme_name': {'$arrayElemAt': ['$scheme.name', 0]}
                }},
                {'$sort': {'created_at': -1}},
                {'$skip': skip},
                {'$limit': limit}
            ]
            
            imports = list(mongo.db.import_history.aggregate(pipeline))
            
            # Convert ObjectId and datetime to string for JSON serialization
            for import_record in imports:
                import_record['_id'] = {'$oid': str(import_record['_id'])}
                if 'scheme_id' in import_record:
                    import_record['scheme_id'] = {'$oid': str(import_record['scheme_id'])}
                if 'department_id' in import_record:
                    import_record['department_id'] = {'$oid': str(import_record['department_id'])}
                
                # Remove lookup arrays that contain ObjectIds
                if 'department' in import_record:
                    del import_record['department']
                if 'scheme' in import_record:
                    del import_record['scheme']
                
                # Convert datetime fields to ISO format strings
                datetime_fields = ['created_at', 'started_at', 'completed_at', 'failed_at', 'stopped_at', 'updated_at']
                for field in datetime_fields:
                    if field in import_record and import_record[field]:
                        import_record[field] = import_record[field].isoformat()
            
            # Get total count
            total_count = mongo.db.import_history.count_documents(query)
            
            return {
                'success': True,
                'imports': imports,
                'total_count': total_count
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Error fetching import history: {str(e)}'}
    
    @staticmethod
    def get_import_by_id(mongo, import_id):
        """Get specific import record by ID"""
        try:
            import_record = mongo.db.import_history.find_one({'_id': ObjectId(import_id)})
            
            if not import_record:
                return {'success': False, 'message': 'Import record not found'}
            
            # Convert ObjectId and datetime to string for JSON serialization
            import_record['_id'] = {'$oid': str(import_record['_id'])}
            if 'scheme_id' in import_record:
                import_record['scheme_id'] = {'$oid': str(import_record['scheme_id'])}
            if 'department_id' in import_record:
                import_record['department_id'] = {'$oid': str(import_record['department_id'])}
            
            # Convert datetime fields to ISO format strings
            datetime_fields = ['created_at', 'started_at', 'completed_at', 'failed_at', 'stopped_at', 'updated_at']
            for field in datetime_fields:
                if field in import_record and import_record[field]:
                    import_record[field] = import_record[field].isoformat()
            
            return {'success': True, 'import_record': import_record}
            
        except Exception as e:
            return {'success': False, 'message': f'Error fetching import record: {str(e)}'}
    
    @staticmethod
    def stop_import(mongo, import_id, stopped_by):
        """Stop an import operation"""
        try:
            result = mongo.db.import_history.update_one(
                {'_id': ObjectId(import_id), 'status': ImportStatus.IN_PROGRESS.value},
                {'$set': {
                    'status': ImportStatus.STOPPED.value,
                    'stopped_at': datetime.utcnow(),
                    'stopped_by': stopped_by
                }}
            )
            
            if result.modified_count > 0:
                return {'success': True, 'message': 'Import stopped successfully'}
            else:
                return {'success': False, 'message': 'Import not found or not in progress'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error stopping import: {str(e)}'}
    
    @staticmethod
    def get_active_imports(mongo):
        """Get all active imports (in progress)"""
        try:
            imports = list(mongo.db.import_history.find({
                'status': ImportStatus.IN_PROGRESS.value,
                'is_active': True
            }))
            
            # Convert ObjectId and datetime to string for JSON serialization
            for import_record in imports:
                import_record['_id'] = {'$oid': str(import_record['_id'])}
                if 'scheme_id' in import_record:
                    import_record['scheme_id'] = {'$oid': str(import_record['scheme_id'])}
                if 'department_id' in import_record:
                    import_record['department_id'] = {'$oid': str(import_record['department_id'])}
                
                # Convert datetime fields to ISO format strings
                datetime_fields = ['created_at', 'started_at', 'completed_at', 'failed_at', 'stopped_at', 'updated_at']
                for field in datetime_fields:
                    if field in import_record and import_record[field]:
                        import_record[field] = import_record[field].isoformat()
            
            return {'success': True, 'imports': imports}
            
        except Exception as e:
            return {'success': False, 'message': f'Error fetching active imports: {str(e)}'}
