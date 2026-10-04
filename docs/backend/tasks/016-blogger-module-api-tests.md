# 任务 016：编写博主模块接口测试

## 预计完成时间

预计完成时间：约 1.5 小时。

估算依据：本任务需要为博主模块写一组接口测试，覆盖新增、列表、详情、编辑、删除、列表参数校验和错误场景；测试代码本身都很短，主要工作量是照着接口文档逐条核对断言。

## 任务目标

为博主模块建立自动化测试。

完成后可以：

1. 自动验证新增博主接口。
2. 自动验证博主名称重复错误。
3. 自动验证列表、详情、编辑、删除接口。
4. 自动验证列表接口的排序白名单和分页边界。
5. 自动验证路径参数错误。
6. 修改博主模块代码后，可以用测试快速发现回归问题。

## 断言的依据

所有断言必须对照接口文档写，不要照着 `app/routes/bloggers.py` 的代码写。

```text
docs/api/v1-basic-management.md
```

理由：接口文档是前后端唯一契约。  
如果照着代码写断言，测试只是把当前实现固定下来；万一实现和文档不一致，测试还会帮着把错误行为锁死。  
发现代码和文档不一致时，先停下来反馈，不要自己改文档也不要改断言。

## 范围说明

本任务只测试博主模块接口。

不包含：

- 基金模块测试
- 初始持仓模块测试
- 前端测试
- 性能测试

## 前置条件

1. 任务 015 已完成，测试数据库隔离和 `clean_db` fixture 可用。
2. 任务 010 已完成，博主详情、编辑、删除接口可用。
3. `pytest -q` 至少有 3 个测试通过。

## 新概念：接口测试、happy path、error path

### 接口测试

接口测试是直接请求 API，验证响应状态码和 JSON 数据是否符合预期。

### happy path

happy path 是正常场景。  
例如新增博主时传入合法字段，期望返回成功。

### error path

error path 是异常场景。  
例如传入空名称、重复名称、不存在的 ID，期望返回统一错误结构。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建共享测试数据工厂

**必要性：**  
多个测试文件都需要「先建一个博主」「先建一只基金」。如果每个文件各写一份，下一个任务 017 就会出现第二份、第三份重复代码，改一个字段要改好几处。  
所以先把这类函数集中到一个共享文件里。

新建文件：

```text
backend/tests/factories.py
```

内容：

```python
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
            "name": name,
            "fund_code": fund_code
        }
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    return body["data"]
```

说明：

- 这个文件不是测试文件，里面的函数不能以 `test_` 开头，否则 pytest 会把它们当成测试用例执行。
- 两个函数内部都断言了 `status_code == 200` 和 `code == 0`。这样一旦准备数据的步骤失败，报错位置就在工厂函数里，很容易定位，而不是在后面某个断言上莫名失败。
- 本项目所有新增接口成功时都返回 `200`，不是 `201`。

---

### 步骤 2：创建博主测试文件

**必要性：**  
博主模块的测试集中放在一个文件里，后续维护更方便。

新建文件：

```text
backend/tests/test_bloggers.py
```

第一行先导入工厂函数：

```python
from factories import create_blogger
```

说明：`tests` 目录里没有 `__init__.py`，pytest 会把 `tests` 目录本身加入模块搜索路径，所以这里直接写 `from factories import ...`，不要写成 `from tests.factories import ...`。

---

### 步骤 3：新增成功场景测试

**必要性：**  
先验证最基础的创建能力。这个测试通过后，说明测试环境和博主新增接口都能正常工作。

添加：

```python
def test_create_blogger_success(client):
    data = create_blogger(client, name="新增成功博主")

    assert data["name"] == "新增成功博主"
    assert data["sector"] == "成长股"
    assert data["observe_start_date"] == "2020-01-01"
    assert "blogger_id" in data
```

---

### 步骤 4：新增重复名称测试

**必要性：**  
博主名称要求唯一。这个测试可以防止以后有人误删重复校验。

添加：

```python
def test_create_blogger_with_duplicate_name(client):
    create_blogger(client, name="重复名称博主")

    response = client.post(
        "/api/v1/bloggers",
        json={
            "name": "重复名称博主",
            "sector": "价值股",
            "observe_start_date": "2020-01-01"
        }
    )
    body = response.get_json()

    assert response.status_code == 409
    assert body["code"] == "BLOGGER_NAME_DUPLICATED"
```

---

### 步骤 5：新增列表和详情测试

**必要性：**  
列表页和详情页都依赖这两个接口，必须确认返回字段完整。

添加：

```python
def test_list_bloggers_returns_created_blogger(client):
    create_blogger(client, name="列表测试博主")

    response = client.get("/api/v1/bloggers")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["total"] >= 1
    assert any(
        item["name"] == "列表测试博主"
        for item in body["data"]["items"]
    )


def test_get_blogger_detail(client):
    blogger = create_blogger(client, name="详情测试博主")

    response = client.get(f"/api/v1/bloggers/{blogger['blogger_id']}")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["name"] == "详情测试博主"
```

---

### 步骤 6：新增编辑测试

**必要性：**  
编辑接口可能会影响观察天数和状态，必须防止以后误改。

添加：

```python
def test_update_blogger_success(client):
    blogger = create_blogger(client, name="编辑前博主")

    response = client.put(
        f"/api/v1/bloggers/{blogger['blogger_id']}",
        json={
            "name": "编辑后博主",
            "sector": "价值股",
            "observe_start_date": "2020-01-01"
        }
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["name"] == "编辑后博主"
    assert body["data"]["sector"] == "价值股"


def test_update_blogger_with_duplicate_name(client):
    blogger_a = create_blogger(client, name="博主A")
    create_blogger(client, name="博主B")

    response = client.put(
        f"/api/v1/bloggers/{blogger_a['blogger_id']}",
        json={
            "name": "博主B",
            "sector": "价值股",
            "observe_start_date": "2020-01-01"
        }
    )
    body = response.get_json()

    assert response.status_code == 409
    assert body["code"] == "BLOGGER_NAME_DUPLICATED"
```

