# 任务 047：收益模块接口测试

## ⚠️ 先读这一条

**测试只允许连接 `fund_test_db`。**

`tests/conftest.py` 里的 `clean_db` 夹具会在**每个测试函数开始前**执行 `TRUNCATE` 把表清空。如果测试连到了开发库 `fund_db`，开发库里的数据会被清空，且无法恢复。

- 不要为了「看看真实数据」把 `DB_NAME` 改成 `fund_db`，也不要注释掉 `conftest.py` 里的 `assert_test_database()`。
- 需要手工 curl 验证时，先确认 `python run.py` 用的是哪个库再发请求。

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：

1. 本任务共 **14 个测试函数**。其中 10 个套用同一个模板（用工厂函数造 3–6 条数据 + 发一个请求 + 写 5–8 行断言），每个约 6 分钟，合计约 66 分钟。
2. 剩下 4 个是 null 口径专项（缺净值三层、无持仓返回 0），需要先确认手算的期望值，每个约 8 分钟，合计约 32 分钟。
3. 检查夹具、补齐工厂函数、运行测试与排查失败，约 22 分钟。

合计约 120 分钟，约 2 小时。

如果超时，**优先保证「缺净值返回 null」和「无持仓返回 0」这两组**（步骤 4、5、6 里的 null 用例），参数非法的重复用例可以合并成循环，留到后续任务补充。

## 任务目标

新建 `backend/tests/test_returns_api.py`，自动验证：

1. 单博主累计收益接口（`034`）`GET /api/v1/bloggers/{blogger_id}/returns`。
2. 单基金收益接口（`035`）`GET /api/v1/bloggers/{blogger_id}/funds/{fund_id}/return`。
3. 总体收益汇总接口（`036`）`GET /api/v1/returns/summary`。
4. 缺净值时接口返回 `null` 而不是 `0`，且 HTTP 状态码是 `200`。
5. 没有任何持仓时金额返回 `0`、收益率返回 `null`。
6. 参数非法和不存在的 ID 时的错误响应。

## 为什么不测 Service 层

本任务**只测 HTTP 接口**，通过 Flask Test Client 发请求、断言状态码和响应 JSON；`033` 那几个纯计算函数的单元测试在任务 `046` 里已经做完了，本任务不重复。

分开的理由：函数级用例关心「哪个字段该是 null」，接口级用例关心「HTTP 状态码对不对、字段结构对不对、序列化有没有把 `Decimal` 转成数字」。这两件事的断言写法完全不同，混在一个文件里会互相干扰。

## 范围说明

包含：`034`、`035`、`036` 三个接口的 happy path、null 口径（缺净值返回 `null`、无持仓返回 `0`）、参数非法与不存在的 ID、响应字段结构。

不包含：`033` 的 Service 层单元测试（任务 `046` 的范围）；看板模块三个接口的测试（任务 `048`、`049` 的范围）；修改任何业务代码（发现问题只反馈，不改）；性能测试。

## 前置条件

1. 任务 `033` 已完成，`backend/app/services/return_calculation.py` 存在且可用。
2. 任务 `034`、`035`、`036` 已完成，三个收益接口可访问。
3. 任务 `043` 已完成，工厂函数统一为 `from factories import ...` 的写法。
4. 任务 `046` 已完成（先函数级后接口级，接口测试失败时能先排除计算层问题）。
5. `tests/conftest.py` 里的 `client` 和 `clean_db` 夹具可用，测试库隔离已生效。
6. `pytest -q` 当前全部通过。

## 新概念

### 1. Flask Test Client（测试客户端）

Test Client 是 Flask 提供的**不发真实网络请求就能调用接口**的工具。`conftest.py` 里的 `client` 夹具就是它：

```python
response = client.get("/api/v1/bloggers/1/returns?return_date=2026-01-31")
body = response.get_json()
```

`client.get(url)` 对应一次 HTTP GET，返回响应对象；`response.status_code` 是 HTTP 状态码（整数）；`response.get_json()` 把响应体解析成 Python 字典。

为什么用它而不是 curl：curl 要先把服务跑起来、要依赖库里现有的数据，写完一次就不能重复跑；Test Client 在 `pytest` 里跑，每个用例都有干净的库和可控的数据。

### 2. 响应里的 `null` 与 `0`

这个概念任务 `046` 已经介绍过（`null` 表示没有数据，`0` 表示算出来是 0），这里只说它在 HTTP 响应里的两层含义：

