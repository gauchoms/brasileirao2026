import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'brasileirao2026')
    
    # Se DATABASE_URL existe (Render), usa PostgreSQL. Senão, usa SQLite local
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///' + os.path.join(basedir, 'brasileirao.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_FOOTBALL_KEY = os.getenv('API_FOOTBALL_KEY')
