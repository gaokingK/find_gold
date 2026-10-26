def create_blogger(client, name="测试博主"):
    response = client.post(
        "/api/v1/bloggers",
        json={
            "name": name,
            "sector": "成长股",
            "observe_start_date": "2020-01-01"
        }
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    return body["data"]

def create_fund(client, name="测试基金", fund_code="TEST001"):
    response = client.post(
        "/api/v1/funds",
        json={
            "name":name,
            "fund_code": fund_code
        }
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    return body["data"]