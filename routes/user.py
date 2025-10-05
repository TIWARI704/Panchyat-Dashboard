"""
User Routes Module

This module contains all user-specific routes for the Panchayat Management System.
It handles user dashboard, record management, and scheme-based access control.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models.admin import PanchayatRecord
from models.login import User
from models.department import Department
from models.scheme import Scheme
from routes.login import login_required
from datetime import datetime
from bson import ObjectId

# Initialize user blueprint
user_bp = Blueprint('user', __name__)
mongo = None

def intialize_user(db):
    """Initialize MongoDB connection for user routes"""
    global mongo
    mongo = db

@user_bp.route("/dashboard")
@login_required
def dashboard():
    """
    User Dashboard
    
    Displays user-specific statistics and analytics based on their department
    and scheme access permissions.
    """
    try:
        # Get user access information
        user_id = session.get('user_id')
        user_access = User.get_user_access_info(mongo, user_id)
        
        if not user_access:
            flash('Error loading user access information.', 'error')
            return render_template("user/dashboard.html", 
                                 records_count=0, total_amount=0,
                                 category_stats=[], panchayat_stats=[])
        
        # Get basic statistics for user dashboard based on their access
        department_ids = user_access.get('department_access', [])
        scheme_ids = user_access.get('scheme_access', [])

        dept_filter = None if 'all' in department_ids else department_ids
        scheme_filter = None if 'all' in scheme_ids else scheme_ids
        
        stats = PanchayatRecord.get_statistics(mongo, dept_filter, scheme_filter)
        
        return render_template("user/dashboard.html", 
                             records_count=stats['total_records'],
                             total_amount=stats['total_amount'],
                             category_stats=stats['category_stats'],
                             panchayat_stats=stats['panchayat_stats'])
    except Exception as e:
        flash('An error occurred while loading the dashboard.', 'error')
        return render_template("user/dashboard.html", 
                             records_count=0, total_amount=0,
                             category_stats=[], panchayat_stats=[])

@user_bp.route('/add-record', methods=['GET', 'POST'])
@login_required
def add_record():
    """
    Add New Record
    
    Allows users to add new records to schemes they have access to.
    Form fields are dynamically generated based on the selected scheme's attributes.
    """
    # Get user access information
    user_id = session.get('user_id')
    user_access = User.get_user_access_info(mongo, user_id)
    
    if not user_access:
        flash('Error loading user access information.', 'error')
        return redirect(url_for('user.dashboard'))
    
    # Get accessible schemes for the user
    accessible_schemes = []
    scheme_access = user_access.get('scheme_access', [])

    if 'all' in scheme_access:
        schemes_result = Scheme.get_all_schemes(mongo,active_only=True)
        if schemes_result['success']:
            accessible_schemes = schemes_result['schemes']

    elif scheme_access:
        schemes_result = Scheme.get_schemes_by_ids(mongo, scheme_access)
        if schemes_result['success']:
            accessible_schemes = schemes_result['schemes']
    
    if request.method == 'POST':
        try:
            # Get scheme_id from form
            scheme_id = request.form.get('scheme_id')
            if not scheme_id:
                flash('Please select a scheme.', 'error')
                return render_template('user/add_record.html', schemes=accessible_schemes)
            
            # Validate user has access to this scheme
            if not User.can_access_scheme(mongo, user_id, scheme_id):
                flash('You do not have access to this scheme.', 'error')
                return render_template('user/add_record.html', schemes=accessible_schemes)
            
            # Get scheme details to get department_id
            scheme_result = Scheme.get_scheme_by_id(mongo, scheme_id)
            if not scheme_result['success']:
                flash('Invalid scheme selected.', 'error')
                return render_template('user/add_record.html', schemes=accessible_schemes)
            
            scheme = scheme_result['scheme']
            department_id = scheme['department_id']
            
            # Get scheme attributes to build custom data
            scheme_attributes = scheme.get('attributes', [])
            custom_data = {}
            
            # Process each attribute from the scheme
            for attr in scheme_attributes:
                field_name = attr.get('name')
                data_type = attr.get('type', 'string')
                field_value = request.form.get(field_name)
                
                if field_value:
                    # Convert data types based on scheme definition
                    if data_type == 'int':
                        try:
                            custom_data[field_name] = int(field_value)
                        except ValueError:
                            custom_data[field_name] = 0
                    elif data_type == 'float':
                        try:
                            custom_data[field_name] = float(field_value)
                        except ValueError:
                            custom_data[field_name] = 0.0
                    elif data_type == 'date':
                        try:
                            custom_data[field_name] = datetime.strptime(field_value, '%Y-%m-%d')
                        except ValueError:
                            custom_data[field_name] = None
                    elif data_type == 'boolean':
                        custom_data[field_name] = field_value == 'true'
                    else:  # string, enum, etc.
                        custom_data[field_name] = field_value
                else:
                    # Set default values based on data type
                    if data_type == 'int':
                        custom_data[field_name] = 0
                    elif data_type == 'float':
                        custom_data[field_name] = 0.0
                    elif data_type == 'date':
                        custom_data[field_name] = None
                    elif data_type == 'boolean':
                        custom_data[field_name] = False
                    else:
                        custom_data[field_name] = ''
            
            # Prepare record data with scheme and department info
            record_data = {
                'department_id': department_id,
                'scheme_id': scheme_id,
                'custom_data': custom_data
            }

            # Use PanchayatRecord model to create record with username
            result = PanchayatRecord.create_record(
                mongo, 
                record_data, 
                created_by=session.get('username')
            )
            
            if result['success']:
                flash('Record added successfully!', 'success')
                return redirect(url_for('user.dashboard'))
            else:
                flash(result['message'], 'error')
            
        except Exception as e:
            flash('An error occurred while adding the record.', 'error')

    return render_template('user/add_record.html', schemes=accessible_schemes)

@user_bp.route('/view-records')
@login_required
def view_records():
    """View records based on user's department and scheme access with pagination and search"""
    try:
        page = int(request.args.get('page', 1))
        search = request.args.get('search', '').strip()
        per_page = 10
        
        user_id = session.get('user_id')
        
        # Get user access information
        user_access = User.get_user_access_info(mongo, user_id)
        
        if not user_access:
            flash('Error loading user access information.', 'error')
            return render_template(
                'user/view_records.html',
                records=[],
                total_records=0,
                page=1,
                total_pages=0,
                search=''
            )
        
        # Build base query
        base_conditions = [{'is_active': True}]
        
        # Apply department and scheme access filters
        department_access = user_access.get('department_access', [])
        scheme_access = user_access.get('scheme_access', [])
        
        # Check if user has all access
        has_all_access = user_access.get('has_all_access', False) or user_access.get('is_superadmin', False)
        
        if not has_all_access:
            # Apply department filter if user doesn't have 'all' access
            if department_access and 'all' not in department_access:
                try:
                    valid_dept_ids = [ObjectId(dep_id) for dep_id in department_access if dep_id != 'all']
                    if valid_dept_ids:
                        base_conditions.append({'department_id': {'$in': valid_dept_ids}})
                    else:
                        return render_template(
                            'user/view_records.html',
                            records=[],
                            total_records=0,
                            page=1,
                            total_pages=0,
                            search=''
                        )
                except Exception as e:
                    print(f"ERROR USER_VIEW_RECORDS - Converting department IDs: {e}")
                    flash('Error loading records: Invalid department access', 'error')
                    return render_template(
                        'user/view_records.html',
                        records=[],
                        total_records=0,
                        page=1,
                        total_pages=0,
                        search=''
                    )
            
            # Apply scheme filter if user doesn't have 'all' access
            if scheme_access and 'all' not in scheme_access:
                try:
                    valid_scheme_ids = [ObjectId(scheme_id) for scheme_id in scheme_access if scheme_id != 'all']
                    if valid_scheme_ids:
                        base_conditions.append({'scheme_id': {'$in': valid_scheme_ids}})
                    else:
                        return render_template(
                            'user/view_records.html',
                            records=[],
                            total_records=0,
                            page=1,
                            total_pages=0,
                            search=''
                        )
                except Exception as e:
                    print(f"ERROR USER_VIEW_RECORDS - Converting scheme IDs: {e}")
                    flash('Error loading records: Invalid scheme access', 'error')
                    return render_template(
                        'user/view_records.html',
                        records=[],
                        total_records=0,
                        page=1,
                        total_pages=0,
                        search=''
                    )
        
        # Add search conditions if search query exists
        if search:
            search_regex = {'$regex': search, '$options': 'i'}
            
            # Get all possible custom_data field names from schemes
            # This ensures we search in fields that actually exist
            all_schemes = list(mongo.db.schemes.find({'is_active': True}, {'attributes': 1}))
            custom_field_names = set()
            
            for scheme in all_schemes:
                for attr in scheme.get('attributes', []):
                    field_name = attr.get('name')
                    if field_name:
                        custom_field_names.add(f'custom_data.{field_name}')
            
            # Build search conditions
            search_conditions = [
                {'created_by': search_regex},
            ]
            
            # Add all custom_data fields dynamically
            for field_name in custom_field_names:
                search_conditions.append({field_name: search_regex})
            
            # Add search condition to base conditions
            base_conditions.append({'$or': search_conditions})
        
        # Build final query
        if len(base_conditions) == 1:
            query = base_conditions[0]
        else:
            query = {'$and': base_conditions}
        
        # Calculate pagination
        skip = (page - 1) * per_page
        
        # Get records with department and scheme names using aggregation
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
        
        # Get total count for the search
        total_records = mongo.db.panchayat_records.count_documents(query)
        total_pages = (total_records + per_page - 1) // per_page
        
        # Convert ObjectId to string for template
        for record in records:
            if '_id' in record and isinstance(record['_id'], ObjectId):
                record['_id'] = {'$oid': str(record['_id'])}
            if 'department_id' in record and isinstance(record['department_id'], ObjectId):
                record['department_id'] = str(record['department_id'])
            if 'scheme_id' in record and isinstance(record['scheme_id'], ObjectId):
                record['scheme_id'] = str(record['scheme_id'])
            # Format created_at for display
            if 'created_at' in record and record['created_at']:
                record['created_at'] = record['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return render_template(
            'user/view_records.html',
            records=records,
            total_records=total_records,
            page=page,
            total_pages=total_pages,
            search=search
        )
        
    except Exception as e:
        print(f"ERROR in user view_records: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error loading records: {str(e)}', 'error')
        return render_template(
            'user/view_records.html',
            records=[],
            total_records=0,
            page=1,
            total_pages=0,
            search=''
        )

@user_bp.route('/api/scheme-form-fields/<scheme_id>')
@login_required
def get_scheme_form_fields(scheme_id):
    """
    Get Scheme Form Fields API
    
    Returns the form fields configuration for a specific scheme.
    Used by the frontend to dynamically generate form inputs.
    """
    try:
        # Validate user has access to this scheme
        user_id = session.get('user_id')
        if not User.can_access_scheme(mongo, user_id, scheme_id):
            return {'success': False, 'message': 'Access denied to this scheme'}
        
        # Get scheme details
        scheme_result = Scheme.get_scheme_by_id(mongo, scheme_id)
        if not scheme_result['success']:
            return {'success': False, 'message': 'Scheme not found'}
        
        scheme = scheme_result['scheme']
        attributes = scheme.get('attributes', [])
        
        # Convert attributes to form fields
        form_fields = []
        for attr in attributes:
            field = {
                'name': attr.get('name', ''),
                'label': attr.get('label', ''),
                'type': attr.get('type', 'string'),
                'required': attr.get('required', False),
                'options': attr.get('options', []) if attr.get('type') == 'enum' else []
            }
            form_fields.append(field)
        
        return jsonify({
            'success': True,
            'scheme_name': scheme['name'],
            'department_name': scheme.get('department_name', 'Unknown'),
            'form_fields': form_fields
        })
        
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}'}

