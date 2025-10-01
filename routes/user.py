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
        
        stats = PanchayatRecord.get_statistics(mongo, department_ids, scheme_ids)
        
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
    if user_access.get('schemes'):
        accessible_schemes = user_access['schemes']
    elif user_access.get('scheme_access'):
        schemes_result = Scheme.get_schemes_by_ids(mongo, user_access['scheme_access'])
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

            # Use PanchayatRecord model to create record
            result = PanchayatRecord.create_record(mongo, record_data, session.get('username'))
            
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
    """
    View Records
    
    Displays records that the user has access to based on their department
    and scheme permissions. Includes pagination and search functionality.
    """
    try:
        # Get user access information
        user_id = session.get('user_id')
        user_access = User.get_user_access_info(mongo, user_id)
        
        if not user_access:
            flash('Error loading user access information.', 'error')
            return render_template('user/view_records.html', records=[], page=1, 
                                 total_records=0, total_pages=0, search='')
        
        page = int(request.args.get('page', 1))
        search = request.args.get('search', '')
        per_page = 10
        
        # Get records based on user's access
        department_ids = user_access.get('department_access', [])
        scheme_ids = user_access.get('scheme_access', [])
        
        result = PanchayatRecord.get_records_by_user_access(mongo, page, per_page, search, department_ids, scheme_ids)
        
        if result['success']:
            return render_template('user/view_records.html', 
                                 records=result['records'],
                                 page=result['page'],
                                 total_records=result['total_records'],
                                 total_pages=result['total_pages'],
                                 search=search)
        else:
            flash('Error loading records', 'error')
            return render_template('user/view_records.html', records=[], page=1, 
                                 total_records=0, total_pages=0, search='')
            
    except Exception as e:
        flash('Error loading records', 'error')
        return render_template('user/view_records.html', records=[], page=1, 
                             total_records=0, total_pages=0, search='')

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
        
        return {
            'success': True,
            'scheme_name': scheme['name'],
            'department_name': scheme.get('department_name', 'Unknown'),
            'form_fields': form_fields
        }
        
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}'}