- 缺净值时接口返回 **HTTP `200`**，响应体里 `market_value` 等字段是 `null`。**不是 4xx，也不是 5xx**——数据没到齐不是请求出错。
- 「没有任何持仓」是唯一返回 `0` 的场景：金额是 `0`，`return_rate` 仍然是 `null`。

断言时必须用 `is None`，**不能**用 `not value`——`0` 在 Python 里也是假值，`not 0` 是 `True`，会把「算出来是 0」和「没有数据」混为一谈。

> `Decimal` 和 `ROUND_HALF_UP` 在任务 `033`、`044` 里已经介绍过，本任务直接用。

## 执行目录

所有命令都在下面目录执行（每次新开终端都要先激活虚拟环境）：

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 被测对象速查

| 任务 | 接口 | 可选参数 |
| --- | --- | --- |
| 034 | `GET /api/v1/bloggers/{blogger_id}/returns` | `return_date` |
| 035 | `GET /api/v1/bloggers/{blogger_id}/funds/{fund_id}/return` | `return_date` |
| 036 | `GET /api/v1/returns/summary` | `return_date` |

响应字段：

- `034` 的 `data`：`blogger_id`、`blogger_name`、`return_date`、`total_cost_amount`、`total_market_value`、`profit_amount`、`return_rate`、`items[]`
- `034` 的 `data.items[]`：`fund_id`、`fund_name`、`fund_code`、`shares`、`cost_amount`、`nav`、`nav_date`、`market_value`、`profit_amount`、`return_rate`
- `035` 的 `data`：**扁平**结构，把上面两级合并成一层，额外带 `blogger_id`、`blogger_name`、`return_date`。没有 `items` 这一层
- `036` 的 `data`：`return_date`、`total_cost_amount`、`total_market_value`、`profit_amount`、`return_rate`、`blogger_count`、`items[]`；`items[]` 里每个博主带 `funds[]`，`funds[]` 字段同 `034` 的 `items[]`

**本模块三个接口都不分页**，响应里没有 `page` / `page_size` / 总数这类字段。测试里不要去断言分页字段。

错误响应：

| 场景 | HTTP | code |
| --- | --- | --- |
| 路径参数非法（`abc`、`0`） | 400 | `VALIDATION_ERROR` |
| `return_date` 格式错误 | 400 | `VALIDATION_ERROR` |
| `return_date` 晚于今天 | 400 | `VALIDATION_ERROR` |
| 博主不存在 | 404 | `BLOGGER_NOT_FOUND` |
| 基金不存在，或该博主无该基金持仓 | 404 | `FUND_NOT_FOUND` |

null 真值表的三条要点（完整表格见 `docs/api/v1-returns.md` 第 2.4 节）：① **`0` 只出现在「根本没有任何持仓」这一格**，只要有持仓且缺净值一律 `null`；② 成本 ≤ 0 时 `market_value` 和 `profit_amount` **照实返回数值**，只有 `return_rate` 是 `null`；③ 缺净值的接口返回 **HTTP `200`**，不是 4xx / 5xx。发现代码和文档不一致时**先停下来反馈**，不要自己改文档，也不要改断言去迁就代码。

---

## 具体步骤

### 步骤 1：确认 `clean_db` 覆盖了收益模块需要的表

**必要性：**  
`015` 建夹具时只有三张表需要清空，所以 `clean_db` 里大概率只有 `bloggers`、`funds`、`initial_positions` 三条 `TRUNCATE`。本任务每个测试都要造操作记录和净值记录，`operations` 和 `nav_history` 如果没被清空，上一个测试留下的数据会串到下一个测试里，导致「缺净值」这类断言随机失败——而且很难查，因为失败与否取决于测试执行顺序。

```bash
grep -n "TRUNCATE" tests/conftest.py
```

预期能看到至少 5 条 `TRUNCATE`：`operations`、`nav_history`、`initial_positions`、`funds`、`bloggers`。如果缺少 `operations` 或 `nav_history`，按已有写法补上，顺序保持「先子表后父表」。**这一步不做任何业务代码修改，只动 `tests/conftest.py`。**

---

### 步骤 2：确认并补齐工厂函数

**必要性：**  
本任务 14 个测试每个都要先建博主、建基金、建初始持仓、建操作、录净值。这些 HTTP 请求写在每个测试里会让文件膨胀到无法维护，以后字段一改要改 14 处。造数据的代码必须集中在 `tests/factories.py` 里，测试文件只调用。

