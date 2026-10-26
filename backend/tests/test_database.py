from app.config import DB_CONFIG

def test_database_name_is_test_database():
    assert DB_CONFIG["database"] == "fund_test_db"

def test_clean_db_fixture_can_run(client):
    response = client.get("/health")

    assert response.status_code == 200