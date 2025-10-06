"""
Panchayat Record Model

This module defines the PanchayatRecord model for the Panchayat Management System.
It handles all panchayat record operations including CRUD, statistics, and data export.
"""

from datetime import datetime
from bson import ObjectId
from models.audit_log import AuditLog

class PanchayatRecord:
    """
    PanchayatRecord model for managing panchayat records.
    
    Supports dynamic schema-based data storage with department and scheme associations.
    """
    def __init__(self, panchayat_name, village_name, registration_number, beneficiary_name, 
                 father_name, mother_name, category, priority, schema_code, bank_name, 
                 branch_name, ifsc_code, bank_account_no, sanction_no, amount_released, 
                 installment, credit_date, house_status, inspection_date, department_id=None, 
                 scheme_id=None, custom_data=None, created_by=None):
        
        self.panchayat_name = panchayat_name
        self.village_name = village_name
        self.registration_number = registration_number
        self.beneficiary_name = beneficiary_name
        self.father_name = father_name
        self.mother_name = mother_name
        self.category = category
        self.priority = int(priority) if priority and str(priority).isdigit() else 0
        self.schema_code = schema_code
        self.bank_name = bank_name
        self.branch_name = branch_name
        self.ifsc_code = ifsc_code
        self.bank_account_no = bank_account_no
        self.sanction_no = sanction_no
        self.amount_released = float(amount_released) if amount_released else 0.0
        self.installment = int(installment) if installment else 0
        self.credit_date = credit_date
        self.house_status = house_status
        self.inspection_date = inspection_date
        self.department_id = ObjectId(department_id) if department_id else None
        self.scheme_id = ObjectId(scheme_id) if scheme_id else None
        self.custom_data = custom_data or {}  # For scheme-specific custom fields
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.created_by = created_by
        self.is_active = True

    def to_dict(self):
        return {
            'panchayat_name': self.panchayat_name,
            'village_name': self.village_name,
            'registration_number': self.registration_number,
            'beneficiary_name': self.beneficiary_name,
            'father_name': self.father_name,
            'mother_name': self.mother_name,
            'category': self.category,
            'priority': self.priority,
            'schema_code': self.schema_code,
            'bank_name': self.bank_name,
            'branch_name': self.branch_name,
            'ifsc_code': self.ifsc_code,
            'bank_account_no': self.bank_account_no,
            'sanction_no': self.sanction_no,
            'amount_released': self.amount_released,
            'installment': self.installment,
            'credit_date': self.credit_date,
            'house_status': self.house_status,
            'inspection_date': self.inspection_date,
            'department_id': self.department_id,
            'scheme_id': self.scheme_id,
            'custom_data': self.custom_data,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by,
            'is_active': self.is_active
        }

    @staticmethod
    def create_record(mongo, record_data, created_by=None):
        """Create a new panchayat record"""
        try:
            # Check if registration number already exists (only if provided)
            if record_data.get('registration_number'):
                existing_record = mongo.db.panchayat_records.find_one({
                    'registration_number': record_data.get('registration_number')
                })
                
                if existing_record:
                    return {'success': False, 'message': 'Registration number already exists'}
            
            # Create new record with only provided fields
            record_doc = {
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'created_by': created_by,
                'is_active': True
            }
            
            # Add only the fields that are provided in record_data
            for key, value in record_data.items():
                if value is not None and value != '':
                    if key in ['department_id', 'scheme_id'] and value:
                        record_doc[key] = ObjectId(value)
                    else:
                        record_doc[key] = value
            
            result = mongo.db.panchayat_records.insert_one(record_doc)
            
            if result.inserted_id:
                # Log the creation
                AuditLog.log_action(
                    mongo=mongo,
                    username=created_by or 'System',
                    model_type='panchayat_record',
                    model_id=str(result.inserted_id),
                    action='created',
                    changed_fields={
                        'beneficiary_name': record_data.get('beneficiary_name'),
                        'registration_number': record_data.get('registration_number'),
                        'panchayat_name': record_data.get('panchayat_name')
                    }
                )
                
                return {'success': True, 'message': 'Record created successfully', 'record_id': str(result.inserted_id)}
            else:
                return {'success': False, 'message': 'Failed to create record'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error creating record: {str(e)}'}

    @staticmethod
    def get_all_records(mongo, page=1, per_page=10, search=None, department_ids=None, scheme_ids=None, user_id=None, filters=None, taluka_filter=None):
        """Get all records with pagination, search, and filtering"""
        try:
            # Build search query
            query = {'is_active': True}

            # Add user access filtering FIRST (most important filter)
            if user_id:
                from models.login import User
                user_access = User.get_user_access_info(mongo, user_id)

                if user_access and not user_access.get('has_all_access', False):
                    # User has restricted access - apply filters
                    user_department_access = user_access.get('department_access', [])
                    user_scheme_access = user_access.get('scheme_access', [])
                    
                    # Apply department filter if user doesn't have 'all' access
                    if user_department_access and 'all' not in user_department_access:
                        try:
                            # Filter out 'all' and convert valid IDs to ObjectId
                            valid_dept_ids = [ObjectId(dep_id) for dep_id in user_department_access if dep_id != 'all']
                            if valid_dept_ids:
                                query['department_id'] = {'$in': valid_dept_ids}
                            else:
                                # User has no valid department access - return empty results
                                return {
                                    'success': True,
                                    'records': [],
                                    'total_records': 0,
                                    'page': page,
                                    'per_page': per_page,
                                    'total_pages': 0
                                }
                        except Exception as e:
                            print(f"ERROR - Converting department IDs: {e}")
                            # Invalid ObjectIds - return empty results
                            return {
                                'success': True,
                                'records': [],
                                'total_records': 0,
                                'page': page,
                                'per_page': per_page,
                                'total_pages': 0
                            }
                    
                    # Apply scheme filter if user doesn't have 'all' access
                    if user_scheme_access and 'all' not in user_scheme_access:
                        try:
                            # Filter out 'all' and convert valid IDs to ObjectId
                            valid_scheme_ids = [ObjectId(scheme_id) for scheme_id in user_scheme_access if scheme_id != 'all']
                            if valid_scheme_ids:
                                query['scheme_id'] = {'$in': valid_scheme_ids}
                            else:
                                # User has no valid scheme access - return empty results
                                return {
                                    'success': True,
                                    'records': [],
                                    'total_records': 0,
                                    'page': page,
                                    'per_page': per_page,
                                    'total_pages': 0
                                }
                        except Exception as e:
                            print(f"ERROR - Converting scheme IDs: {e}")
                            # Invalid ObjectIds - return empty results
                            return {
                                'success': True,
                                'records': [],
                                'total_records': 0,
                                'page': page,
                                'per_page': per_page,
                                'total_pages': 0
                            }
            
            # Add search conditions
            if search:
                search_conditions = []
                
                # Search in custom_data fields
                search_conditions.append({'custom_data': {'$regex': search, '$options': 'i'}})
                
                # Search in legacy fields if they exist
                legacy_fields = ['panchayat_name', 'village_name', 'beneficiary_name', 'registration_number']
                for field in legacy_fields:
                    search_conditions.append({field: {'$regex': search, '$options': 'i'}})
                
                query['$or'] = search_conditions
            
            # Add department filter (intersect with user access if already set)
            if department_ids:
                dept_object_ids = [ObjectId(dep_id) for dep_id in department_ids]
                
                if 'department_id' in query:
                    # Intersect with existing user access filter
                    existing_dept_ids = query['department_id'].get('$in', [])
                    intersected_ids = [did for did in dept_object_ids if did in existing_dept_ids]
                    if intersected_ids:
                        query['department_id'] = {'$in': intersected_ids}
                    else:
                        # No intersection - return empty results
                        return {
                            'success': True,
                            'records': [],
                            'total_records': 0,
                            'page': page,
                            'per_page': per_page,
                            'total_pages': 0
                        }
                else:
                    query['department_id'] = {'$in': dept_object_ids}
            
            # Add scheme filter (intersect with user access if already set)
            if scheme_ids:
                scheme_object_ids = [ObjectId(scheme_id) for scheme_id in scheme_ids]
                
                if 'scheme_id' in query:
                    # Intersect with existing user access filter
                    existing_scheme_ids = query['scheme_id'].get('$in', [])
                    intersected_ids = [sid for sid in scheme_object_ids if sid in existing_scheme_ids]
                    if intersected_ids:
                        query['scheme_id'] = {'$in': intersected_ids}
                    else:
                        # No intersection - return empty results
                        return {
                            'success': True,
                            'records': [],
                            'total_records': 0,
                            'page': page,
                            'per_page': per_page,
                            'total_pages': 0
                        }
                else:
                    query['scheme_id'] = {'$in': scheme_object_ids}
            
            # Add taluka filter
            if taluka_filter:
                query['custom_data.taluka'] = taluka_filter
            
            # Add custom filters
            if filters:
                for filter_condition in filters:
                    field = filter_condition.get('field')
                    operator = filter_condition.get('operator', 'eq')
                    value = filter_condition.get('value')
                    
                    if field and value is not None:
                        if operator == 'eq':
                            query[field] = value
                        elif operator == 'ne':
                            query[field] = {'$ne': value}
                        elif operator == 'gt':
                            query[field] = {'$gt': value}
                        elif operator == 'gte':
                            query[field] = {'$gte': value}
                        elif operator == 'lt':
                            query[field] = {'$lt': value}
                        elif operator == 'lte':
                            query[field] = {'$lte': value}
                        elif operator == 'regex':
                            query[field] = {'$regex': value, '$options': 'i'}
                        elif operator == 'in':
                            query[field] = {'$in': value}
                        elif operator == 'nin':
                            query[field] = {'$nin': value}
            
            # Calculate pagination
            skip = (page - 1) * per_page
            
            # Get records with department and scheme names
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
                {'$limit': per_page}
            ]
            
            records = list(mongo.db.panchayat_records.aggregate(pipeline))
            
            # Get total count
            total_records = mongo.db.panchayat_records.count_documents(query)
            
            return {
                'success': True,
                'records': records,
                'total_records': total_records,
                'page': page,
                'per_page': per_page,
                'total_pages': (total_records + per_page - 1) // per_page
            }
            
        except Exception as e:
            print(f"ERROR in get_all_records: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Error fetching records: {str(e)}'}

    @staticmethod
    def get_record_by_id(mongo, record_id):
        """Get record by ID"""
        try:
            record = mongo.db.panchayat_records.find_one({'_id': ObjectId(record_id)})
            return record
        except Exception as e:
            return None

    @staticmethod
    def update_record(mongo, record_id, update_data, updated_by=None):
        """Update record"""
        try:
            # Get old data for audit log
            old_record = mongo.db.panchayat_records.find_one({'_id': ObjectId(record_id)})
            if not old_record:
                return False
            
            # Track changed fields
            changed_fields = {}
            for key, new_value in update_data.items():
                if key in old_record and old_record[key] != new_value:
                    changed_fields[key] = {
                        'old': old_record[key],
                        'new': new_value
                    }
            
            update_data['updated_at'] = datetime.utcnow()
            result = mongo.db.panchayat_records.update_one(
                {'_id': ObjectId(record_id)},
                {'$set': update_data}
            )
            
            if result.modified_count > 0 and changed_fields:
                # Log the update
                AuditLog.log_action(
                    mongo=mongo,
                    username=updated_by or 'System',
                    model_type='panchayat_record',
                    model_id=str(record_id),
                    action='updated',
                    changed_fields=changed_fields
                )
            
            return result.modified_count > 0
        except Exception as e:
            return False

    @staticmethod
    def delete_record(mongo, record_id, deleted_by=None):
        """Soft delete record"""
        try:
            # Get record data before deletion
            record = mongo.db.panchayat_records.find_one({'_id': ObjectId(record_id)})
            if not record:
                return False
            
            result = mongo.db.panchayat_records.update_one(
                {'_id': ObjectId(record_id)},
                {'$set': {'is_active': False, 'updated_at': datetime.utcnow()}}
            )
            
            if result.modified_count > 0:
                # Log the deletion
                AuditLog.log_action(
                    mongo=mongo,
                    username=deleted_by or 'System',
                    model_type='panchayat_record',
                    model_id=str(record_id),
                    action='deleted',
                    changed_fields={
                        'beneficiary_name': record.get('beneficiary_name'),
                        'is_active': {'old': True, 'new': False}
                    }
                )
            
            return result.modified_count > 0
        except Exception as e:
            return False

    @staticmethod
    def get_statistics(mongo, department_ids=None, scheme_ids=None):
        """Get dashboard statistics with optional department and scheme filters"""
        try:
            # Build match criteria
            match_criteria = {'is_active': True}
            
            if department_ids:
                match_criteria['department_id'] = {'$in': [ObjectId(dept_id) for dept_id in department_ids]}
            
            if scheme_ids:
                match_criteria['scheme_id'] = {'$in': [ObjectId(scheme_id) for scheme_id in scheme_ids]}
            
            total_records = mongo.db.panchayat_records.count_documents(match_criteria)
            total_amount = list(mongo.db.panchayat_records.aggregate([
                {'$match': match_criteria},
                {'$group': {'_id': None, 'total': {'$sum': '$amount_released'}}}
            ]))
            
            # Get records by category
            category_stats = list(mongo.db.panchayat_records.aggregate([
                {'$match': match_criteria},
                {'$group': {'_id': '$category', 'count': {'$sum': 1}}}
            ]))
            
            # Get records by panchayat
            panchayat_stats = list(mongo.db.panchayat_records.aggregate([
                {'$match': match_criteria},
                {'$group': {'_id': '$panchayat_name', 'count': {'$sum': 1}}}
            ]))
            
            return {
                'total_records': total_records,
                'total_amount': total_amount[0]['total'] if total_amount else 0,
                'category_stats': category_stats,
                'panchayat_stats': panchayat_stats
            }
            
        except Exception as e:
            return {
                'total_records': 0,
                'total_amount': 0,
                'category_stats': [],
                'panchayat_stats': []
            }

    @staticmethod
    def export_to_excel_data(mongo):
        """Get all records for Excel export"""
        try:
            records = list(mongo.db.panchayat_records.find({'is_active': True}).sort('created_at', -1))
            
            flattened_data = []
            for record in records:
                flat_record = {
                    'Panchayat Name': record.get('panchayat_name', ''),
                    'Village Name': record.get('village_name', ''),
                    'Registration Number': record.get('registration_number', ''),
                    'Beneficiary Name': record.get('beneficiary_name', ''),
                    'Father Name': record.get('father_name', ''),
                    'Mother Name': record.get('mother_name', ''),
                    'Category': record.get('category', ''),
                    'Priority': record.get('priority', ''),
                    'Schema Code': record.get('schema_code', ''),
                    'Bank Name': record.get('bank_name', ''),
                    'Branch Name': record.get('branch_name', ''),
                    'IFSC Code': record.get('ifsc_code', ''),
                    'Bank Account No': record.get('bank_account_no', ''),
                    'Sanction No': record.get('sanction_no', ''),
                    'Amount Released': record.get('amount_released', 0),
                    'Installment': record.get('installment', 0),
                    'Credit Date': record.get('credit_date').strftime('%Y-%m-%d') if record.get('credit_date') else '',
                    'House Status': record.get('house_status', ''),
                    'Inspection Date': record.get('inspection_date').strftime('%Y-%m-%d') if record.get('inspection_date') else '',
                    'Created At': record.get('created_at').strftime('%Y-%m-%d %H:%M:%S') if record.get('created_at') else '',
                    'Created By': record.get('created_by', '')
                }
                flattened_data.append(flat_record)
            
            return flattened_data
            
        except Exception as e:
            return []

    @staticmethod
    def get_house_status_stats(mongo):
        """Get house status distribution for charts"""
        try:
            pipeline = [
                {"$group": {"_id": "$house_status", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            return list(mongo.db.panchayat_records.aggregate(pipeline))
        except Exception as e:
            return []

    @staticmethod
    def get_monthly_trends(mongo, months=6):
        """Get monthly registration trends"""
        try:
            from datetime import datetime, timedelta
            months_ago = datetime.now() - timedelta(days=30*months)
            
            pipeline = [
                {"$match": {"created_at": {"$gte": months_ago}}},
                {"$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"}
                    },
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id.year": 1, "_id.month": 1}}
            ]
            return list(mongo.db.panchayat_records.aggregate(pipeline))
        except Exception as e:
            return []

    @staticmethod
    def get_records_by_user_access(mongo, user_id, page=1, per_page=10, search=None, department_ids=None, scheme_ids=None, filters=None):
        """Get records filtered by user's department and scheme access"""
        try:
            from models.login import User
            
            # Get user's access information
            user_access = User.get_user_access_info(mongo, user_id)
            if not user_access:
                return {'success': False, 'message': 'User not found'}
            
            # If user has all access (superadmin), use all departments and schemes
            if user_access['has_all_access']:
                return PanchayatRecord.get_all_records(mongo, page, per_page, search, department_ids, scheme_ids, filters)
            
            # Filter by user's accessible departments and schemes
            user_department_ids = [str(dep['_id']) for dep in user_access['departments']]
            user_scheme_ids = [str(scheme['_id']) for scheme in user_access['schemes']]
            
            # If specific department_ids or scheme_ids are provided, filter them by user access
            if department_ids:
                accessible_department_ids = [dep_id for dep_id in department_ids if dep_id in user_department_ids]
                if not accessible_department_ids:
                    return {'success': True, 'records': [], 'total_records': 0, 'page': page, 'per_page': per_page, 'total_pages': 0}
                department_ids = accessible_department_ids
            else:
                department_ids = user_department_ids
            
            if scheme_ids:
                accessible_scheme_ids = [scheme_id for scheme_id in scheme_ids if scheme_id in user_scheme_ids]
                if not accessible_scheme_ids:
                    return {'success': True, 'records': [], 'total_records': 0, 'page': page, 'per_page': per_page, 'total_pages': 0}
                scheme_ids = accessible_scheme_ids
            else:
                scheme_ids = user_scheme_ids
            
            return PanchayatRecord.get_all_records(mongo, page, per_page, search, department_ids, scheme_ids, filters)
            
        except Exception as e:
            return {'success': False, 'message': f'Error fetching records by user access: {str(e)}'}

    @staticmethod
    def export_to_excel_data_filtered(mongo, user_id=None, department_ids=None, scheme_ids=None, filters=None):
        """Get filtered records for Excel export"""
        try:
            if user_id:
                # Get records filtered by user access
                result = PanchayatRecord.get_records_by_user_access(mongo, user_id, 1, 10000, None, department_ids, scheme_ids, filters)
                if not result['success']:
                    return []
                records = result['records']
            else:
                # Get all records with filters
                result = PanchayatRecord.get_all_records(mongo, 1, 10000, None, department_ids, scheme_ids, filters)
                if not result['success']:
                    return []
                records = result['records']
            
            flattened_data = []
            for record in records:
                flat_record = {
                    'Panchayat Name': record.get('panchayat_name', ''),
                    'Village Name': record.get('village_name', ''),
                    'Registration Number': record.get('registration_number', ''),
                    'Beneficiary Name': record.get('beneficiary_name', ''),
                    'Father Name': record.get('father_name', ''),
                    'Mother Name': record.get('mother_name', ''),
                    'Category': record.get('category', ''),
                    'Priority': record.get('priority', ''),
                    'Schema Code': record.get('schema_code', ''),
                    'Department': record.get('department_name', ''),
                    'Scheme': record.get('scheme_name', ''),
                    'Bank Name': record.get('bank_name', ''),
                    'Branch Name': record.get('branch_name', ''),
                    'IFSC Code': record.get('ifsc_code', ''),
                    'Bank Account No': record.get('bank_account_no', ''),
                    'Sanction No': record.get('sanction_no', ''),
                    'Amount Released': record.get('amount_released', 0),
                    'Installment': record.get('installment', 0),
                    'Credit Date': record.get('credit_date').strftime('%Y-%m-%d') if record.get('credit_date') else '',
                    'House Status': record.get('house_status', ''),
                    'Inspection Date': record.get('inspection_date').strftime('%Y-%m-%d') if record.get('inspection_date') else '',
                    'Created At': record.get('created_at').strftime('%Y-%m-%d %H:%M:%S') if record.get('created_at') else '',
                    'Created By': record.get('created_by', '')
                }
                
                # Add custom data fields
                custom_data = record.get('custom_data', {})
                for key, value in custom_data.items():
                    flat_record[f'Custom - {key}'] = value
                
                flattened_data.append(flat_record)
            
            return flattened_data
            
        except Exception as e:
            return []

    @staticmethod
    def get_records_by_user(mongo, user_id):
        """Get all records created by a specific user"""
        try:
            # Get user info to check access
            user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            if not user:
                return {'success': False, 'message': 'User not found'}
            
            # Build query - get records created by this user
            query = {
                'created_by': user.get('username'),
                'is_active': True
            }
            
            # Get records with department and scheme names
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
                {'$sort': {'created_at': -1}}
            ]
            
            records = list(mongo.db.panchayat_records.aggregate(pipeline))
            
            return {
                'success': True,
                'records': records,
                'total': len(records)
            }
        except Exception as e:
            print(f"ERROR in get_records_by_user: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Error fetching records: {str(e)}'}