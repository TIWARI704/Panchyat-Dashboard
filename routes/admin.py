from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response
from models.admin import PanchayatRecord
from models.login import User
from routes.login import admin_required, login_required, superadmin_required, can_edit_records
from datetime import datetime, timedelta
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

        # Calculate tab-specific statistics
        approved_stats = calculate_approved_stats(mongo)
        pending_stats = calculate_pending_stats(mongo)
        inreview_stats = calculate_inreview_stats(mongo)
        disapproved_stats = calculate_disapproved_stats(mongo)
        rejected_stats = calculate_rejected_stats(mongo)
        
        return render_template("admin/dashboard.html", 
                             users_count=users_count,
                             records_count=stats['total_records'],
                             total_amount=stats['total_amount'],
                             category_stats=stats['category_stats'],
                             panchayat_stats=stats['panchayat_stats'],
                             status_stats=status_stats,
                             monthly_labels=monthly_labels,
                             monthly_data=monthly_data,
                             # Add tab-specific stats
                             approved_status=approved_stats,  # Fix: Use approved_status not approved_stats
                             approved_stats=approved_stats,
                             pending_stats=pending_stats,
                             inreview_stats=inreview_stats,
                             disapproved_stats=disapproved_stats,
                             rejected_stats=rejected_stats)
                             
    except Exception as e:
        flash('An error occurred while loading the dashboard.', 'error')
        print(f"Dashboard error: {e}")
        # Return with default empty stats
        empty_stats = get_default_stats()
        return render_template("admin/dashboard.html", 
                             users_count=0, 
                             records_count=0, 
                             total_amount=0,
                             category_stats=[], 
                             panchayat_stats=[],
                             status_stats=[], 
                             monthly_labels=[], 
                             monthly_data=[],
                             approved_status=empty_stats,
                             approved_stats=empty_stats,
                             pending_stats=empty_stats,
                             inreview_stats=empty_stats,
                             disapproved_stats=empty_stats,
                             rejected_stats=empty_stats)

def calculate_approved_stats(mongo):
    """Calculate statistics for approved records (Complete status)"""
    try:
        # Total approved count (Complete houses)
        total_count = mongo.db.panchayat_records.count_documents({"house_status": "Complete"})
        
        # This month count
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month = mongo.db.panchayat_records.count_documents({
            "house_status": "Complete",
            "created_at": {"$gte": start_of_month}
        })
        
        # Total amount for approved records
        amount_pipeline = [
            {"$match": {"house_status": "Complete"}},
            {"$group": {"_id": None, "total": {"$sum": {"$toDouble": "$amount_released"}}}}
        ]
        amount_result = list(mongo.db.panchayat_records.aggregate(amount_pipeline))
        total_amount = amount_result[0]['total'] if amount_result else 0
        
        # Calculate average processing days (dummy calculation)
        avg_processing_days = 15
        
        return {
            'count': total_count,
            'this_month': this_month,
            'recent_count': this_month,
            'total_amount': total_amount,
            'avg_amount': round((total_amount / total_count) if total_count > 0 else 0, 2),
            'avg_processing_days': avg_processing_days,
            'fastest_approval': 7,
            'completion_rate': 85
        }
    except Exception as e:
        print(f"Error calculating approved stats: {e}")
        return get_default_stats()

def calculate_pending_stats(mongo):
    """Calculate statistics for pending records (Under Construction)"""
    try:
        # Count pending records
        total_count = mongo.db.panchayat_records.count_documents({"house_status": "Under Construction"})
        
        # Today's count
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = mongo.db.panchayat_records.count_documents({
            "house_status": "Under Construction",
            "created_at": {"$gte": today_start}
        })
        
        # Overdue count (records older than 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        overdue_count = mongo.db.panchayat_records.count_documents({
            "house_status": "Under Construction",
            "created_at": {"$lt": thirty_days_ago}
        })
        
        # Total amount for pending records
        amount_pipeline = [
            {"$match": {"house_status": "Under Construction"}},
            {"$group": {"_id": None, "total": {"$sum": {"$toDouble": "$amount_released"}}}}
        ]
        amount_result = list(mongo.db.panchayat_records.aggregate(amount_pipeline))
        total_amount = amount_result[0]['total'] if amount_result else 0
        
        return {
            'count': total_count,
            'recent_count': today_count,
            'overdue_count': overdue_count,
            'total_amount': total_amount,
            'avg_waiting_days': 22,
            'longest_waiting': 45,
            'avg_amount': 15
        }
    except Exception as e:
        print(f"Error calculating pending stats: {e}")
        return get_default_stats()

