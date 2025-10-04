"""
Login Routes Module

This module handles user authentication, login/logout functionality,
and provides decorators for role-based access control.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.login import User
from datetime import datetime
from functools import wraps

# Initialize login blueprint
login_bp = Blueprint('login', __name__)
mongo = None

def intialize(db):
    """Initialize MongoDB connection for login routes"""
    global mongo
    mongo = db

@login_bp.route("/", methods=["GET", "POST"])
def login():
    """
    User Login
    
    Handles user authentication. On successful login, redirects users
    to their appropriate dashboard based on their role.
    """
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Please enter both username and password.", "error")
            return render_template("login.html")
        
        # Use User model for authentication
        auth_result = User.authenticate(mongo, username, password)
        
        if auth_result['success']:
            user = auth_result['user']

            if not user.get("is_active", True):
                flash("Your account is inactive. Please contact administrator.", "error")
                return render_template("login.html")
            
            session["user_id"] = str(user["_id"])
            session["username"] = user["username"]
            session["is_admin"] = user.get("is_admin", False)
            session["is_superadmin"] = user.get("is_superadmin", False)
            session["role"] = user.get("role", "user")
            
            flash("Login successful!", "success")
            
            # Redirect based on role
            if user.get("is_superadmin") or user.get("is_admin"):
                return redirect(url_for("admin.dashboard"))
            else:
                return redirect(url_for("user.dashboard"))
        else:
            flash(auth_result['message'], "error")
            
    return render_template("login.html")

@login_bp.route("/logout")
def logout():
    """
    User Logout
    
    Clears the user session and redirects to the login page.
    """
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login.login"))

@login_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    User Registration
    
    Allows new users to register for the system. Only available
    if registration is enabled in the configuration.
    """
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")
        user_role = request.form.get("user_role")

        if not username or not password or not user_role:
            flash("Please fill in all required fields.", "error")
            return render_template("register.html")
        
        # Set role-based permissions
        is_admin = user_role in ['admin', 'superadmin']
        is_superadmin = user_role == 'superadmin'
        
        # Use User model to create user
        result = User.create_user(mongo, username, password, email, user_role, is_admin, is_superadmin)
        
        if result['success']:
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login.login"))
        else:
            flash(result['message'], "error")
        
    return render_template("register.html")

@login_bp.before_app_request
def check_user_active_status():
    """
    Middleware to check if the logged-in user is active.
    
    If the user is inactive, they are logged out and redirected to login page.
    """
    if request.endpoint in ['login.login', 'login.logout', 'login.register', 'static']:
        return

    if 'user_id' in session:
        try:
            user = User.get_user_by_id(mongo, session['user_id'])
            if not user or not user.get("is_active", True):
                session.clear()
                flash("Your account has been deactivated. Please contact administrator.", "error")
                return redirect(url_for("login.login"))
        except Exception as e:
            session.clear()
            flash("An error occurred. Please log in again.", "error")
            return redirect(url_for("login.login"))

def login_required(f):
    """
    Decorator to require user login for accessing a route.
    
    Redirects to login page if user is not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("login.login"))
        
        try:
            user = User.get_user_by_id(mongo, session['user_id'])
            if not user or not user.get("is_active", True):
                session.clear()
                flash("Your account has been deactivated. Please contact administrator.", "error")
                return redirect(url_for("login.login"))
        except Exception as e:
            session.clear()
            flash("An error occurred. Please log in again.", "error")
            return redirect(url_for("login.login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator to require admin privileges for accessing a route.
    
    Redirects to login page if user is not authenticated or not an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or not session.get("is_admin"):
            flash("Admin access required.", "error")
            return redirect(url_for("login.login"))
        
        try:
            user = User.get_user_by_id(mongo, session['user_id'])
            if not user or not user.get("is_active", True):
                session.clear()
                flash("Your account has been deactivated. Please contact administrator.", "error")
                return redirect(url_for("login.login"))
        except Exception as e:
            session.clear()
            flash("An error occurred. Please log in again.", "error")
            return redirect(url_for("login.login"))
        return f(*args, **kwargs)
    return decorated_function

def superadmin_required(f):
    """
    Decorator to require super admin privileges for accessing a route.
    
    Redirects to login page if user is not authenticated or not a super admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or not session.get("is_superadmin"):
            flash("Super Admin access required.", "error")
            return redirect(url_for("login.login"))
        
        try:
            user = User.get_user_by_id(mongo, session['user_id'])
            if not user or not user.get("is_active", True):
                session.clear()
                flash("Your account has been deactivated. Please contact administrator.", "error")
                return redirect(url_for("login.login"))
        except Exception as e:
            session.clear()
            flash("An error occurred. Please log in again.", "error")
            return redirect(url_for("login.login"))
        return f(*args, **kwargs)
    return decorated_function

def can_edit_records(f):
    """
    Decorator to check if user can edit records.
    
    Currently only super admins can edit records.
    Redirects to appropriate page if user lacks permissions.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("login.login"))
        
        if not session.get("is_superadmin"):
            flash("Only Super Admin can edit records.", "error")
            return redirect(url_for("admin.dashboard"))
        
        try:
            user = User.get_user_by_id(mongo, session['user_id'])
            if not user or not user.get("is_active", True):
                session.clear()
                flash("Your account has been deactivated. Please contact administrator.", "error")
                return redirect(url_for("login.login"))
        except Exception as e:
            session.clear()
            flash("An error occurred. Please log in again.", "error")
            return redirect(url_for("login.login"))
        
        return f(*args, **kwargs)
    return decorated_function
