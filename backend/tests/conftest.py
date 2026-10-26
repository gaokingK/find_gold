import os

os.environ["DB_NAME"] = "fund_test_db"

from pathlib import Path

import pytest
from pymysql import connect

from app import create_app
from app.config import DB_CONFIG
from tests.factories import create_fund as factory_create_fund


BASE_DIR = Path(__file__).resolve().parent.parent
SQL_PATHS = [
    BASE_DIR / "database" / "v1-basic-management.sql",
    BASE_DIR / "database" / "v2-operations.sql",
    BASE_DIR / "database" / "v3-nav-history.sql",
]
TEST_DB_NAME = "fund_test_db"


def assert_test_database():
    current = DB_CONFIG.get("database")

    if current != TEST_DB_NAME:
        raise RuntimeError(
            f"测试只允许连接 {TEST_DB_NAME}，当前配置是 {current}，已中止测试"
        )


def server_connection():
    config = DB_CONFIG.copy()
    config.pop("database")
    return connect(**config)


def get_test_connection():
    assert_test_database()

    config = DB_CONFIG.copy()
    config["database"] = TEST_DB_NAME
    return connect(**config)


@pytest.fixture(scope="session")
def prepare_test_database():
    assert_test_database()

    conn = server_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE DATABASE IF NOT EXISTS fund_test_db
                CHARACTER SET utf8mb4
                COLLATE utf8mb4_unicode_ci
                """
            )
        conn.commit()
    finally:
        conn.close()

    conn = get_test_connection()

    try:
        with conn.cursor() as cursor:
            for sql_path in SQL_PATHS:
                sql = sql_path.read_text(encoding="utf-8")
                statements = [
                    item.strip()
                    for item in sql.split(";")
                    if item.strip()
                ]

                for statement in statements:
                    cursor.execute(statement)

            conn.commit()
    finally:
        conn.close()


@pytest.fixture(scope="session")
def app(prepare_test_database):
    return create_app()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(prepare_test_database):
    conn = get_test_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS current_db")
            current_db = cursor.fetchone()["current_db"]

            if current_db != TEST_DB_NAME:
                raise RuntimeError(
                    f"拒绝清空数据库 {current_db}，只允许清空 {TEST_DB_NAME}"
                )

            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("TRUNCATE TABLE nav_history")
            cursor.execute("TRUNCATE TABLE operations")
            cursor.execute("TRUNCATE TABLE initial_positions")
            cursor.execute("TRUNCATE TABLE funds")
            cursor.execute("TRUNCATE TABLE bloggers")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        conn.commit()
    finally:
        conn.close()

    yield
    

@pytest.fixture
def create_fund(client):
    def _create_fund(name="测试基金", fund_code="TEST001"):
        return factory_create_fund(client, name, fund_code)
    return _create_fund
        