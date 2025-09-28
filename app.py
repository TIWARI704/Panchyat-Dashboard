import os
from flask import Flask as flask, render_template, redirect, url_for
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

intialize(mongo)
intialize_admin(mongo)
intialize_user(mongo)

app.register_blueprint(login_bp, url_prefix="/auth")
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(user_bp, url_prefix="/user")

@app.route("/")
def home():
    return redirect(url_for("login.login"))


def main():
    app.run(debug=True)

if __name__ == "__main__":
    main()