```bash
grep -n "^def " tests/factories.py
```

预期至少能看到 `create_blogger()`、`create_fund()`、`create_initial_position()`、`create_operation()`、`create_nav_history()`。如果缺 `create_nav_history()`，在 `backend/tests/factories.py` 末尾新增：

```python
def create_nav_history(client, fund_id, nav_date, nav="1.2345"):
    response = client.post(
        "/api/v1/nav-history",
        json={"fund_id": fund_id, "nav_date": nav_date, "nav": nav}
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    return body["data"]
```

说明：`POST /api/v1/nav-history` 是任务 `026` 的「录入或更新净值」接口，`nav` 必须大于 0、`nav_date` 不能晚于今天。如果 `043` 已经统一过工厂函数，这里大概率已经有了，**先 `grep` 再决定要不要新增**。兜底定义的**签名与默认值以 044 步骤 7 为准**（`nav="1.2345"`），不要用别的默认值另写一份。检查定义没有重复：`grep -rn "def create_" tests/`，预期每个工厂函数**只有一处定义**，都在 `tests/factories.py`。

本任务用到的两个工厂签名（来自 `043`）：`create_initial_position(client, blogger_id, fund_id, shares=12000, cost_amount=15600, record_date="2020-01-01")`；`create_operation(client, blogger_id, fund_id, operation_type="buy", operation_date="2020-01-02", shares=100, amount=1300, remark=None)`。

---

### 步骤 3：新建测试文件并写公共辅助

**必要性：**  
收益接口测试是收益模块专属的，单独建文件可以避免和 `test_returns_service.py`（任务 `046`）混在一起。把「断言非空数字」和「断言是 null」抽成辅助函数，是为了让 14 个测试里的断言保持同一种写法——否则有人写 `is None`、有人写 `not value`，后者会漏掉「本该 null 却返回 0」的错误。

新建文件：

```text
backend/tests/test_returns_api.py
```

开头写入：

```python
from decimal import Decimal, ROUND_HALF_UP

from factories import (
    create_blogger,
    create_fund,
    create_initial_position,
    create_nav_history,
    create_operation,
)


MONEY = Decimal("0.0001")
RATE = Decimal("0.000001")

RETURN_DATE = "2026-01-31"
MISSING_NAV_DATE = "2026-02-01"


def assert_number(actual, expected, exp=MONEY):
    assert actual is not None, "期望是数值，实际是 null（本该有数据却返回了 null）"
    assert Decimal(str(actual)).quantize(exp, rounding=ROUND_HALF_UP) == Decimal(
        str(expected)
    ).quantize(exp, rounding=ROUND_HALF_UP)


def assert_null(actual):
    assert actual is None, f"期望是 null，实际是 {actual!r}"


def build_blogger_returns_url(blogger_id, return_date=None):
    url = f"/api/v1/bloggers/{blogger_id}/returns"

    return f"{url}?return_date={return_date}" if return_date else url


def build_fund_return_url(blogger_id, fund_id, return_date=None):
    url = f"/api/v1/bloggers/{blogger_id}/funds/{fund_id}/return"

    return f"{url}?return_date={return_date}" if return_date else url


def build_summary_url(return_date=None):
    return f"/api/v1/returns/summary?return_date={return_date}" if return_date else "/api/v1/returns/summary"
```

说明：`from factories import ...` 这样写是因为 `tests` 目录里没有 `__init__.py`，pytest 会把 `tests` 目录本身加入模块搜索路径——**不要**写成 `from tests.factories import ...`，也**不要**把工厂函数当 fixture 传参。接口返回的金额已经序列化成 JSON 数字，`get_json()` 拿到的是 `float`，所以 `assert_number()` 里用 `Decimal(str(actual))` 先转字符串再转 `Decimal`（**不要**写 `Decimal(actual)`，那会把浮点误差原样带进来；也**不要**用 `float` 直接 `==` 比较）。`RETURN_DATE` 和 `MISSING_NAV_DATE` 是固定日期，不依赖「今天」。

---

### 步骤 4：测 `034` 单博主累计收益接口

**必要性：**  
先验证「数据齐全、净值存在」时接口能算出正确数字。这个测试通过后，说明造数据的工厂、持仓快照、净值查询、收益计算这条链路是通的，后面再测边界时如果失败，就能确定是边界逻辑的问题，而不是数据没造对。

