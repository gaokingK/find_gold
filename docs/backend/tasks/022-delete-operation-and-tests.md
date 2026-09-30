# 任务 022：实现删除操作记录接口并补齐操作记录测试

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务包含三件事——实现删除操作记录接口、修复删除博主时的外键冲突、编写操作记录模块的接口测试。前两件各约 30 分钟，测试约 1 小时。

## 任务目标

完成后可以：

1. 通过 `DELETE /api/v1/operations/{operation_id}` 删除录错的操作记录。
2. 删除博主时能正常级联删除他的操作记录，不再被外键拦住。
3. 操作记录模块有自动化测试，覆盖新增、查询、删除和主要错误场景。
4. `pytest -q` 全部通过。

## 范围说明

本任务包含：

- `DELETE /api/v1/operations/{operation_id}`
- 修改 `DELETE /api/v1/bloggers/{blogger_id}` 的删除顺序
- `backend/tests/test_operations.py`

不包含：

- 编辑操作记录（`PUT`，第一版不做，录错就删了重录）
- 操作记录详情接口（第一版不做）
- 持仓快照计算
- 收益计算
- 权限校验

## 前置条件

1. 任务 020 已完成，`POST /api/v1/operations` 可用。
2. 任务 021 已完成，`GET /api/v1/operations` 可用。
3. 任务 017 已完成，`backend/tests/factories.py` 里有 `create_blogger()` 和 `create_fund()`。
4. 任务 019 的步骤 7 已完成，`tests/conftest.py` 会创建并清空 `operations` 表。

## 实现依据

接口契约在：

```text
docs/api/v1-operations.md
```

第 6 节写了删除接口的完整定义。  
博主删除的级联规则在：

```text
docs/api/v1-basic-management.md
```

看博主删除接口那一节的「业务规则」。

## 新概念：为什么删除博主会被外键拦住

任务 019 建 `operations` 表时，两个外键都**没有**加 `ON DELETE CASCADE`：

```sql
CONSTRAINT fk_operations_blogger
    FOREIGN KEY (blogger_id) REFERENCES bloggers(id),
```

`ON DELETE CASCADE` 的意思是「删父记录时数据库自动删掉子记录」。没加它，数据库的行为是**拒绝**删除还有子记录的父记录。

所以现在的情况是：

```text
博主 1 有 3 条操作记录
    ↓
DELETE /api/v1/bloggers/1
    ↓
MySQL 报错：Cannot delete or update a parent row: a foreign key constraint fails
```

这不是任务 010 写错了，而是那时候 `operations` 表还不存在。表一建出来，原来能跑通的删除接口就坏了——这种「新表把旧接口打坏」的情况很常见，所以建新表后要回头检查有哪些接口会受影响。

有两种修法：

| 修法 | 做法 | 本项目是否采用 |
| --- | --- | --- |
| 数据库层 | 给外键加 `ON DELETE CASCADE` | 不采用 |
| 应用层 | 删博主前，先在同一个事务里删掉他的操作记录 | **采用** |

选应用层的原因：删除是不可逆操作，写在 Python 代码里能看见删了什么、顺序是什么，出问题时容易查。`ON DELETE CASCADE` 藏在建表语句里，代码里看不出来，容易在某次删除时连带删掉比预期多得多的数据。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=你的数据库密码
```

数据库密码只通过环境变量传入，不要写进任何会提交到 Git 的文件。

## 具体步骤

### 步骤 1：先复现删除博主的外键错误

**必要性：**  
直接改代码，你不会知道自己修的是不是真问题。先制造一次失败，确认问题存在，修完再看它消失——这样才能确定修对了。

启动服务：

```bash
python run.py
```

另开一个终端，准备一条操作记录：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/bloggers" \
  -H "Content-Type: application/json" \
  -d '{"name":"外键复现博主","sector":"成长股","observe_start_date":"2026-01-01"}'

curl -X POST "http://127.0.0.1:5000/api/v1/funds" \
  -H "Content-Type: application/json" \
  -d '{"name":"外键复现基金","fund_code":"FKTEST01"}'
```

