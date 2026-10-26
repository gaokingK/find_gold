from factories import create_fund, create_blogger

def create_initial_position(client, blogger_id, fund_id, shares=12000, cost_amount=15600, record_date="2020-01-01"):
    response = client.post(
        "/api/v1/initial-positions",
        json={
            "blogger_id": blogger_id,
            "fund_id": fund_id,
            "shares": shares,
            "cost_amount": cost_amount,
            "record_date": record_date
        }
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    return body["data"]

def test_create_initial_position_success(client):
    blogger = create_blogger(client, name="持仓博主")
    fund = create_fund(client, name="持仓基金", fund_code="POSITION001")

    data = create_initial_position(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"]
    )

    assert data["blogger_id"] == blogger["blogger_id"]
    assert data["fund_id"] == fund["fund_id"]
    assert data["blogger_name"] == "持仓博主"
    assert data["fund_name"] == "持仓基金"
    assert data["fund_code"] == "POSITION001"


def test_list_initial_positions_returns_related_names(client):
    blogger = create_blogger(client, name="列表博主")
    fund = create_fund(client, name="列表基金", fund_code="POSITION002")
    create_initial_position(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"]
    )

    response = client.get("/api/v1/initial-positions")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert any(
        item["blogger_name"] == "列表博主"
        and item["fund_name"] == "列表基金"
        for item in body["data"]["items"]
    )


def test_update_initial_position_success(client):
    blogger = create_blogger(client, name="编辑持仓博主")
    fund = create_fund(client, name="编辑持仓基金", fund_code="POSITION003")
    position = create_initial_position(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"]
    )

    response = client.put(
        f"/api/v1/initial-positions/{position['initial_position_id']}",
        json={
            "blogger_id": blogger["blogger_id"],
            "fund_id": fund["fund_id"],
            "shares":13000,
            "cost_amount":16000,
            "record_date": "2020-01-01"
        }
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["shares"]==13000
    assert body["data"]["cost_amount"]==16000

def test_create_initial_position_with_missing_blogger(client):
    fund = create_fund (client, name="缺失博主基金", fund_code="POSITION004")

    response = client.post(
        "/api/v1/initial-positions",
        json={
            "blogger_id": 999999,
            "fund_id": fund["fund_id"],
            "shares": 12000,
            "cost_amount": 15600,
            "record_date": "2020-01-01"
        }
    )
    body = response.get_json()

    assert response.status_code == 404
    assert body["code"] == "BLOGGER_NOT_FOUND"

def test_create_initial_position_with_missing_fund(client):
    blogger = create_blogger(client, name="缺少基金博主")

    response = client.post(
        "/api/v1/initial-positions",
        json={
            "blogger_id": blogger["blogger_id"],
            "fund_id": 999999,
            "shares": 12000,
            "cost_amount": 15600,
            "record_date": "2020-01-01"
        }
    )
    body = response.get_json()

    assert response.status_code == 404
    assert body["code"] == "FOUND_NOT_FOUND"

def test_create_initial_position_with_duplicate_data(client):
    blogger = create_blogger(client, name="重复持仓博主")
    fund = create_fund(client, name="重复持仓基金", fund_code="POSITION005")

    create_initial_position(
        client,
        blogger_id=blogger['blogger_id'],
        fund_id=fund['fund_id']
    )

    response = client.post(
        "/api/v1/initial-positions",
        json={
            "blogger_id": blogger["blogger_id"],
            "fund_id": fund["fund_id"],
            "shares": 12000,
            "cost_amount": 15600,
            "record_date": "2020-01-01"
        }
    )
    body = response.get_json()

    assert response.status_code == 409
    assert body["code"] == "INITIAL_POSITION_DUPLICATED"