继续添加：

```python
def _make_position_with_nav(client, blogger_id, fund_code, nav, nav_date=RETURN_DATE):
    """建一只基金，给它初始持仓 + 一笔买入 + 一条净值，返回 fund。"""
    fund = create_fund(client, name=f"基金{fund_code}", fund_code=fund_code)
    create_initial_position(client, blogger_id=blogger_id, fund_id=fund["fund_id"],
                            shares=10000, cost_amount=20000, record_date="2026-01-01")
    create_operation(client, blogger_id=blogger_id, fund_id=fund["fund_id"],
                     operation_type="buy", operation_date="2026-01-10",
                     shares=2000, amount=4000)
    create_nav_history(client, fund["fund_id"], nav_date, nav)

    return fund


def test_blogger_returns_happy_path(client):
    blogger = create_blogger(client, name="收益博主")
    fund = _make_position_with_nav(client, blogger["blogger_id"], "RET000001", "2.5")

    response = client.get(build_blogger_returns_url(blogger["blogger_id"], RETURN_DATE))
    body = response.get_json()
    data = body["data"]
    item = data["items"][0]

    assert response.status_code == 200
    assert body["code"] == 0
    assert data["blogger_id"] == blogger["blogger_id"]
    assert data["blogger_name"] == "收益博主"
    assert data["return_date"] == RETURN_DATE

    # 份额 10000 + 2000 = 12000，成本 20000 + 4000 = 24000
    # 市值 12000 × 2.5 = 30000，收益 30000 - 24000 = 6000，收益率 6000 / 24000 = 0.25
    assert_number(data["total_cost_amount"], "24000")
    assert_number(data["total_market_value"], "30000")
    assert_number(data["profit_amount"], "6000")
    assert_number(data["return_rate"], "0.25", RATE)

    assert len(data["items"]) == 1
    assert item["fund_id"] == fund["fund_id"]
    assert_number(item["shares"], "12000")
    assert_number(item["cost_amount"], "24000")
    assert_number(item["nav"], "2.5")
    assert item["nav_date"] == RETURN_DATE
    assert_number(item["market_value"], "30000")
    assert_number(item["profit_amount"], "6000")
    assert_number(item["return_rate"], "0.25", RATE)


def test_blogger_returns_missing_nav_returns_null(client):
    blogger = create_blogger(client, name="缺净值博主")
    # 净值录在 RETURN_DATE，但查询 MISSING_NAV_DATE：当天没有净值
    _make_position_with_nav(client, blogger["blogger_id"], "RET000002", "2.5")

    url = build_blogger_returns_url(blogger["blogger_id"], MISSING_NAV_DATE)
    response = client.get(url)
    body = response.get_json()
    data = body["data"]
    item = data["items"][0]

    # 缺净值是正常返回，HTTP 200，不是 4xx / 5xx
    assert response.status_code == 200
    assert body["code"] == 0

    # 份额和成本不依赖净值，照实返回
    assert_number(item["shares"], "12000")
    assert_number(item["cost_amount"], "24000")

    # 净值相关字段全部是 null，不是 0
    assert_null(item["nav"])
    assert_null(item["nav_date"])
    assert_null(item["market_value"])
    assert item["market_value"] != 0
    assert_null(item["profit_amount"])
    assert_null(item["return_rate"])

    # 博主级汇总跟着变 null，但总成本照实返回
    assert_number(data["total_cost_amount"], "24000")
    assert_null(data["total_market_value"])
    assert_null(data["profit_amount"])
    assert_null(data["return_rate"])


def test_blogger_returns_without_any_position_returns_zero(client):
    blogger = create_blogger(client, name="空仓博主")

    response = client.get(build_blogger_returns_url(blogger["blogger_id"], RETURN_DATE))
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200
    assert data["items"] == []

    # 「没有任何持仓」是唯一返回 0 的场景
    assert_number(data["total_cost_amount"], "0")
    assert_number(data["total_market_value"], "0")
    assert_number(data["profit_amount"], "0")

    # 收益率仍然是 null
    assert_null(data["return_rate"])


def test_blogger_returns_rejects_invalid_params(client):
    blogger = create_blogger(client, name="参数错误博主")
    blogger_id = blogger["blogger_id"]

    # 路径参数非法
    for bad_id in ["abc", "0"]:
        response = client.get(f"/api/v1/bloggers/{bad_id}/returns")
        body = response.get_json()
        assert response.status_code == 400, f"路径参数 {bad_id} 状态码不对"
        assert body["code"] == "VALIDATION_ERROR", f"路径参数 {bad_id} 错误码不对"

    # return_date 非法（query string 必须拼在 /returns 之后）
    for return_date in ["bad-date", "2999-12-31"]:
        response = client.get(f"/api/v1/bloggers/{blogger_id}/returns?return_date={return_date}")
        body = response.get_json()
        assert response.status_code == 400, f"return_date={return_date} 状态码不对"
        assert body["code"] == "VALIDATION_ERROR", f"return_date={return_date} 错误码不对"


def test_blogger_returns_returns_404_when_blogger_missing(client):
    response = client.get(build_blogger_returns_url(999999, RETURN_DATE))
    body = response.get_json()

    assert response.status_code == 404
    assert body["code"] == "BLOGGER_NOT_FOUND"
```

