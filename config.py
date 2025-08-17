import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'gamified-public-speaking-secret-key-2024'
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'gamified_speaking')
    ASSEMBLY_AI_KEY = os.environ.get('assembly_key')
    GEMINI_API_KEY = os.environ.get('gemini_api_key')   
    UPLOAD_FOLDER = 'static/audio'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    LOG_LEVEL = 'INFO'