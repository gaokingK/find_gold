# 任务 017：编写基金与初始持仓接口测试

## 预计完成时间

预计完成时间：约 1.5 小时。

估算依据：本任务需要测试基金模块和初始持仓模块；工厂函数在任务 016 已经写好，可以直接复用，本任务只需新增初始持仓的工厂函数和两个测试文件。

## 任务目标

为基金和初始持仓模块建立自动化测试。

完成后可以：

1. 自动验证基金新增、列表、编辑。
2. 自动验证基金代码重复错误。
3. 自动验证初始持仓新增、列表、编辑。
4. 自动验证博主或基金不存在时的错误。
5. 自动验证同一博主、基金、记录日期的重复数据。

## 范围说明

本任务只测试基金和初始持仓接口。

不包含：

- 博主模块测试
- 前端测试
- 性能测试
- 定时任务测试

## 前置条件

1. 任务 015 已完成，测试数据库隔离和 `clean_db` fixture 可用。
2. 任务 016 已完成，`backend/tests/factories.py` 里已有 `create_blogger()` 和 `create_fund()`。
3. 任务 011 已完成，基金接口可用。
4. 任务 012 已完成，初始持仓接口可用。
5. `pytest -q` 全部通过。

## 断言的依据

所有断言必须对照接口文档写，不要照着路由代码写：

```text
docs/api/v1-basic-management.md
```

特别注意：本项目所有新增接口成功时返回 `200`，不是 `201`。  
如果实际跑出来是 `201`，说明 `funds.py` 或 `initial_positions.py` 里给 `success()` 传了 `http_status=201`，这是需要修的代码缺陷，不要去改断言。排查命令：

```bash
grep -rn "http_status=201" app/
```

预期没有任何输出。

## 新概念：关联查询测试

关联查询测试是验证多表数据组合后返回是否正确。  
比如初始持仓接口不仅要返回 `blogger_id` 和 `fund_id`，还要返回 `blogger_name`、`fund_name`、`fund_code`。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建基金测试文件

**必要性：**  
基金模块测试先独立完成，再测试更复杂的初始持仓模块。

新建文件：

```text
backend/tests/test_funds.py
```

第一行导入任务 016 已经写好的工厂函数：

```python
from factories import create_fund
```

说明：

- `create_fund()` 定义在 `backend/tests/factories.py`，不要在本文件里重新写一份。工厂函数只应该有一处定义，以后改字段只改一个地方。
- `tests` 目录里没有 `__init__.py`，pytest 会把 `tests` 目录本身加入模块搜索路径，所以写 `from factories import ...`，不要写成 `from tests.factories import ...`。
- 如果 `factories.py` 不存在，说明任务 016 没做完，先回去补上，不要在这里另起一份。

---

### 步骤 2：编写基金成功场景测试

**必要性：**  
先确认基金新增、列表和编辑的基本能力可用。

添加：

```python
def test_create_fund_success(client):
    data = create_fund(client, name="基金新增测试", fund_code="F000001")

    assert data["name"] == "基金新增测试"
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
```

---

### 步骤 3：编写基金错误场景测试

**必要性：**  
基金代码要求唯一，必须自动验证重复代码会被拒绝。

添加：

```python
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
```

---

### 步骤 4：创建初始持仓测试文件

**必要性：**  
初始持仓依赖博主和基金，需要测试多表关联和错误处理。

新建文件：

```text
backend/tests/test_initial_positions.py
```

第一行同样从 `factories` 导入博主和基金的工厂函数：

```python
from factories import create_blogger, create_fund
```

初始持仓的工厂函数只有本文件会用到，直接写在本文件里就行，不用放进 `factories.py`：

```python
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
```

---

### 步骤 5：编写初始持仓成功场景测试

**必要性：**  
初始持仓是核心业务数据，必须确认关联字段可以正确返回。

添加：

```python
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
            "shares": 13000,
            "cost_amount": 16000,
            "record_date": "2020-01-01"
        }
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["shares"] == 13000
    assert body["data"]["cost_amount"] == 16000
```

---

### 步骤 6：编写初始持仓错误场景测试

**必要性：**  
初始持仓依赖博主和基金，必须自动验证资源不存在和重复数据。

添加：

```python
def test_create_initial_position_with_missing_blogger(client):
    fund = create_fund(client, name="缺失博主基金", fund_code="POSITION004")

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
    blogger = create_blogger(client, name="缺失基金博主")

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
    assert body["code"] == "FUND_NOT_FOUND"


def test_create_initial_position_with_duplicate_data(client):
    blogger = create_blogger(client, name="重复持仓博主")
    fund = create_fund(client, name="重复持仓基金", fund_code="POSITION005")

    create_initial_position(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"]
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
```

---

### 步骤 7：运行全部测试

**必要性：**  
需要确认新测试和之前的博主测试一起运行时不互相影响。

执行：

```bash
pytest -q
```

预期全部通过，测试总数不少于 26 个（014 和 015 留下 3 个，016 新增 12 个，本任务新增 11 个）。

具体数字可能因为后续调整而变化，重点是：**没有 failed，也没有 error**。

## 验证方式

执行：

```bash
pytest -q
```

如果看到所有测试通过，说明基金和初始持仓模块的接口测试完成。

## 常见坑

### 1. 测试数据名称或代码重复

如果测试数据固定，又没有清空数据库，可能出现重复数据。  
确认 `clean_db` fixture 在每个测试前清空三张表。

### 2. 初始持仓依赖数据创建失败

如果博主或基金创建失败，后面的初始持仓测试也会失败。  
辅助函数里应该直接断言创建成功，方便定位问题。

### 3. 只断言状态码

不要只写：

```python
assert response.status_code == 200
```

还要检查 `code`、`data` 和关键字段。

### 4. 断言数据库自动生成字段的具体值

`created_at`、`updated_at` 是自动生成的，不应该断言固定值。

### 5. 忘记测试错误场景

只测正常场景不能保证接口稳定。  
必须测试资源不存在、重复数据和参数错误。

### 6. 把工厂函数又复制了一份

`create_blogger()` 和 `create_fund()` 只应该存在于 `tests/factories.py` 一处。

检查命令：

```bash
grep -rn "def create_blogger\|def create_fund" tests/
```

预期只有两行输出，都来自 `tests/factories.py`。  
如果 `test_funds.py` 或 `test_initial_positions.py` 里也出现了定义，删掉它们，改成从 `factories` 导入。

## 完成标准

以下条件全部满足，任务 017 才算完成：

1. `backend/tests/test_funds.py` 存在，并且从 `factories` 导入 `create_fund`。
2. `backend/tests/test_initial_positions.py` 存在，并且从 `factories` 导入 `create_blogger` 和 `create_fund`。
3. 基金模块至少覆盖新增、列表、编辑、重复代码、缺字段。
4. 初始持仓模块至少覆盖新增、列表、编辑、博主不存在、基金不存在、重复数据。
5. `grep -rn "def create_blogger\|def create_fund" tests/` 只在 `tests/factories.py` 里有定义。
6. `pytest -q` 全部通过，没有 failed 也没有 error，测试总数不少于 26 个。
7. 测试不依赖手工启动 Flask 服务。

## 完成后请反馈

1. 新增的文件列表。
2. 测试函数数量。
3. `pytest -q` 的完整输出。
4. 断言是否都对照 `docs/api/v1-basic-management.md` 核对过。
5. 有没有发现代码和接口文档不一致的地方。
6. 哪些场景没有覆盖。
7. 遇到的问题和未完成项。