说明：「缺净值」的构造方式是**净值录在 `RETURN_DATE`、查询 `MISSING_NAV_DATE`**，这样同时验证了不会用最近一天净值兜底（两边写成同一天的话，测的就不是缺净值的分支了）。`assert item["market_value"] != 0` 这一行是专门拦「把没数据当 0 返回」的，不要删。循环里 `assert ..., f"路径参数 {bad_id} 状态码不对"` 叫断言消息，能直接告诉你是哪个参数没被拦住。**注意 query string 只能拼在 `/returns` 后面**——如果写进路径变量（例如 `f"{blogger_id}?return_date=bad-date"` 再接 `/returns`），`/returns` 会落进查询串，请求实际打到博主详情接口返回 200，断言 400 必然失败，而且会误导排错方向。

---

### 步骤 5：测 `035` 单基金收益接口

**必要性：**  
`035` 的响应是**扁平**结构，和 `034` 的「汇总 + items」不同，序列化路径是另一段代码，必须单独测。特别是「基金存在但该博主没有持仓」这个分支容易漏——实现里如果只查了 `funds` 表就返回数据，会返回一份份额和成本都是 0 的假数据，前端会显示一条不存在的持仓。

继续添加：

```python
def test_fund_return_happy_path(client):
    blogger = create_blogger(client, name="单基金博主")
    fund = _make_position_with_nav(client, blogger["blogger_id"], "RET000003", "2.5")

    url = build_fund_return_url(blogger["blogger_id"], fund["fund_id"], RETURN_DATE)
    response = client.get(url)
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200
    assert body["code"] == 0
    assert data["blogger_id"] == blogger["blogger_id"]
    assert data["blogger_name"] == "单基金博主"
    assert data["fund_id"] == fund["fund_id"]
    assert data["return_date"] == RETURN_DATE

    assert_number(data["shares"], "12000")
    assert_number(data["cost_amount"], "24000")
    assert_number(data["nav"], "2.5")
    assert data["nav_date"] == RETURN_DATE
    assert_number(data["market_value"], "30000")
    assert_number(data["profit_amount"], "6000")
    assert_number(data["return_rate"], "0.25", RATE)


def test_fund_return_missing_nav_returns_null(client):
    blogger = create_blogger(client, name="单基金缺净值博主")
    fund = _make_position_with_nav(client, blogger["blogger_id"], "RET000004", "2.5")

    url = build_fund_return_url(blogger["blogger_id"], fund["fund_id"], MISSING_NAV_DATE)
    response = client.get(url)
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200

    assert_number(data["shares"], "12000")
    assert_number(data["cost_amount"], "24000")
    assert_null(data["nav"])
    assert_null(data["nav_date"])
    assert_null(data["market_value"])
    assert_null(data["profit_amount"])
    assert_null(data["return_rate"])


def test_fund_return_rejects_invalid_fund_id(client):
    blogger = create_blogger(client, name="基金ID错误博主")

    for fund_id in ["abc", "0"]:
        response = client.get(build_fund_return_url(blogger["blogger_id"], fund_id))
        body = response.get_json()

        assert response.status_code == 400
        assert body["code"] == "VALIDATION_ERROR"
        assert body["details"][0]["field"] == "fund_id"


def test_fund_return_returns_404_when_fund_missing(client):
    blogger = create_blogger(client, name="未持有该基金博主")
    _make_position_with_nav(client, blogger["blogger_id"], "RET000005", "2.5")
    other_fund = create_fund(client, name="未持有基金", fund_code="RET000006")

    # 情况一：fund_id 指向一个根本不存在的基金
    url = build_fund_return_url(blogger["blogger_id"], 999999, RETURN_DATE)
    response = client.get(url)

    assert response.status_code == 404
    assert response.get_json()["code"] == "FUND_NOT_FOUND"

    # 情况二：基金存在，但该博主没有它的持仓
    url = build_fund_return_url(blogger["blogger_id"], other_fund["fund_id"], RETURN_DATE)
    response = client.get(url)

    assert response.status_code == 404
    assert response.get_json()["code"] == "FUND_NOT_FOUND"
```

