# 🏛️ Panchayat Management Dashboard

### Step 1: Clone the Repository
```bash
git clone "URL"
cd Panchyat-Dashboard
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

# Run the application to create collections
python app.py

### Starting the Application
```bash
python app.py
```
### Project Structure
```
Panchyat-Dashboard/
├── app.py                 # Main application entry point
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
├── .gitignore           # Git ignore rules
├── README.md            # Project documentation
├── routes/              # Flask blueprints
│   ├── __init__.py
│   ├── login.py         # Authentication routes
│   ├── admin.py         # Admin routes
│   └── user.py          # User routes
├── models/              # Database models
│   ├── __init__.py
│   ├── admin.py         # Record model
│   └── login.py         # User model
├── templates/           # HTML templates
│   ├── admin/           # Admin templates
│   ├── user/            # User templates
│   ├── login.html       # Login page
│   └── register.html    # Registration page
├── static/              # Static files
│   ├── css/
│   ├── js/
│   └── images/
└── scripts/             # Utility scripts
    ├── add_dummy_data.py
    └── quick_dummy_data.py
```

### Running in Development Mode
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
```