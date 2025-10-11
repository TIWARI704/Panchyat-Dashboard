"""
Bulk Import Routes

This module defines routes for bulk import functionality.
"""

from flask import Blueprint, render_template, request, jsonify, session, make_response, redirect, url_for, flash
from models.bulk_import import BulkImport
from models.login import User
from routes.login import login_required, admin_required, superadmin_required
from bson import ObjectId
import pandas as pd
import io

bulk_import_bp = Blueprint('bulk_import', __name__)
mongo = None

def intialize_bulk_import(db):
    """Initialize MongoDB connection for admin routes"""
    global mongo
    mongo = db

@bulk_import_bp.route('/bulk-import')
@login_required
@superadmin_required
def bulk_import_page():
    """Render bulk import page"""
    if 'user_id' not in session:
        # use the actual login blueprint endpoint name
        return redirect(url_for('login.login'))
    
    # Check if user has permission to import data
    user = User.get_user_by_id(mongo, session['user_id'])
    if not user or not (user.get('is_admin') or user.get('is_superadmin')):
        flash('You do not have permission to access this page.', 'error')
        # redirect to admin dashboard (adjust if your dashboard endpoint differs)
        return redirect(url_for('admin.dashboard'))
    
    # Get scheme_id from query parameters
    scheme_id = request.args.get('scheme_id')
    
    # Get all available schemes for dropdown
    from models.scheme import Scheme
    schemes_result = Scheme.get_all_schemes(mongo, active_only=True)
    schemes = schemes_result.get('schemes', []) if schemes_result.get('success') else []
    
    # Get selected scheme details if scheme_id is provided
    selected_scheme = None
    if scheme_id:
        scheme_result = Scheme.get_scheme_by_id(mongo, scheme_id)
        if scheme_result.get('success'):
            selected_scheme = scheme_result.get('scheme')
    
    # render the template in the admin subfolder
    return render_template('admin/bulk_import.html', 
                         schemes=schemes, 
                         selected_scheme=selected_scheme,
                         scheme_id=scheme_id)

@bulk_import_bp.route('/api/bulk-import/upload', methods=['POST'])
@login_required
@superadmin_required
def upload_bulk_import():
    """Handle bulk import file upload"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        # Check permissions
        user = User.get_user_by_id(mongo, session['user_id'])
        if not user or not (user.get('is_admin') or user.get('is_superadmin')):
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Get options
        skip_duplicates = request.form.get('skip_duplicates') == 'true'
        update_duplicates = request.form.get('update_duplicates') == 'true'
        scheme_id = request.form.get('scheme_id')
        
        # Process import
        result = BulkImport.process_import(
            mongo=mongo,
            file_data=file,
            user_id=session['user_id'],
            username=session.get('username', 'Unknown'),
            skip_duplicates=skip_duplicates,
            update_duplicates=update_duplicates,
            scheme_id=scheme_id
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error processing upload: {str(e)}'}), 500

@bulk_import_bp.route('/api/bulk-import/validate', methods=['POST'])
@login_required
@superadmin_required
def validate_import_file():
    """Validate import file without importing"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Get scheme_id from form data
        scheme_id = request.form.get('scheme_id')
        if not scheme_id:
            return jsonify({'success': False, 'message': 'Please select a scheme first'}), 400
        
        # Validate file format
        format_validation = BulkImport.validate_file_format(file)
        if not format_validation['success']:
            return jsonify(format_validation), 400
        
        # Read and validate data
        read_result = BulkImport.read_file_data(file)
        if not read_result['success']:
            return jsonify(read_result), 400
        
        data = read_result['data']
        
        # Validate columns against the selected scheme
        column_validation = BulkImport.validate_columns(data, scheme_id, mongo)
        if not column_validation['success']:
            return jsonify(column_validation), 400
        
        # Validate sample rows (first 10)
        sample_errors = []
        sample_warnings = []
        
        for index, row in enumerate(data[:10], 1):
            row_validation = BulkImport.validate_row_data(row, index, mongo, scheme_id)
            sample_errors.extend(row_validation.get('errors', []))
            sample_warnings.extend(row_validation.get('warnings', []))
        
        return jsonify({
            'success': True,
            'total_rows': len(data),
            'columns': column_validation['columns'],
            'expected_columns': column_validation.get('expected_columns', []),
            'sample_errors': sample_errors,
            'sample_warnings': sample_warnings,
            'preview_data': data[:5]  # First 5 rows for preview
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error validating file: {str(e)}'}), 500

@bulk_import_bp.route('/api/bulk-import/template')
@login_required
@superadmin_required
def download_template():
    """Download sample import template"""
    try:
        # Get scheme_id from query parameters
        scheme_id = request.args.get('scheme_id')
        
        # Create sample data
        if scheme_id:
            # Generate dynamic template based on scheme
            sample_data = [BulkImport.get_dynamic_template(mongo, scheme_id)]
            
            # Get scheme name for filename
            scheme = mongo.db.schemes.find_one({'_id': ObjectId(scheme_id)})
            scheme_name = scheme['name'] if scheme else 'Unknown'
            filename = f'import_template_{scheme_name.replace(" ", "_")}.xlsx'
        else:
            # Use default template
            sample_data = [BulkImport.get_sample_template()]
            filename = 'panchayat_records_import_template.xlsx'
        
        # Create DataFrame
        df = pd.DataFrame(sample_data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Import Template')
        
        output.seek(0)
        
        # Create response
        response = make_response(output.read())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error generating template: {str(e)}'}), 500