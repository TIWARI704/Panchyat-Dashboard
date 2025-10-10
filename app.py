import os
from flask import Flask as flask, redirect, url_for
from flask_pymongo import PyMongo
from config import config



app = flask(__name__)


app.config["MONGO_URI"] = config.DATABASE_URL
app.config["SECRET_KEY"] = config.SECRET_KEY_BASE

mongo = PyMongo(app)

# Import and initialize all routes
from routes.login import login_bp, intialize
from routes.admin import admin_bp, intialize_admin
from routes.user import user_bp, intialize_user
from routes.bulk_import import bulk_import_bp,intialize_bulk_import


intialize(mongo)
intialize_admin(mongo)
intialize_user(mongo)
intialize_bulk_import(mongo)

# Initialize sample data if it doesn't exist
try:
    from scripts.create_sample_data import create_sample_data
    create_sample_data(mongo)
except Exception as e:
    print(f"Warning: Could not initialize sample data: {e}")

# Create default user if none exists
try:
    from scripts.create_default_user import create_default_user
    create_default_user(mongo)
except Exception as e:
    print(f"Warning: Could not create default user: {e}")

app.register_blueprint(login_bp, url_prefix="/auth")
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(bulk_import_bp, url_prefix="/data")

@app.route("/")
def home():
    return redirect(url_for("login.login"))


def main():
    app.run(debug=True)

if __name__ == "__main__":
    main()