说明：`035` 的 `data` 是**扁平**的，直接取 `data["shares"]`，没有 `items` 这一层。「基金不存在」和「博主未持有该基金」共用 `FUND_NOT_FOUND`，靠 `message` 区分，所以测试里只断言 `code`。

---

### 步骤 6：测 `036` 总体收益汇总接口

**必要性：**  
`036` 是唯一一个跨博主聚合的接口：它的 `items` 是博主列表，每个博主下面还嵌着 `funds` 数组。聚合路径多一层，就多一处可能把 `null` 和 `0` 搞混的地方。同时它的空数据场景（一个博主都没有）是看板首屏的真实状态，必须确认不报错。

继续添加：

```python
def test_total_returns_summary_happy_path(client):
    blogger = create_blogger(client, name="汇总博主")
    fund_a = _make_position_with_nav(client, blogger["blogger_id"], "RET000007", "2.5")
    fund_b = create_fund(client, name="基金RET000008", fund_code="RET000008")

    create_initial_position(client, blogger_id=blogger["blogger_id"], fund_id=fund_b["fund_id"],
                            shares=5000, cost_amount=15000, record_date="2026-01-01")
    create_nav_history(client, fund_b["fund_id"], RETURN_DATE, "3.6")

    response = client.get(build_summary_url(RETURN_DATE))
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200
    assert body["code"] == 0
    assert data["return_date"] == RETURN_DATE
    assert data["blogger_count"] == 1
    assert len(data["items"]) == 1

    blogger_item = data["items"][0]

    assert blogger_item["blogger_id"] == blogger["blogger_id"]
    assert len(blogger_item["funds"]) == 2

    # 基金 A：份额 12000，成本 24000，市值 30000
    # 基金 B：份额 5000，成本 15000，市值 18000
    # 博主合计：成本 39000，市值 48000，收益 9000，收益率 9000 / 39000 ≈ 0.230769
    assert_number(blogger_item["total_cost_amount"], "39000")
    assert_number(blogger_item["total_market_value"], "48000")
    assert_number(blogger_item["profit_amount"], "9000")
    assert_number(blogger_item["return_rate"], "0.230769", RATE)

    # 只有一个博主，全局级等于博主级
    assert_number(data["total_cost_amount"], "39000")
    assert_number(data["total_market_value"], "48000")
    assert_number(data["profit_amount"], "9000")
    assert_number(data["return_rate"], "0.230769", RATE)


def test_total_returns_summary_missing_nav_makes_total_null(client):
    blogger = create_blogger(client, name="汇总缺净值博主")
    _make_position_with_nav(client, blogger["blogger_id"], "RET000009", "2.5")

    # 净值录在 RETURN_DATE，查询 MISSING_NAV_DATE：全局唯一一只基金缺净值
    response = client.get(build_summary_url(MISSING_NAV_DATE))
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200

    # 成本不依赖净值，照实返回
    assert_number(data["total_cost_amount"], "24000")
    assert_number(data["items"][0]["total_cost_amount"], "24000")

    # 全局级：任意基金缺净值 → 总市值、总收益、总收益率都是 null
    assert_null(data["total_market_value"])
    assert data["total_market_value"] != 0
    assert_null(data["profit_amount"])
    assert_null(data["return_rate"])

    # 博主级同样为 null，但博主仍然出现在 items 里
    assert data["blogger_count"] == 1
    assert_null(data["items"][0]["total_market_value"])
    assert_null(data["items"][0]["profit_amount"])
    assert_null(data["items"][0]["return_rate"])


def test_total_returns_summary_without_data(client):
    response = client.get(build_summary_url(RETURN_DATE))
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200
    assert body["code"] == 0
    assert data["blogger_count"] == 0
    assert data["items"] == []

    assert_number(data["total_cost_amount"], "0")
    assert_number(data["total_market_value"], "0")
    assert_number(data["profit_amount"], "0")
    assert_null(data["return_rate"])


def test_total_returns_summary_rejects_invalid_return_date(client):
    for return_date in ["bad-date", "2999-12-31"]:
        response = client.get(build_summary_url(return_date))
        body = response.get_json()

        assert response.status_code == 400, f"日期 {return_date} 应该被拒绝"
        assert body["code"] == "VALIDATION_ERROR"
        assert body["details"][0]["field"] == "return_date"
```