@user_bp.route('/api/record-details/<record_id>')
@login_required
def get_record_details(record_id):
    """API endpoint to get details of a specific record"""
    try:
        from bson import ObjectId
        
        username = session.get('username')
        
        # Get the record - only user's own records
        record = mongo.db.panchayat_records.find_one({
            '_id': ObjectId(record_id),
            'created_by': username,
            'is_active': True
        })
        
        if not record:
            return jsonify({
                'success': False,
                'message': 'Record not found or access denied'
            })
        
        # Get department and scheme info
        dept = mongo.db.departments.find_one({'_id': record.get('department_id')})
        scheme = mongo.db.schemes.find_one({'_id': record.get('scheme_id')})
        
        # Format the response
        record_data = {
            'scheme_name': scheme['name'] if scheme else 'Unknown',
            'department_name': dept['name'] if dept else 'Unknown',
            'created_by': record.get('created_by', 'Unknown'),
            'created_at': record.get('created_at').strftime('%d-%m-%Y %H:%M') if record.get('created_at') else '-',
            'custom_data': record.get('custom_data', {})
        }
        
        return jsonify({
            'success': True,
            'record': record_data
        })
        
    except Exception as e:
        print(f"ERROR in get_record_details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error fetching record details: {str(e)}'
        })

@user_bp.route('/api/user-filter-data')
@login_required
def get_user_filter_data():
    """Get user's accessible schemes for filter dropdown"""
    try:
        user_id = session.get('user_id')
        user_access = User.get_user_access_info(mongo, user_id)
        
        if not user_access:
            return jsonify({'success': False, 'message': 'User access not found'})
        
        scheme_access = user_access.get('scheme_access', [])
        
        # Get schemes user has access to
        if 'all' in scheme_access:
            schemes_result = Scheme.get_all_schemes(mongo, active_only=True)
        else:
            schemes_result = Scheme.get_schemes_by_ids(mongo, scheme_access)
        
        if not schemes_result['success']:
            return jsonify({'success': False, 'message': 'Error loading schemes'})
        
        schemes = schemes_result['schemes']
        
        # Convert ObjectId to string
        for scheme in schemes:
            if '_id' in scheme:
                scheme['_id'] = {'$oid': str(scheme['_id'])}
            if 'department_id' in scheme:
                scheme['department_id'] = {'$oid': str(scheme['department_id'])}
        
        return jsonify({
            'success': True,
            'schemes': schemes
        })
        
    except Exception as e:
        print(f"ERROR in get_user_filter_data: {e}")
        return jsonify({'success': False, 'message': str(e)})

