import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'attendance.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    XAI_API_KEY = os.environ.get('XAI_API_KEY', '')
    WTF_CSRF_ENABLED = True
    ATTENDANCE_THRESHOLD = 75.0
    CRITICAL_THRESHOLD = 65.0
