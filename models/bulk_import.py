"""
Bulk Import Model

This module handles bulk import operations for panchayat records.
Supports Excel/CSV file imports with validation and error handling.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from bson import ObjectId
from models.admin import PanchayatRecord
from models.audit_log import AuditLog
import io

class BulkImport:
    """
    Bulk Import model for importing multiple records from Excel/CSV files.
    """
    
    @staticmethod
    def _to_int(value, default=0):
        """Safe int conversion: accept numeric types or numeric strings with commas, return default on failure"""
        if value is None:
            return default
        try:
            if isinstance(value, str):
                v = value.strip().replace(',', '')
                if v == '':
                    return default
                # Handle text priorities
                priority_map = {
                    'high': 1, 'urgent': 1, 'critical': 1,
                    'medium': 2, 'normal': 2, 'standard': 2,
                    'low': 3, 'routine': 3, 'basic': 3
                }
                if v.lower() in priority_map:
                    return priority_map[v.lower()]
                return int(float(v))
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _to_float(value, default=0.0):
        """Safe float conversion: accept numeric types or numeric strings with commas, return default on failure"""
        if value is None:
            return default
        try:
            if isinstance(value, str):
                v = value.strip().replace(',', '')
                if v == '':
                    return default
                return float(v)
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _is_numeric_like(value):
        """Return True if value can be interpreted as a number (robust for pandas/numpy values and messy strings)"""
        if value is None:
            return True  # Allow None/empty values for optional numeric fields
        try:
            # normalize common nuisances in Excel/CSV strings
            if isinstance(value, str):
                v = value.strip()
                # remove non-breaking spaces and common thousands separators
                v = v.replace('\u00A0', '').replace('\xa0', '').replace(',', '')
                if v == '' or v.lower() in ['nan', 'null', 'none', '-']:
                    return True  # Allow empty/null-like values
                # use pandas.to_numeric for robust coercion
                num = pd.to_numeric(v, errors='coerce')
                return not pd.isna(num)
            # for numpy / pandas numeric types, pandas.to_numeric handles them too
            num = pd.to_numeric(value, errors='coerce')
            return not pd.isna(num)
        except Exception:
            return False

    @staticmethod
    def validate_file_format(file):
        """Validate if the uploaded file is in supported format"""
        try:
            filename = file.filename.lower()
            if not (filename.endswith('.xlsx') or filename.endswith('.xls') or filename.endswith('.csv')):
                return {'success': False, 'message': 'Invalid file format. Only Excel (.xlsx, .xls) and CSV files are supported.'}
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'message': f'Error validating file: {str(e)}'}
    
    @staticmethod
    def read_file_data(file):
        """Read data from uploaded Excel or CSV file"""
        try:
            filename = file.filename.lower()
            
            # Read file content into memory
            file_content = file.read()
            file.seek(0)  # Reset file pointer
            
            # Read into DataFrame (read all as strings to avoid dtype surprises)
            if filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_content), dtype=str)
            else:
                df = pd.read_excel(io.BytesIO(file_content), dtype=str)
            
            # Normalize column names: strip, lower, replace spaces with underscores
            df.columns = [str(col).strip().lower().replace(' ', '_') for col in df.columns]
            
            # Map common alternate headers to canonical names
            header_aliases = {
                'panchayat': 'panchayat_name',
                'panchayatname': 'panchayat_name',
                'beneficiary': 'beneficiary_name',
                'beneficiaryname': 'beneficiary_name'
            }
            df.rename(columns=lambda c: header_aliases.get(c, c), inplace=True)
            
            # Replace NaN values with None
            df = df.where(pd.notnull(df), None)
            
            # Convert DataFrame to list of dictionaries
            records = df.to_dict('records')
            
            return {
                'success': True,
                'data': records,
                'total_rows': len(records)
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Error reading file: {str(e)}'}
    
    @staticmethod
    def get_required_columns():
        """Get list of required columns for import"""
        return [
            'panchayat_name',
            'beneficiary_name'
        ]
    
    @staticmethod
    def get_optional_columns():
        """Get list of optional columns for import"""
        return [
            'village_name',
            'registration_number',
            'father_name',
            'mother_name',
            'category',
            'priority',
            'schema_code',
            'bank_name',
            'branch_name',
            'ifsc_code',
            'bank_account_no',
            'sanction_no',
            'amount_released',
            'installment',
            'credit_date',
            'house_status',
            'inspection_date',
            'department_name',
            'scheme_name'
        ]
    
    @staticmethod
    def validate_columns(data):
        """Validate if required columns are present"""
        try:
            if not data:
                return {'success': False, 'message': 'No data found in file'}
            
            # Get column names from first row
            columns = [str(k).strip().lower() for k in list(data[0].keys())] if data else []
            required_columns = BulkImport.get_required_columns()
            
            # Support aliases if users used alternate headers
            aliases = {
                'panchayat_name': ['panchayat', 'panchayatname'],
                'beneficiary_name': ['beneficiary', 'beneficiaryname']
            }
            
            # Rename keys in data rows if alias found
            for req in required_columns:
                if req not in columns:
                    for alias in aliases.get(req, []):
                        if alias in columns:
                            # rename key in each row
                            for row in data:
                                if alias in row and req not in row:
                                    row[req] = row.pop(alias)
                            # update columns list
                            columns = [req if c == alias else c for c in columns]
                            break
            
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                return {
                    'success': False,
                    'message': f'Missing required columns: {", ".join(missing_columns)}'
                }
            
            return {
                'success': True,
                'columns': columns,
                'required_columns': required_columns,
                'optional_columns': BulkImport.get_optional_columns()
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Error validating columns: {str(e)}'}
    
    @staticmethod
    def validate_row_data(row_data, row_number, mongo=None):
        """Validate individual row data"""
        errors = []
        warnings = []
        
        try:
            # Required field validations
            if not row_data.get('panchayat_name'):
                errors.append(f'Row {row_number}: Panchayat name is required')
            
            if not row_data.get('beneficiary_name'):
                errors.append(f'Row {row_number}: Beneficiary name is required')
            
            # Data type validations - only validate if value exists and is not empty
            priority_val = row_data.get('priority')
            if priority_val is not None and str(priority_val).strip() != '':
                # Accept text priorities or numbers
                if isinstance(priority_val, str):
                    priority_map = {
                        'high': 1, 'urgent': 1, 'critical': 1,
                        'medium': 2, 'normal': 2, 'standard': 2,
                        'low': 3, 'routine': 3, 'basic': 3
                    }
                    if priority_val.strip().lower() not in priority_map and not BulkImport._is_numeric_like(priority_val):
                        errors.append(f'Row {row_number}: Priority must be a number or text (High/Medium/Low) (found: "{priority_val}")')
                elif not BulkImport._is_numeric_like(priority_val):
                    errors.append(f'Row {row_number}: Priority must be a number or text (High/Medium/Low) (found: "{priority_val}")')
            
            amount_val = row_data.get('amount_released')
            if amount_val is not None and str(amount_val).strip() != '':
                if not BulkImport._is_numeric_like(amount_val):
                    errors.append(f'Row {row_number}: Amount released must be a number (found: "{amount_val}")')
            
            installment_val = row_data.get('installment')
            if installment_val is not None and str(installment_val).strip() != '':
                if not BulkImport._is_numeric_like(installment_val):
                    errors.append(f'Row {row_number}: Installment must be a number (found: "{installment_val}")')
            
            # Date validations
            date_fields = ['credit_date', 'inspection_date']
            for field in date_fields:
                if row_data.get(field):
                    try:
                        if isinstance(row_data[field], str):
                            pd.to_datetime(row_data[field])
                    except:
                        errors.append(f'Row {row_number}: {field} has invalid date format')
            
            # Check for duplicate registration number (if provided)
            if mongo and row_data.get('registration_number'):
                existing = mongo.db.panchayat_records.find_one({
                    'registration_number': row_data['registration_number'],
                    'is_active': True
                })
                if existing:
                    warnings.append(f'Row {row_number}: Registration number {row_data["registration_number"]} already exists')
            
            return {
                'success': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f'Row {row_number}: Validation error - {str(e)}'],
                'warnings': []
            }
    
    @staticmethod
    def resolve_department_and_scheme(mongo, row_data):
        """Resolve department and scheme IDs from names"""
        try:
            department_id = None
            scheme_id = None
            
            # Resolve department
            if row_data.get('department_name'):
                department = mongo.db.departments.find_one({
                    'name': {'$regex': f'^{row_data["department_name"]}$', '$options': 'i'},
                    'is_active': True
                })
                if department:
                    department_id = department['_id']
            
            # Resolve scheme
            if row_data.get('scheme_name'):
                scheme_query = {
                    'name': {'$regex': f'^{row_data["scheme_name"]}$', '$options': 'i'},
                    'is_active': True
                }
                if department_id:
                    scheme_query['department_id'] = department_id
                
                scheme = mongo.db.schemes.find_one(scheme_query)
                if scheme:
                    scheme_id = scheme['_id']
                    # If department wasn't resolved but scheme was found, use scheme's department
                    if not department_id:
                        department_id = scheme['department_id']
            
            return {
                'success': True,
                'department_id': department_id,
                'scheme_id': scheme_id
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error resolving department/scheme: {str(e)}'
            }
    
    @staticmethod
    def process_import(mongo, file_data, user_id, username, skip_duplicates=False, update_duplicates=False):
        """Process bulk import of records"""
        try:
            # Validate file format
            format_validation = BulkImport.validate_file_format(file_data)
            if not format_validation['success']:
                return format_validation
            
            # Read file data
            read_result = BulkImport.read_file_data(file_data)
            if not read_result['success']:
                return read_result
            
            data = read_result['data']
            
            # Validate columns
            column_validation = BulkImport.validate_columns(data)
            if not column_validation['success']:
                return column_validation
            
            # Process each row
            successful_imports = 0
            failed_imports = 0
            warnings = []
            errors = []
            
            for index, row in enumerate(data, 1):
                try:
                    # Validate row data
                    row_validation = BulkImport.validate_row_data(row, index, mongo)
                    
                    if not row_validation['success']:
                        failed_imports += 1
                        errors.extend(row_validation['errors'])
                        continue
                    
                    # Add warnings to collection
                    if row_validation['warnings']:
                        warnings.extend(row_validation['warnings'])
                        
                        # Skip if duplicate and skip_duplicates is True
                        if skip_duplicates and any('already exists' in w for w in row_validation['warnings']):
                            continue
                    
                    # Resolve department and scheme
                    resolution = BulkImport.resolve_department_and_scheme(mongo, row)
                    if not resolution['success']:
                        failed_imports += 1
                        errors.append(f'Row {index}: {resolution["message"]}')
                        continue
                    
                    # Prepare record data
                    record_data = {
                        'panchayat_name': row.get('panchayat_name'),
                        'village_name': row.get('village_name'),
                        'registration_number': row.get('registration_number'),
                        'beneficiary_name': row.get('beneficiary_name'),
                        'father_name': row.get('father_name'),
                        'mother_name': row.get('mother_name'),
                        'category': row.get('category'),
                        'priority': BulkImport._to_int(row.get('priority'), default=0),
                        'schema_code': row.get('schema_code'),
                        'bank_name': row.get('bank_name'),
                        'branch_name': row.get('branch_name'),
                        'ifsc_code': row.get('ifsc_code'),
                        'bank_account_no': row.get('bank_account_no'),
                        'sanction_no': row.get('sanction_no'),
                        'amount_released': BulkImport._to_float(row.get('amount_released'), default=0.0),
                        'installment': BulkImport._to_int(row.get('installment'), default=0),
                        'house_status': row.get('house_status'),
                        'department_id': resolution['department_id'],
                        'scheme_id': resolution['scheme_id']
                    }
                    
                    # Handle dates
                    if row.get('credit_date'):
                        try:
                            record_data['credit_date'] = pd.to_datetime(row['credit_date']).to_pydatetime()
                        except:
                            pass
                    
                    if row.get('inspection_date'):
                        try:
                            record_data['inspection_date'] = pd.to_datetime(row['inspection_date']).to_pydatetime()
                        except:
                            pass
                    
                    # Handle duplicate records
                    if update_duplicates and row.get('registration_number'):
                        existing = mongo.db.panchayat_records.find_one({
                            'registration_number': row['registration_number'],
                            'is_active': True
                        })
                        
                        if existing:
                            # Update existing record - PanchayatRecord is now imported at top
                            update_result = PanchayatRecord.update_record(
                                mongo, str(existing['_id']), record_data, username
                            )
                            if update_result:
                                successful_imports += 1
                            else:
                                failed_imports += 1
                                errors.append(f'Row {index}: Failed to update existing record')
                            continue
                    
                    # Create new record - PanchayatRecord is now imported at top
                    result = PanchayatRecord.create_record(mongo, record_data, username)
                    
                    if result['success']:
                        successful_imports += 1
                    else:
                        failed_imports += 1
                        errors.append(f'Row {index}: {result["message"]}')
                
                except Exception as e:
                    failed_imports += 1
                    errors.append(f'Row {index}: Error processing row - {str(e)}')
            
            # Log bulk import action
            AuditLog.log_action(
                mongo=mongo,
                username=username,
                model_type='bulk_import',
                model_id='bulk_import',
                action='bulk_import',
                changed_fields={
                    'total_rows': len(data),
                    'successful_imports': successful_imports,
                    'failed_imports': failed_imports,
                    'file_name': file_data.filename
                }
            )
            
            return {
                'success': True,
                'message': f'Import completed. {successful_imports} records imported, {failed_imports} failed.',
                'successful_imports': successful_imports,
                'failed_imports': failed_imports,
                'warnings': warnings,
                'errors': errors,
                'total_rows': len(data)
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Error processing import: {str(e)}'}
    
    @staticmethod
    def get_sample_template():
        """Generate sample template data for download"""
        return {
            'panchayat_name': 'Sample Panchayat',
            'village_name': 'Sample Village',
            'registration_number': 'REG001',
            'beneficiary_name': 'John Doe',
            'father_name': 'Father Name',
            'mother_name': 'Mother Name',
            'category': 'General',
            'priority': 1,
            'schema_code': 'SCH001',
            'bank_name': 'Sample Bank',
            'branch_name': 'Sample Branch',
            'ifsc_code': 'SBIN0001234',
            'bank_account_no': '1234567890',
            'sanction_no': 'SAN001',
            'amount_released': 50000.0,
            'installment': 1,
            'credit_date': '2024-01-15',
            'house_status': 'Completed',
            'inspection_date': '2024-01-20',
            'department_name': 'Sample Department',
            'scheme_name': 'Sample Scheme'
        }