说明：`036` 的 `items[]` 里每个博主有 `total_cost_amount` 等汇总字段，嵌套的 `funds[]` 字段同 `034` 的 `items[]`。取行时按 `blogger_id` / `fund_id` 建字典，**不要**依赖下标顺序（本任务只造一个博主，所以直接取 `items[0]`）。

---

### 步骤 7：测响应字段结构

**必要性：**  
前面 13 个测试断言的都是「数字对不对」，没有一个断言「字段全不全」。字段漏了（比如 `035` 少返回 `blogger_name`）不会让任何数字断言失败，但前端会直接报错。这个用例专门守字段结构。

继续添加：

```python
def test_returns_response_fields_match_contract(client):
    blogger = create_blogger(client, name="字段结构博主")
    fund = _make_position_with_nav(client, blogger["blogger_id"], "RET000010", "2.5")

    # 034：data 是「汇总 + items」两层
    response = client.get(build_blogger_returns_url(blogger["blogger_id"], RETURN_DATE))
    body = response.get_json()
    data = body["data"]

    assert set(body.keys()) == {"code", "message", "data"}
    assert set(data.keys()) == {
        "blogger_id", "blogger_name", "return_date", "total_cost_amount",
        "total_market_value", "profit_amount", "return_rate", "items",
    }
    assert set(data["items"][0].keys()) == {
        "fund_id", "fund_name", "fund_code", "shares", "cost_amount",
        "nav", "nav_date", "market_value", "profit_amount", "return_rate",
    }

    # 本模块接口不分页，响应里不应该出现分页字段
    assert not {"page", "page_size", "total"} & set(data.keys())

    # 035：扁平结构，没有 items 这一层，但带上了博主信息
    url = build_fund_return_url(blogger["blogger_id"], fund["fund_id"], RETURN_DATE)
    response = client.get(url)
    flat = response.get_json()["data"]

    assert "items" not in flat
    assert set(flat.keys()) == {
        "blogger_id", "blogger_name", "fund_id", "fund_name", "fund_code",
        "return_date", "shares", "cost_amount", "nav", "nav_date",
        "market_value", "profit_amount", "return_rate",
    }
```

说明：用 `set(...) == {...}` 断言字段集合，能同时抓出「多了字段」和「少了字段」两种问题。如果以后接口文档加字段，同步更新这里即可。

---

### 步骤 8：运行测试

**必要性：**  
写完必须实际运行。收益测试里有大量手算期望值，只有真正跑一遍才能确认手算和实现一致。

```bash
pytest tests/test_returns_api.py -q
pytest -q
```

预期：本文件 14 个测试全部通过；全量没有 failed 也没有 error。**再次确认：运行 `pytest` 时连接的是 `fund_test_db`。**

## 验证方式

```bash
pytest tests/test_returns_api.py -q    # 预期 14 个测试全部通过
pytest -q                              # 预期全部通过，没有 failed 也没有 error
grep -n "fund_test_db" tests/conftest.py   # 预期能看到 DB_NAME 被设成 fund_test_db
grep -rn "fund_db" tests/              # 预期没有任何输出；出现裸的 fund_db 说明夹具被改错，立即停止并反馈
grep -rn "def create_" tests/          # 预期每个工厂函数只有一处定义，都在 tests/factories.py
```

## 常见坑

### 1. 连错了数据库，把开发数据清空了

这是本项目测试里后果最严重的一个错误。`clean_db` 会在每个测试前 `TRUNCATE` 表，连到 `fund_db` 就是清空开发库。

排查：`grep -n "DB_NAME" tests/conftest.py` 和 `grep -n "assert_test_database" tests/conftest.py`。如果 `assert_test_database()` 被注释掉了，恢复它（它在任何 `TRUNCATE` 之前检查数据库名）。

### 2. 用 `not value` 判断 null