记下返回的 `blogger_id` 和 `fund_id`，下面假设都是 `1`。

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"operation_type":"buy","operation_date":"2026-01-02","shares":100,"amount":1300}'
```

现在删除这个博主：

```bash
curl -i -X DELETE "http://127.0.0.1:5000/api/v1/bloggers/1"
```

预期失败。可能是 HTTP 500，也可能是 Flask 直接抛出异常栈，取决于任务 010 的错误处理怎么写的。在 `python run.py` 那个终端里应该能看到：

```text
Cannot delete or update a parent row: a foreign key constraint fails
```

**把这个输出记下来**，反馈时要贴。看到它说明问题复现成功，可以往下修了。

---

### 步骤 2：修改删除博主的实现

**必要性：**  
博主删除接口现在是坏的。前端点「删除博主」会报 500，必须先修好。

修改文件：

```text
backend/app/routes/bloggers.py
```

找到删除博主的路由，在删 `initial_positions` 之前加一条删 `operations`。

修改后的删除部分大致是这样：

```python
            cursor.execute(
                "DELETE FROM operations WHERE blogger_id = %s",
                (blogger_id,)
            )
            cursor.execute(
                "DELETE FROM initial_positions WHERE blogger_id = %s",
                (blogger_id,)
            )
            cursor.execute(
                "DELETE FROM bloggers WHERE id = %s",
                (blogger_id,)
            )
        conn.commit()
```

三条 `DELETE` 的顺序说明：

1. 先删 `operations`（子表）。
2. 再删 `initial_positions`（子表）。
3. 最后删 `bloggers`（父表）。

子表必须在父表之前删。反过来写第 3 条就会报外键错误。

`operations` 和 `initial_positions` 之间没有外键关系，这两条谁先谁后都可以。这里把 `operations` 放前面，是为了让「操作记录」这个较新的表在代码里更显眼，以后再加新子表时知道往哪里插。

注意 `conn.commit()` 必须在三条 `DELETE` 都执行完之后，只调用一次。这样三条删除是同一个事务：要么全部生效，要么全部不生效。如果每删一条就 `commit()` 一次，万一第三条失败，博主还在但他的操作记录已经没了——数据就烂掉了。

---

### 步骤 3：验证删除博主已修好

**必要性：**  
确认步骤 1 里复现的错误确实消失了。

重启服务，然后重复步骤 1 的数据准备，再删一次：

```bash
curl -i -X DELETE "http://127.0.0.1:5000/api/v1/bloggers/1"
```

预期返回 `code: 0`，HTTP 状态码 `200`。

再确认操作记录也没了：

```bash
curl "http://127.0.0.1:5000/api/v1/operations?blogger_id=1"
```

预期 `data.total` 是 `0`。

---

### 步骤 4：添加路径参数校验辅助

**必要性：**  
删除接口要处理非法的 `operation_id`，例如 `0`、`-1`、`abc`。这些应该返回 `400`，不是 `404`，也不是 500。

`operations.py` 里已经有 `parse_positive_int()`（任务 020 写的），直接用它，不用再写一个。

---

### 步骤 5：实现删除操作记录接口

**必要性：**  
第一版没有编辑接口，录错的记录只能删掉重录。没有删除接口，错数据就永远留在库里，后面算持仓和收益全是错的。

在 `backend/app/routes/operations.py` 末尾添加：

```python
@operations_bp.delete("/api/v1/operations/<operation_id>")
def delete_operation(operation_id):
    parsed_operation_id = parse_positive_int(operation_id)

    if parsed_operation_id is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "operation_id",
                    "message": "操作记录 ID 必须为正整数"
                }
            ],
            http_status=400
        )

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM operations WHERE id = %s",
                (parsed_operation_id,)
            )

            if cursor.fetchone() is None:
                return error(
                    code="OPERATION_NOT_FOUND",
                    message="操作记录不存在",
                    details=[],
                    http_status=404
                )

            cursor.execute(
                "DELETE FROM operations WHERE id = %s",
                (parsed_operation_id,)
            )
        conn.commit()
    finally:
        conn.close()

    return success(data={"operation_id": parsed_operation_id})
