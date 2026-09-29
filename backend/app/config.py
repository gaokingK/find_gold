import os

from pymysql.cursors import DictCursor

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', "127.0.0.1"),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'fund_db'),
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}