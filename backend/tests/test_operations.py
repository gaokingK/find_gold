from factories import create_blogger, create_fund

def create_operation(
    client,
    blogger_id,
    fund_id,
    operation_type="buy",
    operation_date="2020-01-02",
    shares=100,
    amount=1300,
    remark=None
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

    if remark is not None:
        payload["remark"] = remark

    response = client.post("/api/v1/operations", json=payload)
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    return body["data"]

def test_create_buy_operation(client):
    blogger = create_blogger(client, name="买入测试博主")
    fund = create_fund(client, name="买入测试基金", fund_code="OP000001")

    data = create_operation(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        operation_type="buy",
        shares=1000,
        amount=13000,
        remark="第一次买入"
    )

    assert data["operation_type"] == "buy"
    assert data["shares"] == 1000
    assert data["amount"] == 13000
    assert data["blogger_name"] == "买入测试博主"
    assert data["fund_name"] == "买入测试基金"
    assert data["fund_code"] == "OP000001"
    assert data["remark"] == "第一次买入"
    assert "operation_id" in data

def test_create_sell_operation(client):
    blogger = create_blogger(client, name="卖出测试博主")
    fund = create_fund(client, name="卖出测试基金", fund_code="OP000002")

    data = create_operation(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        operation_type="sell",
        shares=300,
        amount=4200
    )

    assert data["operation_type"] == "sell"
    assert data["shares"] == 300

def test_create_dividend_without_shares(client):
    blogger = create_blogger(client, name="分红测试博主")
    fund = create_fund(client, name="分红测试基金", fund_code="OP000003")

    data = create_operation(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        operation_type="dividend_cash",
        shares=None,
        remark=None
    )

    assert data["operation_type"] == "dividend_cash"
    assert data["shares"] == 0

def test_create_operation_rejects_unknown_type(client):
    blogger = create_blogger(client, name="非法类型博主")
    fund = create_fund(client, name="非法类型基金", fund_code="OP000004")

    response = client.post(
        "/api/v1/operations",
        json={
            "blogger_id": blogger["blogger_id"],
            "fund_id": fund["fund_id"],
            "operation_type": "transfer",
            "operation_date": "2020-01-02",
            "shares": 100,
            "amount": 1300
        }
    )
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"

def test_create_dividend_rejects_nonzero_shares(client):
    blogger = create_blogger(client, name="分红份额博主")
    fund = create_fund(client, name="分红份额基金", fund_code="OP000005")

    response = client.post(
        "/api/v1/operations",
        json={
            "blogger_id": blogger["blogger_id"],
            "fund_id": fund["fund_id"],
            "operation_type": "dividend_cash",
            "operation_date": "2020-01-02",
            "shares": 100,
            "amount": 120
        }
    )
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"

def test_create_buy_requires_shares(client):
    blogger = create_blogger(client, name="买入缺份额博主")
    fund = create_fund(client, name="买入缺份额基金", fund_code="OP000006")

    response = client.post(
        "/api/v1/operations",
        json={
            "blogger_id": blogger["blogger_id"],
            "fund_id": fund["fund_id"],
            "operation_type": "buy",
            "operation_date": "2020-01-01",
            "amount": 1300
        }
    )
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"

def test_create_operation_rejects_future_date(client):
    blogger = create_blogger(client, name="未来日期博主")
    fund = create_fund(client, name="未来日期基金", fund_code="OP000007")

    response = client.post(
        "/api/v1/operations",
        json={
            "blogger_id": blogger["blogger_id"],
            "fund_id": fund["fund_id"],
            "operation_type": "buy",
            "operation_date": "2099-01-01",
            "shares": 100,
            "amount": 1300
        }
    )
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"

def test_create_operation_with_missing_blogger(client):
  fund = create_fund(client, name="缺博主基金", fund_code="OP000008")

  response = client.post(
      "/api/v1/operations",
      json={
          "blogger_id": 999999,
          "fund_id": fund["fund_id"],
          "operation_type": "buy",
          "operation_date": "2020-01-02",
          "shares": 100,
          "amount": 1300
      }
  )
  body = response.get_json()

  assert response.status_code == 404
  assert body["code"] == "BLOGGER_NOT_FOUND"

def test_create_operation_with_missing_fund(client):
    blogger = create_blogger(client, name="缺基金博主")

    response = client.post(
        "/api/v1/operations",
        json={
            "blogger_id": blogger["blogger_id"],
            "fund_id": 999999,
            "operation_type": "buy",
            "operation_date": "2020-01-02",
            "shares": 100,
            "amount": 1300
        }
    )
    body = response.get_json()

    assert response.status_code == 404
    assert body["code"] == "FUND_NOT_FOUND"

def test_list_operation_returns_created_operation(client):
    blogger = create_blogger(client, name="查询列表博主")
    fund = create_fund(client, name="查询列表基金", fund_code="OP0000009")
    create_operation(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        remark="列表查询标记"
    )

    response = client.get("/api/v1/operations")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["remark"] == "列表查询标记"

def test_list_operations_filter_by_blogger(client):
    blogger_a = create_blogger(client, name="筛选博主A")
    blogger_b = create_blogger(client, name="筛选博主B")
    fund = create_fund(client, name="筛选基金", fund_code="OP000010")

    create_operation(
        client, 
        blogger_id=blogger_a["blogger_id"],
        fund_id=fund["fund_id"]
    )
    create_operation(
        client,
        blogger_id=blogger_b["blogger_id"],
        fund_id=fund["fund_id"]
    )

    response = client.get(
        f"/api/v1/operations?blogger_id={blogger_a['blogger_id']}"
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["blogger_name"] == "筛选博主A"

def test_list_operations_filter_by_type(client):
    blogger = create_blogger(client, name="类型筛选博主")
    fund = create_fund(client, name="类型筛选基金", fund_code="OP000011")

    create_operation(
        client, 
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        operation_type="buy",
        shares=100,
        amount=1300
    )
    create_operation(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        operation_type="dividend_cash",
        shares=None,
        amount=50
    )

    response = client.get("/api/v1/operations?operation_type=dividend_cash")
    body = response.get_json()

    assert response.status_code == 200
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["operation_type"] == "dividend_cash"

def test_list_operations_filter_by_date_range(client):
    blogger = create_blogger(client, name="日期筛选博主")
    fund = create_fund(client, name="日期筛选类型", fund_code="OP000012")

    create_operation(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        operation_date="2020-01-02"
    )
    create_operation(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        operation_date="2021-06-15"
    )

    response = client.get(
        "/api/v1/operations?date_from=2021-01-01&date_to=2021-12-31"
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["operation_date"] == "2021-06-15"

def test_list_operations_rejects_invalid_params(client):
    queries = [
        "page=0",
        "page_size=0",
        "page_size=101",
        "operation_type=transfer",
        "sort_by=password",
        "order=middle",
        "date_from=2021-13-45"
    ]

    for query in queries:
        response = client.get(f"/api/v1/operations?{query}")
        body = response.get_json()

        assert response.status_code == 400, f"参数 {query} 应该被拒绝"
        assert body["code"] == "VALIDATION_ERROR", f"参数 {query} 错误码不对"

def test_delete_operation_success(client):
    blogger = create_blogger(client, name="删除操作博主")
    fund = create_fund(client, name="删除操作基金", fund_code="OP000013")
    operation = create_operation(
        client, 
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"]
    )

    response = client.delete(
        f"/api/v1/operations/{operation['operation_id']}"
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["operation_id"] == operation["operation_id"]

    list_response = client.get("/api/v1/operations")

    assert list_response.get_json()["data"]["total"] == 0

def test_delete_operation_not_found(client):
    response = client.delete(f"/api/v1/operations/999999")
    body = response.get_json()

    assert response.status_code == 404
    assert body["code"] == "OPERATION_ERROR"

def test_delete_operation_with_invalid_id(client):
    for operation_id in ["0", "abc"]:
        response = client.delete(f"/api/v1/operations/{operation_id}")
        body = response.get_json()

        assert response.status_code == 400, f"ID {operation_id}"
        assert body["code"] == "VALIDATION_ERROR"

def test_delete_blogger_removes_operations(client):
    blogger = create_blogger(client, name="级联删除博主")
    fund = create_fund(client, name="级联删除博主", fund_code="OP000014")
    create_operation(
        client, 
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"]
    )

    response = client.delete(f"/api/v1/bloggers/{blogger['blogger_id']}")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    list_response = client.get("/api/v1/operations")

    assert list_response.get_json()["data"]["total"] == 0