```

说明：

- 路由写成 `<operation_id>` 而不是 `<int:operation_id>`。用 `<int:...>` 时，Flask 遇到 `abc` 会直接返回 HTML 404，前端拿不到统一的 JSON 错误结构。接成字符串再自己校验，才能返回 `VALIDATION_ERROR`。这和博主模块的处理方式一致。
- 删除前先 `SELECT` 一次确认存在。不查直接删，`DELETE` 对不存在的 ID 也会「成功」（影响 0 行），前端无法区分「删掉了」和「本来就没有」。
- 返回 `{"operation_id": 1}` 而不是 `null`，让前端知道删的是哪一条。这和接口文档第 6 节一致。

---

### 步骤 6：重启并用 curl 验证删除接口

**必要性：**  
接口代码写完必须实际跑一次，确认路由注册生效、SQL 没写错。

```bash
python run.py
```

准备一条记录并删掉：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":2,"fund_id":1,"operation_type":"buy","operation_date":"2026-01-02","shares":100,"amount":1300}'
```

记下返回的 `operation_id`，假设是 `5`：

```bash
curl -i -X DELETE "http://127.0.0.1:5000/api/v1/operations/5"
curl -i -X DELETE "http://127.0.0.1:5000/api/v1/operations/5"
curl -i -X DELETE "http://127.0.0.1:5000/api/v1/operations/0"
curl -i -X DELETE "http://127.0.0.1:5000/api/v1/operations/abc"
```

预期依次是：

1. `code: 0`，HTTP `200`，`data.operation_id` 是 `5`。
2. `OPERATION_NOT_FOUND`，HTTP `404`（已经删掉了）。
3. `VALIDATION_ERROR`，HTTP `400`。
4. `VALIDATION_ERROR`，HTTP `400`，**不是** HTML 404 页面。

第 4 条要特别看一眼响应体是不是 JSON。如果是 HTML，说明路由写成了 `<int:operation_id>`。

---

### 步骤 7：创建操作记录测试文件

**必要性：**  
操作记录是第 7 天持仓快照和第 8 天收益计算的数据来源。这部分逻辑一旦被改坏，后面所有计算都是错的，而且很难看出来。必须有测试守住。

新建文件：

```text
backend/tests/test_operations.py
```

第一行导入工厂函数：

```python
from factories import create_blogger, create_fund
```

再添加一个本文件用的辅助函数：

```python
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
```

说明：`shares=None` 时不把这个字段放进请求体，用来测现金分红省略 `shares` 的场景。注意这和 `shares=0` 不是一回事——`0` 会被传出去，`None` 是整个字段都不传。

---

### 步骤 8：编写新增场景测试

**必要性：**  
三种操作类型的字段规则不一样，每一种都要测到。

添加：

```python
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
        amount=120
    )

    assert data["operation_type"] == "dividend_cash"
    assert data["shares"] == 0
```

最后那个 `assert data["shares"] == 0` 是这一组里最重要的一条断言：它确认了后端在调用方省略 `shares` 时自己补了 `0`，而不是写进 `NULL` 或者报错。

---

### 步骤 9：编写新增错误场景测试

**必要性：**  
字段校验是防止脏数据进库的唯一屏障。这些规则最容易在后续「顺手简化一下」时被去掉。

添加：

```python
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
            "operation_date": "2020-01-02",
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
```

注意 `test_create_operation_rejects_future_date` 用的是固定的 `2099-01-01`。这个测试在 2099 年之前都有效，够用了。不要写成「今天 + 1 天」那种动态日期——看起来更严谨，但读测试的人要在脑子里算日期，反而更难理解。

---

