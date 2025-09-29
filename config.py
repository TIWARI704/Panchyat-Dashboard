import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    SECRET_KEY_BASE = os.getenv("SECRET_KEY_BASE", "default_secret_key")

config = Config()