`0` 在 Python 里是假值。缺净值时如果写 `assert not item["market_value"]`，即使实现返回了 `0` 也会通过——测试就失去意义了。必须写 `assert item["market_value"] is None`（本任务的 `assert_null()` 就是干这个的）。

### 3. 用 `float` 直接 `==` 比较金额

接口返回的金额是 JSON 数字，`get_json()` 拿到的是 `float`。直接 `==` 比较有二进制表示误差。统一用 `assert_number()`，它先 `Decimal(str(actual))` 再 `quantize(..., ROUND_HALF_UP)`。

### 4. 不传 `return_date`，测试随机失败

`return_date` 不传时默认今天。周末和节假日没有净值，默认查询会返回 `null` 市值（这是预期行为）。如果测试依赖默认值，周一跑通过、周日跑失败。**除专门测试默认行为的用例外，所有测试都显式传 `return_date`。**

### 5. 把工厂函数当 pytest fixture 传参

错误写法：

```python
def test_xxx(client, create_blogger):     # 错误
    blogger = create_blogger(client)
```

`create_blogger` 是普通函数不是 fixture，pytest 会报 `fixture 'create_blogger' not found`。正确写法是 `from factories import create_blogger`，然后在函数体里调用。

### 6. 造数据时净值日期写错，以为测的是「缺净值」

「缺净值」的正确构造方式是：净值录在 A 日，查询 B 日。如果两边写成同一天，测的就不是缺净值的分支。核对方法：`grep -n "create_nav_history\|MISSING_NAV_DATE" tests/test_returns_api.py`。

### 7. 另外两条（对照检查即可）

- **依赖 `items` 的下标顺序**：`items` 的顺序由实现决定，不同接口可能不同。取行时按 `fund_id` / `blogger_id` 建字典，不要写 `items[0]`、`items[1]`（本任务只造一个博主，所以直接取 `items[0]`；以后加数据要改成按 `fund_id` 取）。
- **断言了不存在的分页字段**：本模块三个接口都不分页，照别的模块抄来 `assert data["page"] == 1` 会直接 `KeyError`。

## 完成标准

以下条件全部满足，任务 047 才算完成：

- [ ] `backend/tests/test_returns_api.py` 已创建，包含 14 个测试函数。
- [ ] `034`、`035`、`036` 三个接口各有 happy path 用例，且断言了金额和收益率。
- [ ] 缺净值的用例断言了接口返回 `null` 而不是 `0`、HTTP 状态码是 `200`（不是 4xx / 5xx），并覆盖博主级（034）、基金级（035）、全局级（036）三层。
- [ ] 「没有任何持仓」的用例断言了成本 / 市值 / 收益金额是 `0`、收益率是 `null`。
- [ ] 参数非法有覆盖：路径参数非法（`abc`、`0`）、`return_date` 格式错误、`return_date` 晚于今天。
- [ ] 不存在的 ID 有覆盖：博主不存在返回 `BLOGGER_NOT_FOUND`；基金不存在和博主无该基金持仓都返回 `FUND_NOT_FOUND`。
- [ ] 有用例断言了 `034` 的 `data` 和 `items[]` 字段集合、`035` 的扁平结构，且确认响应里没有分页字段。
- [ ] 金额比较全部走 `Decimal` + `ROUND_HALF_UP`，没有用 `float` 直接 `==`；除专门测试默认行为的用例外都显式传了 `return_date`。
- [ ] `pytest tests/test_returns_api.py -q` 和 `pytest -q` 全部通过，没有 failed 也没有 error。
- [ ] 测试全程只连 `fund_test_db`，`tests/` 目录下没有任何裸的 `fund_db`。
- [ ] 没有修改任何业务代码；发现的不一致全部记录待反馈。
- [ ] 没有把工厂函数当作 pytest fixture 使用。

---

## 完成后请反馈

1. 新增和修改的文件列表。
2. `pytest tests/test_returns_api.py -q` 的完整输出（14 个测试），以及 `pytest -q` 的完整输出。
3. 「场景 ↔ 测试函数」对照表（14 行即可，一行一个测试函数 + 它守的是哪个接口的哪条口径）。
4. 步骤数与「必要性：」说明数量是否一致（应为 8 对 8）。
5. 有没有发现代码和 `docs/api/v1-returns.md` 或 `api-contract-gaps.md` 5.5 节不一致的地方（列出来，不要自行修改）。
6. 哪些场景没有覆盖、遇到了什么问题、有哪些未完成项。