### 步骤 10：编写查询场景测试

**必要性：**  
查询接口有筛选、分页、排序和白名单，是本模块第二密的一段逻辑。

添加：

```python
def test_list_operations_returns_created_operation(client):
    blogger = create_blogger(client, name="查询列表博主")
    fund = create_fund(client, name="查询列表基金", fund_code="OP000009")
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
    fund = create_fund(client, name="日期筛选基金", fund_code="OP000012")

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
        "date_from=2021-13-45",
    ]

    for query in queries:
        response = client.get(f"/api/v1/operations?{query}")
        body = response.get_json()

        assert response.status_code == 400, f"参数 {query} 应该被拒绝"
        assert body["code"] == "VALIDATION_ERROR", f"参数 {query} 错误码不对"
```

最后那个测试里的 `assert ..., f"参数 {query} 应该被拒绝"` 是 pytest 的断言消息。循环里有 7 个参数，不写消息的话失败时只能看到「400 != 200」，不知道是哪个参数漏了校验。加上消息，报错直接告诉你是哪一个。

`sort_by=password` 这一条尤其重要：排序字段是直接拼进 SQL 的（`ORDER BY {sort_column}`），如果白名单被去掉，就是 SQL 注入漏洞。

---

### 步骤 11：编写删除场景测试

**必要性：**  
删除接口是本任务新写的代码，必须自测。级联删除也要测——它是本任务修的那个 bug 的回归测试。

添加：

```python
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
    response = client.delete("/api/v1/operations/999999")
    body = response.get_json()

    assert response.status_code == 404
    assert body["code"] == "OPERATION_NOT_FOUND"


def test_delete_operation_with_invalid_id(client):
    for operation_id in ["0", "abc"]:
        response = client.delete(f"/api/v1/operations/{operation_id}")
        body = response.get_json()

        assert response.status_code == 400, f"ID {operation_id} 应该被拒绝"
        assert body["code"] == "VALIDATION_ERROR"


def test_delete_blogger_removes_operations(client):
    blogger = create_blogger(client, name="级联删除博主")
    fund = create_fund(client, name="级联删除基金", fund_code="OP000014")
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
```

`test_delete_blogger_removes_operations` 是本任务最有价值的一个测试。  
它锁住了步骤 2 修的那个 bug：以后有人把 `bloggers.py` 里那条 `DELETE FROM operations` 删掉，这个测试立刻红。没有它，这个 bug 会一直等到某天真的有人删博主时才暴露。

---

### 步骤 12：运行全部测试

**必要性：**  
必须确认新测试通过，而且没有影响前面 26 个测试。

```bash
pytest -q
```

预期全部通过，测试总数不少于 44 个（第 4 天留下 26 个，本任务新增 18 个）。

具体数字可能因为后续调整而变化，重点是：**没有 failed，也没有 error**。

如果只想跑本任务的测试：

```bash
pytest -q tests/test_operations.py
```

但最终验收必须跑完整的 `pytest -q`。

## 验证方式

### 1. 自动化测试

```bash
pytest -q
```

预期全部通过。

### 2. 删除接口的 curl 验证

见步骤 6，四条命令的结果都要符合预期。

### 3. 删除博主不再报外键错误

```bash
grep -n "DELETE FROM operations" app/routes/bloggers.py
```

预期能看到一行。

### 4. 确认没有实现 PUT 接口

第一版不做编辑操作记录。

```bash
grep -n "operations_bp.put" app/routes/operations.py
```

预期没有输出。如果有，说明做了范围外的东西，请说明原因。

## 常见坑

### 1. 删除顺序写反

```python
cursor.execute("DELETE FROM bloggers WHERE id = %s", (blogger_id,))
cursor.execute("DELETE FROM operations WHERE blogger_id = %s", (blogger_id,))
```

这样写第一条就会报外键错误。必须先删子表，再删父表。

### 2. 每删一条就 commit 一次

