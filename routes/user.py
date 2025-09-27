from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.admin import PanchayatRecord
from routes.login import login_required
from datetime import datetime

user_bp = Blueprint('user', __name__)
mongo = None

def intialize_user(db):
    global mongo
    mongo = db

@user_bp.route("/dashboard")
@login_required
def dashboard():
    try:
        # Get basic statistics for user dashboard
        stats = PanchayatRecord.get_statistics(mongo)
        
        return render_template("user/dashboard.html", 
                             records_count=stats['total_records'],
                             total_amount=stats['total_amount'],
                             category_stats=stats['category_stats'],
                             panchayat_stats=stats['panchayat_stats'])
    except Exception as e:
        flash('An error occurred while loading the dashboard.', 'error')
        print(f"User dashboard error: {e}")
        return render_template("user/dashboard.html", 
                             records_count=0, total_amount=0,
                             category_stats=[], panchayat_stats=[])

@user_bp.route('/add-record', methods=['GET', 'POST'])
@login_required
def add_record():
    if request.method == 'POST':
        try:
            # Prepare record data (same as admin)
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
                return redirect(url_for('user.dashboard'))
            else:
                flash(result['message'], 'error')
            
        except Exception as e:
            flash('An error occurred while adding the record.', 'error')
            print(f"User add record error: {e}")

    return render_template('user/add_record.html')

@user_bp.route('/view-records')
@login_required
def view_records():
    try:
        page = int(request.args.get('page', 1))
        search = request.args.get('search', '')
        per_page = 10
        
        # Use PanchayatRecord model to get records
        result = PanchayatRecord.get_all_records(mongo, page, per_page, search)
        
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
        print(f"User view records error: {e}")
        return render_template('user/view_records.html', records=[], page=1, 
                             total_records=0, total_pages=0, search='')