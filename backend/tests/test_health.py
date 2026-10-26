def test_health(client):
    response = client.get('/health')
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["message"] == "ok"
    assert body["data"]["status"] == "ok"