from datetime import datetime
from bson import ObjectId


class PanchayatRecord:
    def __init__(self, panchayat_name, village_name, registration_number, beneficiary_name, 
                 father_name, mother_name, category, priority, schema_code, bank_name, 
                 branch_name, ifsc_code, bank_account_no, sanction_no, amount_released, 
                 installment, credit_date, house_status, inspection_date, created_by=None):
        
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
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by,
            'is_active': self.is_active
        }

    @staticmethod
    def create_record(mongo, record_data, created_by=None):
        """Create a new panchayat record"""
        try:
            # Check if registration number already exists
            existing_record = mongo.db.panchayat_records.find_one({
                'registration_number': record_data.get('registration_number')
            })
            
            if existing_record:
                return {'success': False, 'message': 'Registration number already exists'}
            
            # Create new record
            record = PanchayatRecord(
                panchayat_name=record_data.get('panchayat_name'),
                village_name=record_data.get('village_name'),
                registration_number=record_data.get('registration_number'),
                beneficiary_name=record_data.get('beneficiary_name'),
                father_name=record_data.get('father_name'),
                mother_name=record_data.get('mother_name'),
                category=record_data.get('category'),
                priority=record_data.get('priority'),
                schema_code=record_data.get('schema_code'),
                bank_name=record_data.get('bank_name'),
                branch_name=record_data.get('branch_name'),
                ifsc_code=record_data.get('ifsc_code'),
                bank_account_no=record_data.get('bank_account_no'),
                sanction_no=record_data.get('sanction_no'),
                amount_released=record_data.get('amount_released'),
                installment=record_data.get('installment'),
                credit_date=record_data.get('credit_date'),
                house_status=record_data.get('house_status'),
                inspection_date=record_data.get('inspection_date'),
                created_by=created_by
            )
            
            result = mongo.db.panchayat_records.insert_one(record.to_dict())
            
            if result.inserted_id:
                return {'success': True, 'message': 'Record created successfully', 'record_id': str(result.inserted_id)}
            else:
                return {'success': False, 'message': 'Failed to create record'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error creating record: {str(e)}'}

    @staticmethod
    def get_all_records(mongo, page=1, per_page=10, search=None):
        """Get all records with pagination and search"""
        try:
            # Build search query
            query = {'is_active': True}
            if search:
                query['$or'] = [
                    {'panchayat_name': {'$regex': search, '$options': 'i'}},
                    {'village_name': {'$regex': search, '$options': 'i'}},
                    {'beneficiary_name': {'$regex': search, '$options': 'i'}},
                    {'registration_number': {'$regex': search, '$options': 'i'}}
                ]
            
            # Calculate pagination
            skip = (page - 1) * per_page
            
            # Get records
            records = list(mongo.db.panchayat_records.find(query)
                          .sort('created_at', -1)
                          .skip(skip)
                          .limit(per_page))
            
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
            return {'success': False, 'message': f'Error fetching records: {str(e)}'}

    @staticmethod
    def get_record_by_id(mongo, record_id):
        """Get record by ID"""
        try:
            record = mongo.db.panchayat_records.find_one({'_id': ObjectId(record_id)})
            return record
        except Exception as e:
            print(f"Error getting record by ID: {e}")
            return None

    @staticmethod
    def update_record(mongo, record_id, update_data):
        """Update record"""
        try:
            update_data['updated_at'] = datetime.utcnow()
            result = mongo.db.panchayat_records.update_one(
                {'_id': ObjectId(record_id)},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating record: {e}")
            return False

    @staticmethod
    def delete_record(mongo, record_id):
        """Soft delete record"""
        try:
            result = mongo.db.panchayat_records.update_one(
                {'_id': ObjectId(record_id)},
                {'$set': {'is_active': False, 'updated_at': datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error deleting record: {e}")
            return False

    @staticmethod
    def get_statistics(mongo):
        """Get dashboard statistics"""
        try:
            total_records = mongo.db.panchayat_records.count_documents({'is_active': True})
            total_amount = list(mongo.db.panchayat_records.aggregate([
                {'$match': {'is_active': True}},
                {'$group': {'_id': None, 'total': {'$sum': '$amount_released'}}}
            ]))
            
            # Get records by category
            category_stats = list(mongo.db.panchayat_records.aggregate([
                {'$match': {'is_active': True}},
                {'$group': {'_id': '$category', 'count': {'$sum': 1}}}
            ]))
            
            # Get records by panchayat
            panchayat_stats = list(mongo.db.panchayat_records.aggregate([
                {'$match': {'is_active': True}},
                {'$group': {'_id': '$panchayat_name', 'count': {'$sum': 1}}}
            ]))
            
            return {
                'total_records': total_records,
                'total_amount': total_amount[0]['total'] if total_amount else 0,
                'category_stats': category_stats,
                'panchayat_stats': panchayat_stats
            }
            
        except Exception as e:
            print(f"Error getting statistics: {e}")
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
            print(f"Error preparing export data: {e}")
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
            print(f"Error getting house status stats: {e}")
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
            print(f"Error getting monthly trends: {e}")
            return []