def calculate_inreview_stats(mongo):
    """Calculate statistics for records in review (Incomplete status)"""
    try:
        # Count in-review records
        total_count = mongo.db.panchayat_records.count_documents({"house_status": "Incomplete"})
        
        # Today's count
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = mongo.db.panchayat_records.count_documents({
            "house_status": "Incomplete",
            "created_at": {"$gte": today_start}
        })
        
        return {
            'count': total_count,
            'today_count': today_count,
            'reviewers': 5,
            'avg_per_reviewer': round(total_count / 5) if total_count > 0 else 0,
            'avg_review_days': 8,
            'efficiency': 15,
            'doc_verified': round(total_count * 0.6),
            'field_pending': round(total_count * 0.3),
            'final_pending': round(total_count * 0.1)
        }
    except Exception as e:
        print(f"Error calculating inreview stats: {e}")
        return get_default_stats()

def calculate_disapproved_stats(mongo):
    """Calculate statistics for disapproved records"""
    try:
        # Using priority >= 8 as disapproved for demo
        total_count = mongo.db.panchayat_records.count_documents({"priority": {"$gte": 8}})
        
        # This month count
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month = mongo.db.panchayat_records.count_documents({
            "priority": {"$gte": 8},
            "created_at": {"$gte": start_of_month}
        })
        
        return {
            'count': total_count,
            'this_month': this_month,
            'resubmitted': round(total_count * 0.3),
            'resubmit_rate': 30,
            'top_reason': 'Incomplete Documentation',
            'top_reason_count': round(total_count * 0.4),
            'disapproval_rate': 12,
            'trend': 'down',
            'trend_text': '↓ 5% vs last month'
        }
    except Exception as e:
        print(f"Error calculating disapproved stats: {e}")
        return get_default_stats()

def calculate_rejected_stats(mongo):
    """Calculate statistics for rejected records"""
    try:
        # Using priority == 10 as rejected for demo
        total_count = mongo.db.panchayat_records.count_documents({"priority": 10})
        
        return {
            'count': total_count,
            'this_month': round(total_count * 0.1),
            'total_amount': total_count * 50000,
            'rejection_rate': 5,
            'top_reason': 'Eligibility Criteria Not Met',
            'top_reason_count': round(total_count * 0.6)
        }
    except Exception as e:
        print(f"Error calculating rejected stats: {e}")
        return get_default_stats()

def get_default_stats():
    """Return default stats when there's an error or no data"""
    return {
        'count': 0,
        'this_month': 0,
        'recent_count': 0,
        'total_amount': 0,
        'avg_amount': 0,
        'avg_processing_days': 0,
        'fastest_approval': 0,
        'completion_rate': 0,
        'overdue_count': 0,
        'avg_waiting_days': 0,
        'longest_waiting': 0,
        'today_count': 0,
        'reviewers': 0,
        'avg_per_reviewer': 0,
        'avg_review_days': 0,
        'efficiency': 0,
        'doc_verified': 0,
        'field_pending': 0,
        'final_pending': 0,
        'resubmitted': 0,
        'resubmit_rate': 0,
        'top_reason': 'N/A',
        'top_reason_count': 0,
        'disapproval_rate': 0,
        'trend': 'stable',
        'trend_text': 'No change',
        'rejection_rate': 0
    }

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
                'priority': int(request.form.get('priority',0)) if request.form.get('priority') else None,
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

# Add these routes to your admin.py file

@admin_bp.route("/create_user", methods=["POST"])
@login_required
@superadmin_required
def create_user():
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        email = request.form.get('email', '').strip()
        role = request.form.get('role', '')
        status = request.form.get('status', 'active')
        full_name = request.form.get('full_name', '').strip()

        print(f"Creating user: {username}, role: {role}, email: {email}")

        # Validation
        if not username or not password or not role:
            flash('Username, password, and role are required.', 'error')
            return redirect(url_for('admin.manage_users'))

        if len(username) < 3:
            flash('Username must be at least 3 characters long.', 'error')
            return redirect(url_for('admin.manage_users'))

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('admin.manage_users'))

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('admin.manage_users'))

        if role not in ['user', 'admin', 'superadmin']:
            flash('Invalid role selected.', 'error')
            return redirect(url_for('admin.manage_users'))

        # Set role-based flags
        is_admin = role in ['admin', 'superadmin']
        is_superadmin = role == 'superadmin'

        # Create user using the User model (dictionary approach)
        user_data = {
            'username': username,
            'password': password,
            'role': role,
            'email': email if email else None,
            'full_name': full_name if full_name else None,
            'is_active': status == 'active',
            'is_admin': role in ['admin', 'superadmin'],
            'is_superadmin': role == 'superadmin'
        }

        result = User.create_user(mongo, user_data)

        if result['success']:
            flash(f'User "{username}" created successfully with role "{role}".', 'success')
        else:
            flash(result['message'], 'error')

    except Exception as e:
        print(f"Error creating user: {e}")
        import traceback
        traceback.print_exc()
        flash('An error occurred while creating the user.', 'error')

    return redirect(url_for('admin.manage_users'))
