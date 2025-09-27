import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import random
from flask import Flask
from flask_pymongo import PyMongo
from config import config
from models.admin import PanchayatRecord

# Quick setup
app = Flask(__name__)
app.config["MONGO_URI"] = config.DATABASE_URL
app.config["SECRET_KEY"] = config.SECRET_KEY_BASE
mongo = PyMongo(app)

def add_quick_data():
    """Add 25 quick dummy records"""
    records = [
        {
            'panchayat_name': f'Gram Panchayat {random.choice(["Rampur", "Sitapur", "Govindpur", "Krishnapur", "Shivpur"])}',
            'village_name': f'{random.choice(["Ram", "Shyam", "Gopal", "Krishna", "Shiva"])} Nagar',
            'registration_number': f'UP0{random.randint(1,5)}/2024/{random.randint(1000,9999)}',
            'beneficiary_name': random.choice(['Ram Kumar Singh', 'Shyam Lal Gupta', 'Sunita Devi', 'Geeta Singh', 'Mohan Prasad']),
            'father_name': f'Late {random.choice(["Ram", "Shyam", "Krishna", "Govind"])} Singh',
            'mother_name': f'Late {random.choice(["Sita", "Radha", "Geeta", "Meera"])} Devi',
            'category': random.choice(['SC', 'ST', 'OBC', 'General']),
            'priority': random.choice(['High', 'Medium', 'Low']),
            'schema_code': f'PMAY-G-{random.randint(1000,9999)}',
            'bank_name': random.choice(['State Bank of India', 'Punjab National Bank', 'Bank of Baroda']),
            'branch_name': 'Main Branch',
            'ifsc_code': f'SBIN0{random.randint(100000,999999)}',
            'bank_account_no': str(random.randint(10000000000, 99999999999)),
            'sanction_no': f'PMAY-G/2024/{random.randint(10000,99999)}',
            'amount_released': random.choice([120000, 150000, 180000, 200000]),
            'installment': random.randint(1, 3),
            'credit_date': datetime.now() - timedelta(days=random.randint(30, 365)),
            'house_status': random.choice(['Complete', 'Under Construction', 'Incomplete']),
            'inspection_date': datetime.now() - timedelta(days=random.randint(1, 30))
        }
        for _ in range(25)
    ]
    
    with app.app_context():
        success_count = 0
        for i, record in enumerate(records):
            try:
                result = PanchayatRecord.create_record(mongo, record, "quick_script")
                if result['success']:
                    success_count += 1
                    print(f"✓ Added record {i+1}: {record['beneficiary_name']}")
                else:
                    print(f"✗ Failed record {i+1}: {result['message']}")
            except Exception as e:
                print(f"✗ Error record {i+1}: {e}")
        
        print(f"\n🎉 Successfully added {success_count}/25 records!")

if __name__ == "__main__":
    print("🚀 Quick Dummy Data Generator")
    add_quick_data()