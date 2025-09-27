from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response
from models.admin import PanchayatRecord
from models.login import User
from routes.login import admin_required, login_required, superadmin_required, can_edit_records
from datetime import datetime
import pandas as pd
import io


admin_bp = Blueprint('admin', __name__)
mongo = None


def intialize_admin(db):
    global mongo
    mongo = db

@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    try:
        # Use PanchayatRecord model for statistics
        stats = PanchayatRecord.get_statistics(mongo)
        users_count = mongo.db.users.count_documents({})
        
        # Additional chart data
        # House status distribution
        status_pipeline = [
            {"$group": {"_id": "$house_status", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        status_stats = list(mongo.db.panchayat_records.aggregate(status_pipeline))
        
        # Monthly trends (last 6 months)
        from datetime import datetime, timedelta
        import calendar
        
        six_months_ago = datetime.now() - timedelta(days=180)
        monthly_pipeline = [
            {"$match": {"created_at": {"$gte": six_months_ago}}},
            {"$group": {
                "_id": {
                    "year": {"$year": "$created_at"},
                    "month": {"$month": "$created_at"}
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}}
        ]
        monthly_stats = list(mongo.db.panchayat_records.aggregate(monthly_pipeline))
        
        # Format monthly data for chart
        monthly_labels = []
        monthly_data = []
        for stat in monthly_stats:
            month_name = calendar.month_abbr[stat['_id']['month']]
            monthly_labels.append(month_name)
            monthly_data.append(stat['count'])
        
        return render_template("admin/dashboard.html", 
                             users_count=users_count,
                             records_count=stats['total_records'],
                             total_amount=stats['total_amount'],
                             category_stats=stats['category_stats'],
                             panchayat_stats=stats['panchayat_stats'],
                             status_stats=status_stats,
                             monthly_labels=monthly_labels,
                             monthly_data=monthly_data)
                             
    except Exception as e:
        flash('An error occurred while loading the dashboard.', 'error')
        print(f"Dashboard error: {e}")
        return render_template("admin/dashboard.html", 
                             users_count=0, records_count=0, total_amount=0,
                             category_stats=[], panchayat_stats=[],
                             status_stats=[], monthly_labels=[], monthly_data=[])
    
@admin_bp.route('add-record', methods=['GET', 'POST'])
@login_required
@admin_required
def add_record():
    if request.method == 'POST':
        try:
            # Prepare record data
            record_data = {
                'panchayat_name': request.form.get('panchayat_name'),
                'village_name': request.form.get('village_name'),
                'registration_number': request.form.get('registration_number'),
                'beneficiary_name': request.form.get('beneficiary_name'),
                'father_name': request.form.get('father_name'),
                'mother_name': request.form.get('mother_name'),
                'category': request.form.get('category'),
                'priority': request.form.get('priority'),
                'schema_code': request.form.get('schema_code'),
                'bank_name': request.form.get('bank_name'),
                'branch_name': request.form.get('branch_name'),
                'ifsc_code': request.form.get('ifsc_code'),
                'bank_account_no': request.form.get('bank_account_no'),
                'sanction_no': request.form.get('sanction_no'),
                'amount_released': request.form.get('amount_released'),
                'installment': request.form.get('installment'),
                'credit_date': datetime.strptime(request.form.get('credit_date'), '%Y-%m-%d') if request.form.get('credit_date') else None,
                'house_status': request.form.get('house_status'),
                'inspection_date': datetime.strptime(request.form.get('inspection_date'), '%Y-%m-%d') if request.form.get('inspection_date') else None,
            }

            # Use PanchayatRecord model to create record
            result = PanchayatRecord.create_record(mongo, record_data, session.get('username'))
            
            if result['success']:
                flash('Record added successfully!', 'success')
                return redirect(url_for('admin.dashboard'))
            else:
                flash(result['message'], 'error')
            
        except Exception as e:
            flash('An error occurred while adding the record.', 'error')
            print(f"Add record error: {e}")

    return render_template('admin/add_record.html')

@admin_bp.route('/view-records')
@login_required
@admin_required
def view_records():
    try:
        page = int(request.args.get('page', 1))
        search = request.args.get('search', '')
        per_page = 10
        
        # Use PanchayatRecord model to get records
        result = PanchayatRecord.get_all_records(mongo, page, per_page, search)
        
        if result['success']:
            return render_template('admin/view_records.html', 
                                 records=result['records'],
                                 page=result['page'],
                                 total_records=result['total_records'],
                                 total_pages=result['total_pages'],
                                 search=search,
                                 can_edit=session.get('is_superadmin', False))  # Add this line
        else:
            flash('Error loading records', 'error')
            return render_template('admin/view_records.html', records=[], page=1, 
                                 total_records=0, total_pages=0, search='', 
                                 can_edit=session.get('is_superadmin', False))  # Add this line
            
    except Exception as e:
        flash('Error loading records', 'error')
        print(f"View records error: {e}")
        return render_template('admin/view_records.html', records=[], page=1, 
                             total_records=0, total_pages=0, search='', 
                             can_edit=session.get('is_superadmin', False))  # Add this line

@admin_bp.route('/export-excel')
@login_required
@admin_required
def export_excel():
    try:
        # Use PanchayatRecord model for export data
        export_data = PanchayatRecord.export_to_excel_data(mongo)
        
        if not export_data:
            flash('No data available for export', 'warning')
            return redirect(url_for('admin.dashboard'))

        df = pd.DataFrame(export_data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Panchayat Data')
        
        output.seek(0)

        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=panchayat_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        return response
    except Exception as e:
        flash('An error occurred while exporting data.', 'error')
        print(f"Export Excel error: {e}")
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete-record/<record_id>')
@login_required
@admin_required
def delete_record(record_id):
    try:
        # Use PanchayatRecord model to delete record
        success = PanchayatRecord.delete_record(mongo, record_id)
        
        if success:
            flash('Record deleted successfully!', 'success')
        else:
            flash('Record not found or could not be deleted', 'error')
            
    except Exception as e:
        flash('Error deleting record', 'error')
        print(f"Delete error: {e}")
    
    return redirect(url_for('admin.view_records'))

@admin_bp.route('/manage-users')
@login_required
@superadmin_required
def manage_users():
    try:
        page = int(request.args.get('page', 1))
        search = request.args.get('search', '')
        per_page = 10
        
        # Get all users with pagination
        query = {}
        if search:
            query = {
                '$or': [
                    {'username': {'$regex': search, '$options': 'i'}},
                    {'email': {'$regex': search, '$options': 'i'}},
                    {'role': {'$regex': search, '$options': 'i'}}
                ]
            }
        
        total_users = mongo.db.users.count_documents(query)
        total_pages = (total_users + per_page - 1) // per_page
        
        users = list(mongo.db.users.find(query)
                    .sort('created_at', -1)
                    .skip((page - 1) * per_page)
                    .limit(per_page))
        
        return render_template('admin/manage_users.html', 
                             users=users,
                             page=page,
                             total_users=total_users,
                             total_pages=total_pages,
                             search=search)
        
    except Exception as e:
        flash('Error loading users', 'error')
        print(f"Manage users error: {e}")
        return render_template('admin/manage_users.html', users=[], page=1, 
                             total_users=0, total_pages=0, search='')

@admin_bp.route('/edit-user/<user_id>', methods=['GET', 'POST'])
@login_required
@superadmin_required
def edit_user(user_id):
    if request.method == 'POST':
        try:
            new_role = request.form.get('role')
            is_admin = new_role in ['admin', 'superadmin']
            is_superadmin = new_role == 'superadmin'
            
            # Prevent superadmin from demoting themselves
            if user_id == session.get('user_id') and not is_superadmin:
                flash('You cannot demote yourself from superadmin role.', 'error')
                return redirect(url_for('admin.manage_users'))
            
            update_data = {
                'role': new_role,
                'is_admin': is_admin,
                'is_superadmin': is_superadmin,
                'updated_at': datetime.utcnow()
            }
            
            success = User.update_user(mongo, user_id, update_data)
            
            if success:
                flash('User role updated successfully!', 'success')
                return redirect(url_for('admin.manage_users'))
            else:
                flash('Failed to update user role', 'error')
            
        except Exception as e:
            flash('An error occurred while updating user role.', 'error')
            print(f"Edit user error: {e}")
    
    # GET request - show edit form
    try:
        user = User.get_user_by_id(mongo, user_id)
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('admin.manage_users'))
        
        return render_template('admin/edit_user.html', user=user)
        
    except Exception as e:
        flash('Error loading user', 'error')
        print(f"Edit user GET error: {e}")
        return redirect(url_for('admin.manage_users'))

@admin_bp.route('/toggle-user-status/<user_id>')
@login_required
@superadmin_required
def toggle_user_status(user_id):
    try:
        # Prevent superadmin from deactivating themselves
        if user_id == session.get('user_id'):
            flash('You cannot deactivate your own account.', 'error')
            return redirect(url_for('admin.manage_users'))
        
        user = User.get_user_by_id(mongo, user_id)
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('admin.manage_users'))
        
        new_status = not user.get('is_active', True)
        update_data = {
            'is_active': new_status,
            'updated_at': datetime.utcnow()
        }
        
        success = User.update_user(mongo, user_id, update_data)
        
        if success:
            status_text = 'activated' if new_status else 'deactivated'
            flash(f'User {status_text} successfully!', 'success')
        else:
            flash('Failed to update user status', 'error')
        
    except Exception as e:
        flash('Error updating user status', 'error')
        print(f"Toggle user status error: {e}")
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/delete-user/<user_id>')
@login_required
@superadmin_required
def delete_user(user_id):
    try:
        # Prevent superadmin from deleting themselves
        if user_id == session.get('user_id'):
            flash('You cannot delete your own account.', 'error')
            return redirect(url_for('admin.manage_users'))
        
        from bson import ObjectId
        result = mongo.db.users.delete_one({'_id': ObjectId(user_id)})
        
        if result.deleted_count > 0:
            flash('User deleted successfully!', 'success')
        else:
            flash('User not found or could not be deleted', 'error')
        
    except Exception as e:
        flash('Error deleting user', 'error')
        print(f"Delete user error: {e}")
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/edit-record/<record_id>', methods=['GET', 'POST'])
@login_required
@can_edit_records
def edit_record(record_id):
    if request.method == 'POST':
        try:
            # Prepare update data
            update_data = {
                'panchayat_name': request.form.get('panchayat_name'),
                'village_name': request.form.get('village_name'),
                'registration_number': request.form.get('registration_number'),
                'beneficiary_name': request.form.get('beneficiary_name'),
                'father_name': request.form.get('father_name'),
                'mother_name': request.form.get('mother_name'),
                'category': request.form.get('category'),
                'priority': request.form.get('priority'),
                'schema_code': request.form.get('schema_code'),
                'bank_name': request.form.get('bank_name'),
                'branch_name': request.form.get('branch_name'),
                'ifsc_code': request.form.get('ifsc_code'),
                'bank_account_no': request.form.get('bank_account_no'),
                'sanction_no': request.form.get('sanction_no'),
                'amount_released': float(request.form.get('amount_released')) if request.form.get('amount_released') else 0,
                'installment': int(request.form.get('installment')) if request.form.get('installment') else 0,
                'credit_date': datetime.strptime(request.form.get('credit_date'), '%Y-%m-%d') if request.form.get('credit_date') else None,
                'house_status': request.form.get('house_status'),
                'inspection_date': datetime.strptime(request.form.get('inspection_date'), '%Y-%m-%d') if request.form.get('inspection_date') else None,
                'updated_by': session.get('username')
            }

            # Update record
            success = PanchayatRecord.update_record(mongo, record_id, update_data)
            
            if success:
                flash('Record updated successfully!', 'success')
                return redirect(url_for('admin.view_records'))
            else:
                flash('Failed to update record', 'error')
            
        except Exception as e:
            flash('An error occurred while updating the record.', 'error')
            print(f"Edit record error: {e}")
    
    # GET request - show edit form
    try:
        record = PanchayatRecord.get_record_by_id(mongo, record_id)
        if not record:
            flash('Record not found', 'error')
            return redirect(url_for('admin.view_records'))
        
        return render_template('admin/edit_record.html', record=record)
        
    except Exception as e:
        flash('Error loading record', 'error')
        print(f"Edit record GET error: {e}")
        return redirect(url_for('admin.view_records'))

