# 任务 032：持仓快照接口测试

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务要覆盖空数据、初始持仓、买入、卖出、分红、参数错误和博主不存在等场景。测试本身不复杂，但数据准备和断言较多。

## 任务目标

创建：

```text
backend/tests/test_position_snapshots.py
```

完成后可以：

1. 验证博主不存在时的错误响应。
2. 验证路径参数和日期参数错误。
3. 验证空数据返回空列表。
4. 验证只有初始持仓时的快照结果。
5. 验证买入、卖出、现金分红的计算结果。
6. `pytest -q` 全部通过。

## 范围说明

本任务只写接口测试。

不包含：

- 修改业务代码
- 修改数据库表结构
- 市值或收益率测试
- 持仓快照持久化测试

## 前置条件

1. 任务 031 已完成，快照接口可用。
2. `pytest -q` 当前全部通过。
3. 测试数据库隔离已经生效。

## 新概念：接口测试场景

接口测试要覆盖正常场景和错误场景。  
本任务重点关注：

1. 正常计算。
2. 空数据。
3. 参数错误。
4. 资源不存在。

## 执行目录

```bash
cd /d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建测试文件

**必要性：**  
快照是新模块，单独建一个测试文件，避免和其他模块混在一起。

新建文件：

```text
backend/tests/test_position_snapshots.py
```

先写公共辅助函数：

```python
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
```

---

### 步骤 2：添加错误场景测试

**必要性：**  
接口必须能正确处理路径参数、日期参数和不存在的博主。

添加：

```python
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
```

---

### 步骤 3：添加空数据测试

**必要性：**  
博主存在但没有任何持仓和操作时，接口应该返回空列表，而不是报错。

添加：

```python
def test_position_snapshots_returns_empty_items(client):
    blogger = create_blogger(client, name="空快照博主")
    response = get_snapshot(client, blogger["blogger_id"], "2026-01-31")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["blogger_id"] == blogger["blogger_id"]
    assert body["data"]["snapshot_date"] == "2026-01-31"
    assert body["data"]["items"] == []
```

---

### 步骤 4：添加只有初始持仓的测试

**必要性：**  
初始持仓是快照起点，必须先确认它没有变化时能正确返回。

添加：

```python
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
```

---

### 步骤 5：添加买入、卖出、分红测试

**必要性：**  
这是快照的核心计算场景，必须验证三种操作都能参与计算。

添加：

```python
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
```

这里的成本计算依据是：

- 初始成本：`15600`
- 买入后成本：`15600 + 13000 = 28600`
- 买入后份额：`12000 + 1000 = 13000`
- 卖出前平均成本：`28600 / 13000 = 2.2`
- 卖出 300 份扣减成本：`2.2 * 300 = 660`
- 卖出后成本：`28600 - 660 = 27940`

---

### 步骤 6：运行全部测试

**必要性：**  
确认新测试通过，并且没有影响已有模块。

执行：

```bash
pytest -q
```

预期全部通过。

## 验证方式

### 1. 专项测试

```bash
pytest tests/test_position_snapshots.py -q
```

预期全部通过。

### 2. 全量测试

```bash
pytest -q
```

预期全部通过。

## 常见坑

### 1. 测试数据日期写错

操作日期必须晚于或等于初始持仓日期。  
否则新增操作记录接口会返回参数错误。

### 2. 只测正常场景

接口错误场景同样重要。  
不要只测成功请求。

### 3. 期望值算错

卖出成本使用平均成本法。  
写断言前先手动算一遍。

## 完成标准

以下条件全部满足，任务 032 才算完成：

1. `backend/tests/test_position_snapshots.py` 已创建。
2. 错误参数、空数据、初始持仓、买入、卖出、分红场景都有测试。
3. `pytest tests/test_position_snapshots.py -q` 全部通过。
4. `pytest -q` 全部通过。

## 完成后请反馈

1. 新增和修改的文件列表。
2. `pytest tests/test_position_snapshots.py -q` 的完整输出。
3. `pytest -q` 的完整输出。
4. 是否发现接口文档和实际行为不一致。
5. 遇到的问题和未完成项。