三条 `DELETE` 必须在同一个事务里，最后统一 `conn.commit()`。  
分开提交时，中间任何一条失败都会留下半删的数据。

### 3. 用 `<int:operation_id>` 写路由

```python
@operations_bp.delete("/api/v1/operations/<int:operation_id>")
```

这样 `/api/v1/operations/abc` 会返回 Flask 默认的 HTML 404 页面，前端解析 JSON 会报错。  
正确写法是接成字符串，再用 `parse_positive_int()` 自己校验。

### 4. 删除前不查存在性

直接 `DELETE FROM operations WHERE id = 999999` 不会报错，只是影响 0 行。  
如果不先 `SELECT`，前端删一个不存在的 ID 也会收到成功响应。

### 5. 想顺手把 `ON DELETE CASCADE` 加上

不要改 `database/v2-operations.sql` 的外键定义。  
本项目的约定是在应用层控制删除顺序，理由见上面「新概念」一节。  
如果你认为数据库层更好，可以反馈，但不要自己改——改了之后已经建好的表不会自动更新，开发库和测试库的行为会不一致，非常难查。

### 6. 测试里假设 `total` 是某个大于 1 的数

`clean_db` 每个测试前都会清空 `operations`，所以每个测试里的数据只有自己创建的那几条。  
断言可以直接写 `== 1`、`== 0`，不用写 `>= 1`。这样断言更强，能发现「筛选条件没生效，返回了多余数据」这类问题。

反过来，如果你发现某个测试必须写 `>= 1` 才能过，说明 `clean_db` 没清 `operations` 表——回去检查任务 019 的步骤 7。

### 7. 基金代码在测试里撞车

本文件里用了 `OP000001` 到 `OP000014`。新增测试时接着往后编号，不要复用。  
虽然 `clean_db` 会清表，但同一个测试函数里建两只基金用同一个代码，仍然会撞 `FUND_CODE_DUPLICATED`。

### 8. 忘记 `operations` 的测试数据日期要晚于初始持仓

本文件的测试都没有创建初始持仓，所以操作日期没有下界限制。  
如果你新增的测试里先建了初始持仓，那么操作日期必须晚于或等于它的 `record_date`，否则会返回 `400`。

## 完成标准

以下条件全部满足，任务 022 才算完成：

1. 步骤 1 的外键错误已复现并记录。
2. `app/routes/bloggers.py` 里删除博主时会先删 `operations`，再删 `initial_positions`，最后删 `bloggers`。
3. 三条 `DELETE` 共用一个 `conn.commit()`。
4. `DELETE /api/v1/operations/{operation_id}` 可以删除记录，返回 `200` 和 `{"operation_id": ...}`。
5. 删除不存在的 ID 返回 `404` 和 `OPERATION_NOT_FOUND`。
6. 非法 ID（`0`、`abc`）返回 `400` 和 `VALIDATION_ERROR`，且响应体是 JSON 不是 HTML。
7. `backend/tests/test_operations.py` 存在，并从 `factories` 导入工厂函数。
8. 测试覆盖：三种操作类型新增、分红省略 `shares`、非法类型、分红份额非 0、买入缺份额、未来日期、博主/基金不存在。
9. 测试覆盖：列表查询、按博主筛选、按类型筛选、按日期区间筛选、非法查询参数。
10. 测试覆盖：删除成功、删除不存在、删除非法 ID、删除博主级联删除操作记录。
11. 没有实现 `PUT /api/v1/operations/{operation_id}`。
12. `pytest -q` 全部通过，没有 failed 也没有 error，总数不少于 44 个。

## 完成后请反馈

1. 新增和修改的文件列表。
2. 步骤 1 复现的外键错误原文。
3. 步骤 6 四条 curl 命令的结果。
4. `pytest -q` 的完整输出。
5. 测试函数数量。
6. 响应字段是否和 `docs/api/v1-operations.md` 第 6 节一致。
7. 有没有发现接口文档里说不通的地方。
8. 遇到的问题和未完成项。
