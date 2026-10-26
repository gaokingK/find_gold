def create_blogger(client, name="快照博主"):
    response = client.post(
        "/api/v1/bloggers",
        json={
            "name": name,
            "sector": "成长股",
            "observe_start_date": "2026-01-01"
        }
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    return body["data"]


def create_fund(client, name="快照基金", fund_code="SNAP000001"):
    response = client.post(
        "/api/v1/funds",
        json={
            "name": name,
            "fund_code": fund_code
        }
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    return body["data"]


def create_initial_position(
        client,
        blogger_id,
        fund_id,
        shares=12000,
        cost_amount=15600,
        record_date="2026-01-01"
): 
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


def create_operation(
        client,
        blogger_id,
        fund_id,
        operation_type,
        operation_date,
        shares=None,
        amount=0
):
    payload = {
        "blogger_id": blogger_id,
        "fund_id": fund_id,
        "operation_type": operation_type,
        "operation_date": operation_date,
        "amount": amount
    }

    if shares is not None:
        payload["shares"] = shares

    response = client.post("/api/v1/operations", json=payload)
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    return body["data"]


def get_snapshot(client, blogger_id, snapshot_date=None):
    url = f"/api/v1/bloggers/{blogger_id}/position-snapshots"

    if snapshot_date is not None:
        url = f"{url}?snapshot_date={snapshot_date}"

    response = client.get(url)
    return response


def test_position_snapshots_rejects_invalid_blogger_id(client):
    response = get_snapshot(client, "abc")
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"

def test_position_snapshots_rejects_missing_blogger(client):
    response = get_snapshot(client, 999999)
    body = response.get_json()

    assert response.status_code == 404
    assert body["code"] == "BLOGGER_NOT_FOUND"


def test_position_snapshots_rejects_invalid_snapshot_date(client):
    blogger = create_blogger(client, name="快照日期错误博主")
    response = get_snapshot(client, blogger["blogger_id"], "bad-date")
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"


def test_position_snapshots_rejects_future_snapshot_date(client):
    blogger = create_blogger(client, name="快照未来日期博主")
    response = get_snapshot(client, blogger["blogger_id"], "2999-12-31")
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"


def test_position_snapshots_returns_empty_items(client):
    blogger = create_blogger(client, name="空快照博主")
    response = get_snapshot(client, blogger["blogger_id"], "2026-01-31")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["blogger_id"] == blogger["blogger_id"]
    assert body["data"]["snapshot_date"] == "2026-01-31"
    assert body["data"]["items"] == []


def test_position_snapshots_with_initial_position_only(client):
    blogger = create_blogger(client, name="初始持仓博主")
    fund = create_fund(
        client,
        name="初始持仓基金",
        fund_code="SNAP000002"
    )
    create_initial_position(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        shares=12000,
        cost_amount=15600,
        record_date="2026-01-01"
    )

    response = get_snapshot(client, blogger["blogger_id"], "2026-01-31")
    body = response.get_json()
    item = body["data"]["items"][0]

    assert response.status_code == 200
    assert body["code"] == 0
    assert item["fund_id"] == fund["fund_id"]
    assert item["initial_record_date"] == "2026-01-01"
    assert item["initial_shares"] == 12000
    assert item["initial_cost_amount"] == 15600
    assert item["buy_shares"] == 0
    assert item["sell_shares"] == 0
    assert item["dividend_cash_amount"] == 0
    assert item["shares"] == 12000
    assert item["cost_amount"] == 15600


def test_position_snapshots_with_buy_sell_and_dividend(client):
    blogger = create_blogger(client, name="买卖分红博主")
    fund = create_fund(
        client,
        name="买卖分红基金",
        fund_code="SNAP000003"
    )
    create_initial_position(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        shares=12000,
        cost_amount=15600,
        record_date="2026-01-01"
    )
    create_operation(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        operation_type="buy",
        operation_date="2026-01-10",
        shares=1000,
        amount=13000
    )
    create_operation(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        operation_type="sell",
        operation_date="2026-01-20",
        shares=300,
        amount=4200
    )
    create_operation(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        operation_type="dividend_cash",
        operation_date="2026-01-25",
        amount=120
    )

    response = get_snapshot(client, blogger["blogger_id"], "2026-01-31")
    body = response.get_json()
    item = body["data"]["items"][0]

    assert response.status_code == 200
    assert item["initial_shares"] == 12000
    assert item["initial_cost_amount"] == 15600
    assert item["buy_shares"] == 1000
    assert item["buy_amount"] == 13000
    assert item["sell_shares"] == 300
    assert item["sell_amount"] == 4200
    assert item["dividend_cash_amount"] == 120
    assert item["shares"] == 12700
    assert item["cost_amount"] == 27940