# 创建初始化脚本
# 有了初始化脚本，新环境可以快速创建同样的表结构，避免手动执行多条SQL导致遗漏

from pathlib import Path

from pymysql import connect

from app.config import DB_CONFIG

BASE_DIR = Path(__file__).resolve().parent.parent
SQL_PATH = BASE_DIR / "database" / "v1-basic-management.sql"

def create_datebase():
    server_config = DB_CONFIG.copy()
    server_config.pop('database')

    conn = connect(**server_config)

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE DATABASE IF NOT EXISTS fund_db
                CHARACTER SET utf8mb4
                COLLATE utf8mb4_unicode_ci
                """
            )
        conn.commit()

    finally:
        conn.close()

def create_table():
    sql = SQL_PATH.read_text(encoding='utf-8')
    # 列表推导式
    statements = [item.strip() for item in sql.split(";") if item.strip()]

    conn = connect(**DB_CONFIG) 

    try:
        with conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)

            cursor.execute('SHOW TABLES')
            tables = cursor.fetchall()

        conn.commit()
        print('Create tables:')
        for row in tables:
            print(dict(row))
    finally:
        conn.close()

def main():
    create_datebase()
    create_table()

if __name__ == '__main__':
    main()