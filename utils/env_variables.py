import os
from dotenv import load_dotenv

load_dotenv()

db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')
db_url = os.getenv('DB_URL')
db_port = os.getenv('DB_PORT')
DATABASE_URL = f"postgresql+asyncpg://{db_user}:{db_password}@{db_url}:{db_port}/{db_name}"

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES')
REFRESH_TOKEN_EXPIRE_MINUTES = os.getenv('REFRESH_TOKEN_EXPIRE_MINUTES')


UPLOAD_DIR = os.getenv('UPLOAD_DIR')
UPLOAD_DIR_UNKNOWN = UPLOAD_DIR + os.getenv('UPLOAD_DIR_UNKNOWN')
UPLOAD_DIR_KNOWN = UPLOAD_DIR + os.getenv('UPLOAD_DIR_KNOWN')

FIREBASE_CERTIFICATE_PATH = os.getenv('FIREBASE_CERTIFICATE_PATH')
