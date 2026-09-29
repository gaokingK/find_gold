# 此文件的目的是为了避免重复代码
from pymysql import connect

from app.config import DB_CONFIG

def get_connection():
    return connect(**DB_CONFIG)