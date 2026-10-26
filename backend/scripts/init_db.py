# 创建初始化脚本
# 有了初始化脚本，新环境可以快速创建同样的表结构，避免手动执行多条SQL导致遗漏

from pathlib import Path

from pymysql import connect

from app.config import DB_CONFIG

BASE_DIR = Path(__file__).resolve().parent.parent
SQL_PATHS = [
    BASE_DIR / "database" / "v1-basic-management.sql",
    BASE_DIR / "database" / "v2-operations.sql",
    BASE_DIR / "database" / "v3-nav-history.sql",
]

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
    conn = connect(**DB_CONFIG)

    try:
        with conn.cursor() as cursor:
            for sql_path in SQL_PATHS:
                if not sql_path.exists():
                    raise FileNotFoundError(f"SQL file not found: {sql_path}")

                sql = sql_path.read_text(encoding="utf-8")
                statements = [
                    item.strip()
                    for item in sql.split(";")
                    if item.strip()
                ]

                for statement in statements:
                    cursor.execute(statement)

            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()

        conn.commit()
        print("Created tables:")
        for row in tables:
            print(dict(row))
    finally:
        conn.close()

def main():
    create_datebase()
    create_table()


if __name__ == "__main__":
    main()