@user_bp.route('/api/dashboard-data')
@login_required
def get_user_dashboard_data():
    """Get dashboard data for user based on filters"""
    try:
        user_id = session.get('user_id')
        user_access = User.get_user_access_info(mongo, user_id)
        
        if not user_access:
            return jsonify({'success': False, 'message': 'User access not found'})
        
        # Get filter parameters
        scheme_id = request.args.get('scheme_id')
        taluka = request.args.get('taluka')
        
        # Build query
        query = {'is_active': True}
        
        # Apply user's access restrictions
        department_access = user_access.get('department_access', [])
        scheme_access = user_access.get('scheme_access', [])
        
        has_all_access = user_access.get('has_all_access', False)
        
        if not has_all_access:
            if department_access and 'all' not in department_access:
                dept_ids = [ObjectId(dep_id) for dep_id in department_access if dep_id != 'all']
                if dept_ids:
                    query['department_id'] = {'$in': dept_ids}
            
            if scheme_access and 'all' not in scheme_access:
                scheme_ids = [ObjectId(s_id) for s_id in scheme_access if s_id != 'all']
                if scheme_ids:
                    query['scheme_id'] = {'$in': scheme_ids}
        
        # Apply additional filters
        if scheme_id:
            query['scheme_id'] = ObjectId(scheme_id)
        
        if taluka:
            query['custom_data.taluka'] = taluka
        
        # Get records with aggregation
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
            {'$limit': 1000}  # Limit for performance
        ]
        
        records = list(mongo.db.panchayat_records.aggregate(pipeline))
        
        # Convert ObjectId to string
        for record in records:
            if '_id' in record:
                record['_id'] = str(record['_id'])
            if 'department_id' in record:
                record['department_id'] = str(record['department_id'])
            if 'scheme_id' in record:
                record['scheme_id'] = str(record['scheme_id'])
            if 'created_at' in record:
                record['created_at'] = record['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'records': records
        })
        
    except Exception as e:
        print(f"ERROR in get_user_dashboard_data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})