---

### 步骤 7：新增删除测试

**必要性：**  
删除接口涉及数据一致性，必须自动验证博主可以被删除。

添加：

```python
def test_delete_blogger_success(client):
    blogger = create_blogger(client, name="删除测试博主")

    response = client.delete(f"/api/v1/bloggers/{blogger['blogger_id']}")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    detail_response = client.get(f"/api/v1/bloggers/{blogger['blogger_id']}")
    detail_body = detail_response.get_json()

    assert detail_response.status_code == 404
    assert detail_body["code"] == "BLOGGER_NOT_FOUND"
```

---

### 步骤 8：新增错误路径测试

**必要性：**  
不能只测正常请求。前端需要统一错误结构，必须确认非法 ID 和缺字段请求会被拦截。

添加：

```python
def test_get_blogger_with_invalid_id(client):
    for blogger_id in ["0", "abc"]:
        response = client.get(f"/api/v1/bloggers/{blogger_id}")
        body = response.get_json()

        assert response.status_code == 400
        assert body["code"] == "VALIDATION_ERROR"


def test_create_blogger_with_missing_fields(client):
    response = client.post(
        "/api/v1/bloggers",
        json={}
    )
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"
    assert len(body["details"]) > 0
```

---

### 步骤 9：新增列表参数校验测试

**必要性：**  
博主列表接口是目前逻辑最密的一段代码：它有排序字段白名单、状态白名单和分页上限。  
这三样东西一旦被人「图省事」去掉，就会出现两种后果：排序字段被直接拼进 SQL（SQL 注入风险），或者一次查询返回几万条数据把服务拖垮。  
这类回归靠手工验收很难每次都想到，正是自动化测试最该守住的地方。

添加：

```python
def test_list_bloggers_rejects_unknown_sort_field(client):
    response = client.get("/api/v1/bloggers?sort_by=password")
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"


def test_list_bloggers_rejects_invalid_paging(client):
    for query in ["page=0", "page_size=0", "page_size=101"]:
        response = client.get(f"/api/v1/bloggers?{query}")
        body = response.get_json()

        assert response.status_code == 400
        assert body["code"] == "VALIDATION_ERROR"


def test_list_bloggers_status_filter(client):
    response = client.get("/api/v1/bloggers?status=observing")

    assert response.status_code == 200

    response = client.get("/api/v1/bloggers?status=unknown_status")
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"
```

说明：`page_size` 的合法范围是 1–100，`sort_by` 和 `status` 的合法取值见接口文档。  
如果这三个测试里有任何一个拿到了 `200`，说明白名单或上限被去掉了，必须先反馈再继续。

---

### 步骤 10：运行测试

**必要性：**  
必须实际运行，确认所有测试都通过。

执行：

```bash
pytest -q
```

预期全部通过，测试总数不少于 15 个（014 和 015 留下 3 个，本任务新增 12 个）。

具体数字可能因为后续调整而变化，重点是：**没有 failed，也没有 error**。

## 验证方式

执行：

```bash
pytest -q
```

如果看到所有测试通过，说明博主模块接口测试完成。

## 常见坑

### 1. 测试之间互相依赖

pytest 不保证按你心里想的顺序执行。  
每个测试都应该能独立运行，不能依赖前一个测试留下的数据。

### 2. 断言太多动态字段

`created_at`、`updated_at`、`observe_days` 可能随时间变化。  
不要断言它们的固定值，只断言字段存在或类型正确。

### 3. 断言写得太宽松

比如只断言 `response.status_code == 200`，不检查 `code` 和 `data`。  
这样无法发现响应结构变化。

### 4. 忘记使用 `client` fixture

如果直接写 `requests.get(...)`，就需要先启动服务。  
接口测试应该使用 Flask Test Client。

### 5. 测试数据没有清理

如果 `clean_db` fixture 没生效，重复名称测试可能会因为旧数据误报。  
检查 `tests/conftest.py` 中是否有 `autouse=True`。

### 6. 把工厂函数复制到测试文件里

`create_blogger()` 只应该存在于 `tests/factories.py` 一处。  
不要为了方便把它复制进 `test_bloggers.py`，下一个任务 017 还要用同一个函数。

检查命令：

```bash
grep -rn "def create_blogger" tests/
```

预期只有一行输出，来自 `tests/factories.py`。

## 完成标准

以下条件全部满足，任务 016 才算完成：

1. `backend/tests/factories.py` 存在，包含 `create_blogger()` 和 `create_fund()`。
2. `backend/tests/test_bloggers.py` 存在，并且从 `factories` 导入工厂函数。
3. 至少覆盖新增、列表、详情、编辑、删除。
4. 至少覆盖重复名称和非法 ID。
5. 至少覆盖排序字段白名单、分页边界、状态白名单。
6. `pytest -q` 全部通过，没有 failed 也没有 error。
7. 测试不依赖手工启动 Flask 服务。
8. `grep -rn "def create_blogger" tests/` 只有一处定义。

## 完成后请反馈

1. 新增的文件列表。
2. 测试函数数量。
3. `pytest -q` 的完整输出。
4. 断言是否都对照 `docs/api/v1-basic-management.md` 核对过。
5. 有没有发现代码和接口文档不一致的地方。
6. 哪些场景没有覆盖。
7. 遇到的问题和未完成项。
