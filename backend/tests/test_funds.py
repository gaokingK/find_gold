from factories import create_fund

def test_create_fund_success(client):
    data = create_fund(client, name="基金新增测试", fund_code="F000001")

    assert data["name"]  == "基金新增测试"
    assert data["fund_code"] == "F000001"
    assert "fund_id" in data

def test_list_funds_returns_created_fund(client):
    create_fund(client, name="基金列表测试", fund_code="F000002")

    response = client.get("/api/v1/funds")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert any(
        item["name"] == "基金列表测试"
        for item in body["data"]["items"]
    )

def test_update_fund_success(client):
    fund = create_fund(client, name="编辑前基金", fund_code="F000003")

    response = client.put(
        f"/api/v1/funds/{fund['fund_id']}",
        json={
            "name": "编辑后基金",
            "fund_code": "F000003"
        }
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["name"] == "编辑后基金"

def test_create_fund_with_duplicate_code(client):
    create_fund(client, name="第一只基金", fund_code="DUPLICATE001")

    response = client.post(
        "/api/v1/funds",
        json={
            "name": "第二只基金",
            "fund_code": "DUPLICATE001"
        }
    )
    body = response.get_json()

    assert response.status_code == 409
    assert body["code"] == "FUND_CODE_DUPLICATED"

def test_create_fund_with_missing_fields(client):
    response = client.post(
        "/api/v1/funds",
        json={}
    )
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"