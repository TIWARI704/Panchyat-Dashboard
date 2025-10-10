"""
Bulk Import Routes

This module defines routes for bulk import functionality.
"""

from flask import Blueprint, render_template, request, jsonify, session, make_response, redirect, url_for, flash
from models.bulk_import import BulkImport
from models.login import User
from routes.login import login_required, admin_required, superadmin_required
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
    
    # render the template in the admin subfolder
    return render_template('admin/bulk_import.html')

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
        
        # Process import
        result = BulkImport.process_import(
            mongo=mongo,
            file_data=file,
            user_id=session['user_id'],
            username=session.get('username', 'Unknown'),
            skip_duplicates=skip_duplicates,
            update_duplicates=update_duplicates
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
        
        # Validate file format
        format_validation = BulkImport.validate_file_format(file)
        if not format_validation['success']:
            return jsonify(format_validation), 400
        
        # Read and validate data
        read_result = BulkImport.read_file_data(file)
        if not read_result['success']:
            return jsonify(read_result), 400
        
        data = read_result['data']
        
        # Validate columns
        column_validation = BulkImport.validate_columns(data)
        if not column_validation['success']:
            return jsonify(column_validation), 400
        
        # Validate sample rows (first 10)
        sample_errors = []
        sample_warnings = []
        
        for index, row in enumerate(data[:10], 1):
            row_validation = BulkImport.validate_row_data(row, index, mongo)
            sample_errors.extend(row_validation.get('errors', []))
            sample_warnings.extend(row_validation.get('warnings', []))
        
        return jsonify({
            'success': True,
            'total_rows': len(data),
            'columns': column_validation['columns'],
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
        # Create sample data
        sample_data = [BulkImport.get_sample_template()]
        
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
        response.headers['Content-Disposition'] = 'attachment; filename=panchayat_records_import_template.xlsx'
        
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error generating template: {str(e)}'}), 500