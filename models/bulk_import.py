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
        """Get list of required columns for import - now flexible based on scheme"""
        return []  # No hardcoded required columns - will be determined by scheme
    
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
    def validate_columns(data, scheme_id=None, mongo=None):
        """Validate columns against the selected scheme"""
        try:
            if not data:
                return {'success': False, 'message': 'No data found in file'}
            
            # Get column names from first row
            csv_columns = [str(k).strip().lower() for k in list(data[0].keys())] if data else []
            
            if not scheme_id or not mongo:
                # If no scheme specified, just return the columns
                return {
                    'success': True,
                    'columns': csv_columns,
                    'required_columns': [],
                    'optional_columns': csv_columns
                }
            
            # Get scheme details
            scheme = mongo.db.schemes.find_one({'_id': ObjectId(scheme_id)})
            if not scheme:
                return {'success': False, 'message': 'Invalid scheme selected'}
            
            # Get expected columns from scheme attributes
            scheme_attributes = scheme.get('attributes', [])
            expected_columns = [attr.get('name').lower() for attr in scheme_attributes]
            
            # Check for missing columns
            missing_columns = [col for col in expected_columns if col not in csv_columns]
            
            # Check for extra columns
            extra_columns = [col for col in csv_columns if col not in expected_columns]
            
            errors = []
            if missing_columns:
                errors.append(f'Missing required columns: {", ".join(missing_columns)}')
            
            if extra_columns:
                errors.append(f'Extra columns found (will be ignored): {", ".join(extra_columns)}')
            
            if errors:
                return {
                    'success': False,
                    'message': '; '.join(errors),
                    'missing_columns': missing_columns,
                    'extra_columns': extra_columns,
                    'expected_columns': expected_columns,
                    'csv_columns': csv_columns
                }
            
            return {
                'success': True,
                'columns': csv_columns,
                'expected_columns': expected_columns,
                'message': f'All {len(expected_columns)} required columns found'
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Error validating columns: {str(e)}'}
    
    @staticmethod
    def validate_row_data(row_data, row_number, mongo=None, scheme_id=None):
        """Validate individual row data"""
        errors = []
        warnings = []
        
        try:
            # No hardcoded required field validations - will be based on scheme
            # Only validate data types for fields that exist
            
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
    def process_import(mongo, file_data, user_id, username, skip_duplicates=False, update_duplicates=False, scheme_id=None):
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
            
            # Validate columns against the selected scheme
            column_validation = BulkImport.validate_columns(data, scheme_id, mongo)
            if not column_validation['success']:
                return column_validation
            
            # Process each row
            successful_imports = 0
            failed_imports = 0
            warnings = []
            errors = []
            
            for index, row in enumerate(data, 1):
                try:
                    # Use provided scheme_id or resolve from row data
                    if scheme_id:
                        # Use the scheme_id provided from the bulk import page
                        scheme = mongo.db.schemes.find_one({'_id': ObjectId(scheme_id)})
                        if not scheme:
                            failed_imports += 1
                            errors.append(f'Row {index}: Invalid scheme ID')
                            continue
                        
                        resolution = {
                            'success': True,
                            'department_id': scheme['department_id'],
                            'scheme_id': ObjectId(scheme_id)
                        }
                    else:
                        # Fallback to resolving from row data
                        resolution = BulkImport.resolve_department_and_scheme(mongo, row)
                        if not resolution['success']:
                            failed_imports += 1
                            errors.append(f'Row {index}: {resolution["message"]}')
                            continue
                    
                    # Validate row data with scheme context
                    row_validation = BulkImport.validate_row_data(row, index, mongo, resolution.get('scheme_id'))
                    
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
                    
                    # Get scheme attributes to determine which fields go into custom_data
                    scheme_attributes = []
                    if resolution['scheme_id']:
                        scheme = mongo.db.schemes.find_one({'_id': resolution['scheme_id']})
                        if scheme:
                            scheme_attributes = scheme.get('attributes', [])
                    
                    # Define standard fields that should NOT go into custom_data
                    standard_fields = {
                        'panchayat_name', 'village_name', 'registration_number', 'beneficiary_name',
                        'father_name', 'mother_name', 'category', 'priority', 'schema_code',
                        'bank_name', 'branch_name', 'ifsc_code', 'bank_account_no', 'sanction_no',
                        'amount_released', 'installment', 'credit_date', 'house_status', 'inspection_date',
                        'department_id', 'scheme_id', 'department_name', 'scheme_name'
                    }
                    
                    # Get scheme attribute field names
                    scheme_field_names = {attr.get('name') for attr in scheme_attributes}
                    
                    # Get department and scheme names for easier filtering
                    department_name = None
                    scheme_name = None
                    if resolution['department_id']:
                        department = mongo.db.departments.find_one({'_id': resolution['department_id']})
                        department_name = department['name'] if department else None
                    if resolution['scheme_id']:
                        scheme = mongo.db.schemes.find_one({'_id': resolution['scheme_id']})
                        scheme_name = scheme['name'] if scheme else None
                    
                    # Prepare record data with only base fields at root level
                    record_data = {
                        'department_id': resolution['department_id'],
                        'scheme_id': resolution['scheme_id']
                    }
                    
                    # Process ONLY fields that are defined in the scheme attributes
                    custom_data = {}
                    for key, value in row.items():
                        # Skip empty values
                        if not value or str(value).strip() == '':
                            continue
                        
                        # Only process fields that are defined in the scheme attributes
                        attr_def = next((attr for attr in scheme_attributes if attr.get('name').lower() == key.lower()), None)
                        if attr_def:
                            data_type = attr_def.get('type', 'string')
                            field_name = attr_def.get('name')  # Use the exact field name from scheme
                            try:
                                if data_type == 'int':
                                    custom_data[field_name] = BulkImport._to_int(value, default=0)
                                elif data_type == 'float':
                                    custom_data[field_name] = BulkImport._to_float(value, default=0.0)
                                elif data_type == 'date':
                                    custom_data[field_name] = pd.to_datetime(value).to_pydatetime()
                                elif data_type == 'boolean':
                                    custom_data[field_name] = str(value).lower() in ['true', '1', 'yes', 'y']
                                else:  # string, enum, etc.
                                    custom_data[field_name] = str(value)
                            except Exception:
                                # If conversion fails, store as string
                                custom_data[field_name] = str(value)
                        # Skip fields that are not defined in the scheme attributes
                    
                    # Add custom_data to record_data
                    record_data['custom_data'] = custom_data
                    
                    # Note: Duplicate handling is not applicable since we don't have unique identifiers
                    # in the custom data structure. Each import creates a new record.
                    
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
            'scheme_name': 'Sample Scheme',
            # Example custom fields (these will go into custom_data)
            'taluka': 'Sample Taluka',
            'block': 'Sample Block',
            'aadhar_number': '123456789012',
            'mobile_number': '9876543210',
            'remarks': 'Sample remarks'
        }
    
    @staticmethod
    def get_dynamic_template(mongo, scheme_id):
        """Generate dynamic template based on scheme attributes - ONLY custom scheme fields"""
        try:
            # Get scheme details
            scheme = mongo.db.schemes.find_one({'_id': ObjectId(scheme_id)})
            if not scheme:
                return {}
            
            # Start with empty template - only custom scheme fields
            template = {}
            
            # Add ONLY scheme-specific custom fields
            scheme_attributes = scheme.get('attributes', [])
            for attr in scheme_attributes:
                field_name = attr.get('name')
                field_type = attr.get('type', 'string')
                field_label = attr.get('label', field_name)
                required = attr.get('required', False)
                
                # Generate sample value based on field type
                if field_type == 'int':
                    sample_value = 100
                elif field_type == 'float':
                    sample_value = 100.50
                elif field_type == 'date':
                    sample_value = '2024-01-15'
                elif field_type == 'boolean':
                    sample_value = 'true'
                elif field_type == 'enum' and attr.get('options'):
                    sample_value = attr['options'][0] if attr['options'] else 'Sample'
                else:  # string
                    # Generate more realistic sample data based on field name
                    field_lower = field_name.lower()
                    if 'name' in field_lower:
                        sample_value = 'Sample Name'
                    elif 'address' in field_lower:
                        sample_value = 'Sample Address'
                    elif 'phone' in field_lower or 'mobile' in field_lower:
                        sample_value = '9876543210'
                    elif 'email' in field_lower:
                        sample_value = 'sample@email.com'
                    elif 'id' in field_lower or 'number' in field_lower:
                        sample_value = 'SAMPLE001'
                    elif 'amount' in field_lower or 'cost' in field_lower or 'price' in field_lower:
                        sample_value = '1000.00'
                    elif 'age' in field_lower:
                        sample_value = '25'
                    elif 'date' in field_lower:
                        sample_value = '2024-01-15'
                    else:
                        sample_value = f'Sample {field_label}'
                
                template[field_name] = sample_value
            
            return template
            
        except Exception as e:
            # Return empty template if there's an error
            return {}