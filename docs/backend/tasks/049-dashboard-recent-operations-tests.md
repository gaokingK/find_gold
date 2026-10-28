# 任务 049：近期操作统计接口测试

## ⚠️ 先读这一条：测试只连 `fund_test_db`

**测试全程只允许连接测试库 `fund_test_db`。**

`tests/conftest.py` 里的 `clean_db` 夹具会在**每个测试函数开始前**执行 `TRUNCATE`，把相关表全部清空。如果测试连到了开发库 `fund_db`，开发库里的数据会被清空，且无法恢复。

- 不要为了「看真实统计效果」把 `DB_NAME` 改成 `fund_db`。
- 不要注释掉 `conftest.py` 里的 `assert_test_database()`。
- `tests/` 目录下不允许出现字符串 `fund_db`（`fund_test_db` 除外）。执行 `grep -rn "fund_db" tests/` 预期**没有任何输出**；如果有，说明夹具被改错了，立即停止并反馈。

**造数据统一用 `from factories import ...` 导入**，不要把工厂函数当 pytest fixture 传参：

```python
# 正确
from factories import create_blogger


def test_xxx(client):
    blogger = create_blogger(client, name="操作统计博主")


# 错误：不要把工厂函数当 fixture 传参
def test_yyy(client, create_blogger):
    blogger = create_blogger(client)
```

**发现实现与文档不一致时只反馈，不改业务代码。**

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：

1. 本任务共 **9 个测试函数**。其中 6 个是「发请求 + 断言 3–6 行」，每个约 7 分钟，合计约 42 分钟。
2. 剩下 3 个是先造数据再断言的用例（日期区间筛选、`summary` 全量统计、`limit` 截断），要算清楚相对日期和统计口径，每个约 18 分钟，合计约 54 分钟。
3. 检查夹具、确认工厂函数、运行测试与排查失败，约 24 分钟。

合计约 120 分钟，约 2 小时。

如果超时，**优先保证日期默认行为（步骤 4）和 `summary` 全量统计（步骤 7）**，参数非法的补充用例可以放到最后。

## 任务目标

创建 `backend/tests/test_dashboard_recent_operations.py`，完成后可以：

1. 自动验证 `039` 四个日期组合的默认行为：只传 `start_date`、只传 `end_date`、两个都不传、`start_date` 晚于今天返回 400。
2. 自动验证 `limit` 的合法边界（1 / 100）和非法值（`0` / `101` / `abc`）分别返回 200 和 400。
3. 自动验证 `items` 为空时返回 `[]` 而不是 `null`。
4. 自动验证 `summary` 统计的是日期范围内**全量**操作，不受 `limit` 影响，因此 `items` 条数可以小于 `summary.operation_count`。
5. 自动验证按日期区间筛选的结果正确，且**包含两端边界日期**。
6. 以后改动 `039` 的代码时，可以用测试快速发现回归。

## 为什么必须有这个任务

`039` 是三个看板接口里唯一带日期范围和分页参数的，也是唯一区分「汇总」和「列表」两种输出的接口。它当时一个测试都没有，完成标准里只有一句「`pytest -q` 全部通过」——这句话只证明没改坏旧代码，证明不了新写的代码是对的：只要接口返回 200，旧测试就是绿的，哪怕默认日期窗口算错、`items` 返回了 `null`，测试也不会发现。

这个接口的默认路径尤其要紧：**前端默认进入看板时走的正是「两个都不传」这一支**。这条路径出错的话，用户一打开页面就看到错的统计区间。而 `summary` 与 `items` 的关系更隐蔽——只有数据条数超过 `limit` 时才暴露，手工 curl 时数据少，几乎碰不到。

## 断言的依据

所有断言必须对照 `docs/api/v1-dashboards.md` 第 5 节（对应 `docs/backend/review/api-contract-gaps.md` 5.6 节追加内容）写，**不要**照着 `app/routes/dashboards.py` 的代码写。理由：接口文档是前后端唯一契约，照代码写只是把当前实现固定下来；万一实现和文档不一致，测试还会帮着把错误行为锁死。

第 5 节的**业务规则 10–16** 是本任务最重要的依据，逐条采用：

| 规则 | 内容 |
| --- | --- |
| 10 | 只传 `start_date` 不传 `end_date` 时，`end_date` 默认今天；`start_date` 晚于今天返回 400 / `VALIDATION_ERROR` |
| 11 | 只传 `end_date` 不传 `start_date` 时，`start_date = end_date - 6` |
| 12 | 两个都不传时，`end_date = 今天`，`start_date = 今天 - 6`，共 7 天（含今天） |
| 13 | `limit` 超出 1–100 时返回 400 / `VALIDATION_ERROR` |
| 14 | `items` 为空时返回 `[]`，不返回 `null` |
| 15 | `summary` 统计日期范围内的**全量**操作，不受 `limit` 影响，因此 `items` 条数可以小于 `summary.operation_count` |
| 16 | `start_date` 也不得晚于今天 |

发现代码和文档不一致时，**先停下来反馈**，不要自己改文档，也不要改断言去迁就代码。

## 范围说明

本任务只测 `GET /api/v1/dashboards/recent-operations`（`039`），重点是**日期参数的默认行为**和**空数据**。

不包含：`GET /api/v1/dashboards/bloggers`（`037`）和 `GET /api/v1/dashboards/funds`（`038`）的测试——那是任务 `048` 的范围；收益模块测试（任务 `046`）；持仓快照模块测试（任务 `032`）；修改任何业务代码（发现问题只反馈，不改）；性能测试、前端测试。

## 前置条件

1. 任务 `037`、`038`、`039` 已完成，三个看板接口可访问。
2. 任务 `043` 已完成，`tests/factories.py` 已统一整理，`create_blogger` / `create_fund` / `create_initial_position` / `create_operation` 都可用。
3. 任务 `015` 已完成，`tests/conftest.py` 里的 `client` 和 `clean_db` 夹具可用，测试库隔离已生效。
4. `pytest -q` 当前全部通过。

## 新概念

### 概念 1：Rolling Window（滚动窗口）与默认日期窗口

Rolling Window 中文叫**滚动窗口**，指「最近 N 天」这种**相对当前日期**的统计区间——窗口的两端会随着今天往前滚。

`039` 不传日期时统计「最近 7 天（含今天）」，也就是 `end_date = 今天`、`start_date = 今天 - 6`。Python 里用 `timedelta(days=6)` 表示 6 天的时间差，`date.today() - timedelta(days=6)` 就得到开始日期。

**测试滚动窗口时不要写死日期**：写死的话，今天一旦超过那个日期，测试就会因为「开始日期晚于今天」（规则 16）而意外失败，而且失败原因看起来和窗口计算毫无关系。用 `date.today() - timedelta(days=30)` 这种相对算法，测试在任何一天都能跑。

### 概念 2：summary（汇总）与 items（列表）的分工

`039` 的响应里同时有 `summary` 和 `items`，两者统计范围不同：

- `summary` 统计的是**整个日期范围**内的**全量**操作。
- `items` 只返回按 `operation_date` 倒序、`id` 倒序排列后**被 `limit` 截断**的前 N 条。

所以 `len(items) < summary["operation_count"]` 是**正常且必须被支持**的情况——数据条数超过 `limit` 时必然如此。如果实现图省事用 `items` 反推 `summary`，前端就会出现「显示 2 条记录、却说总共 2 笔操作」的错误。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 被测对象速查

| 接口 | 路径 | 参数 |
| --- | --- | --- |
| 039 近期操作统计 | `GET /api/v1/dashboards/recent-operations` | `start_date`、`end_date`、`limit`（均可选） |

响应字段：

- `data`：`start_date`、`end_date`、`limit`、`summary`、`items[]`
- `summary`：`operation_count`、`buy_count`、`buy_shares`、`buy_amount`、`sell_count`、`sell_shares`、`sell_amount`、`dividend_cash_count`、`dividend_cash_amount`
- `items[]`：`operation_id`、`blogger_id`、`blogger_name`、`fund_id`、`fund_name`、`fund_code`、`operation_type`、`operation_date`、`shares`、`amount`
- 排序：按 `operation_date` 倒序、`id` 倒序（最新的一笔在最前面）
- `limit` 不传时默认是 `20`

错误响应：只有 `400 VALIDATION_ERROR`，没有 `404`。

## 具体步骤

### 步骤 1：确认 `clean_db` 覆盖了本模块需要的表

**必要性：**
`039` 的测试要造博主、基金、操作记录。如果 `operations` 没被加进 `clean_db`，上一个测试造的操作会串到下一个测试里，「空数据返回 `[]`」和「`summary` 条数」这两类断言就会随机失败，而且失败与否取决于测试执行顺序，很难查。

```bash
grep -n "TRUNCATE" tests/conftest.py
```

预期能看到至少 5 条 `TRUNCATE`：`operations`、`nav_history`、`initial_positions`、`funds`、`bloggers`。如果缺少 `operations`，按 `conftest.py` 里已有 `TRUNCATE` 的写法补上，顺序保持「先子表后父表」。**这一步不做任何业务代码修改，只动 `tests/conftest.py`。**

---

### 步骤 2：确认工厂函数齐全且没有重复定义

**必要性：**
本任务 9 个用例里有 3 个要先建博主、建基金、建操作。这些造数据的代码集中在 `tests/factories.py` 里，才能保证各用例造出来的数据结构一致，字段以后改了也只需要改一处。

```bash
grep -n "^def " tests/factories.py
grep -rn "def create_" tests/
```

第一条预期至少能看到 `create_blogger()`、`create_fund()`、`create_initial_position()`、`create_operation()`。第二条预期每个工厂函数**只有一处定义**，都在 `tests/factories.py`。任务 `043` 已经统一整理过，正常情况下不需要新增任何工厂函数。

---

### 步骤 3：新建测试文件并写公共辅助

**必要性：**
日期类断言最容易出的错是「写死日期导致过一段时间测试自己变红」，相对日期的计算方式必须先统一；`summary` 的浮点字段（`buy_shares`、`buy_amount` 等）不能直接用 `==` 比较，也要统一用一个辅助函数。把这两点放在文件开头锁死，后面 9 个用例就不会各写各的。

新建 `backend/tests/test_dashboard_recent_operations.py`，开头写入：

```python
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from factories import (
    create_blogger,
    create_fund,
    create_operation,
)


BASE_URL = "/api/v1/dashboards/recent-operations"


def days_ago(days):
    """返回「今天往前推 days 天」的日期字符串，例如 days_ago(6)。"""
    return (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")


def days_later(days):
    """返回「今天往后推 days 天」的日期字符串，只用来构造非法参数。"""
    return (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")


def assert_number(actual, expected, places):
    exp = Decimal("1").scaleb(-places)
    assert actual is not None
    assert Decimal(str(actual)).quantize(exp, rounding=ROUND_HALF_UP) == \
        Decimal(str(expected)).quantize(exp, rounding=ROUND_HALF_UP)


def build_operation(client, blogger, fund, operation_type, operation_date,
                    shares=0, amount=0):
    return create_operation(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        operation_type=operation_type,
        operation_date=operation_date,
        shares=shares,
        amount=amount
    )
```

要点：

- `from factories import ...` 这样写是因为 `tests` 目录里没有 `__init__.py`，pytest 会把 `tests` 目录本身加入模块搜索路径。**不要**写成 `from tests.factories import ...`。
- `days_ago()` / `days_later()` 是本任务所有日期的来源，**不要在任何用例里写死日期**——写死的日期一旦变成未来日期，就会因为规则 16 返回 400，失败原因看起来和被测逻辑毫无关系。
- `build_operation()` 不创建博主和基金，只往已存在的博主 + 基金上挂一条操作。造基金时 `fund_code` 必须各不相同，否则撞唯一索引返回 409。

---

### 步骤 4：写日期默认行为的四个用例

**必要性：**
四个分支（只传开始、只传结束、都不传、开始晚于今天报错）的取值规则各不相同，靠手工验证很难每次都试全。而「两个都不传」正是前端默认进入看板时走的那支——这条路径出错，用户一打开页面就看到错的统计区间。必须四个分支各一个用例分别锁住。

继续添加：

```python
def test_end_date_defaults_to_today(client):
    start_date = days_ago(30)

    response = client.get(f"{BASE_URL}?start_date={start_date}")
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200
    assert body["code"] == 0
    assert data["start_date"] == start_date
    assert data["end_date"] == date.today().strftime("%Y-%m-%d")
    assert data["limit"] == 20


def test_rejects_start_date_later_than_today(client):
    response = client.get(f"{BASE_URL}?start_date={days_later(1)}")
    body = response.get_json()

    # start_date 晚于今天，等价于「开始日期晚于结束日期（今天）」
    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"][0]["field"] == "start_date"


def test_start_date_defaults_to_end_date_minus_six(client):
    end_date = days_ago(1)

    response = client.get(f"{BASE_URL}?end_date={end_date}")
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200
    assert data["end_date"] == end_date
    assert data["start_date"] == days_ago(7)


def test_default_range_is_last_seven_days(client):
    response = client.get(BASE_URL)
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200
    assert data["end_date"] == date.today().strftime("%Y-%m-%d")
    assert data["start_date"] == days_ago(6)
    assert data["limit"] == 20
```

说明：

- 「只传 `start_date`」用 `days_ago(30)` 作为开始日期，**不要**写死——写死的话今天超过它之后，测试就会因为规则 16 而失败。
- 「只传 `end_date`」时 `start_date` 是 `end_date - 6`，所以 `end_date` 用 `days_ago(1)`、`start_date` 就是 `days_ago(7)`。
- 「两个都不传」时窗口是 `今天 - 6` 到 `今天`，**含今天共 7 天**。

---

### 步骤 5：写 `limit` 边界的两个用例

**必要性：**
`limit` 的合法范围是 1–100，超出要返回 400。两个方向都要测：只测非法值的话，实现如果把边界值 `1` 也判成非法，测试照样全绿；只测边界值的话，实现不校验非法值也发现不了。

继续添加：

```python
def test_rejects_invalid_limit(client):
    for limit in ["0", "101", "abc"]:
        response = client.get(f"{BASE_URL}?limit={limit}")
        body = response.get_json()

        assert response.status_code == 400
        assert body["code"] == "VALIDATION_ERROR"
        assert body["details"][0]["field"] == "limit"


def test_accepts_limit_boundaries(client):
    for limit in ["1", "100"]:
        response = client.get(f"{BASE_URL}?limit={limit}")
        body = response.get_json()

        assert response.status_code == 200
        assert body["data"]["limit"] == int(limit)
```

---

### 步骤 6：写空数据返回 `[]` 的用例

**必要性：**
规则 14 单独列出来说明它曾经（或很容易）被写错。前端拿到 `items` 会直接 `.map()`，返回 `null` 会让首屏直接白屏报错。这个用例有双重意义：一是守 `[]`，二是顺带确认 `summary` 里所有字段都在、按类型补 `0`。

继续添加：

```python
def test_items_empty_returns_empty_list(client):
    response = client.get(
        f"{BASE_URL}?start_date=2020-01-01&end_date=2020-01-07"
    )
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200
    assert body["code"] == 0

    # 规则 14：items 为空时返回 []，不是 null
    assert data["items"] == []
    assert data["items"] is not None

    # summary 的所有字段都在，按类型补 0
    summary = data["summary"]
    assert summary["operation_count"] == 0
    assert summary["buy_count"] == 0
    assert summary["sell_count"] == 0
    assert summary["dividend_cash_count"] == 0

    assert_number(summary["buy_shares"], 0, 4)
    assert_number(summary["sell_shares"], 0, 4)
    assert_number(summary["buy_amount"], 0, 2)
    assert_number(summary["sell_amount"], 0, 2)
    assert_number(summary["dividend_cash_amount"], 0, 2)
```

这个用例**不创建任何数据**：`clean_db` 已经把表清空了，查一段很久以前的日期区间就是空数据场景。

---

### 步骤 7：写 `summary` 全量统计和日期区间筛选的两个用例

**必要性：**
这两条是本任务最核心、也最容易写错的两条口径。`summary` 统计全量、`items` 受 `limit` 截断——只有数据条数超过 `limit` 时才暴露，手工 curl 数据少几乎碰不到。日期区间筛选则要确认**包含两端边界**，差一天就会漏掉一条记录。

继续添加：

```python
def test_summary_counts_full_range_not_limited_by_limit(client):
    blogger = create_blogger(client, name="分页统计博主")
    fund = create_fund(client, name="分页统计基金", fund_code="RECENT000001")

    # 4 笔买入，都落在查询范围内
    for offset in [5, 4, 3, 2]:
        build_operation(client, blogger, fund, "buy", days_ago(offset),
                        shares=100, amount=1000)

    url = f"{BASE_URL}?start_date={days_ago(6)}&end_date={days_ago(0)}&limit=2"
    response = client.get(url)
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200

    # items 被 limit 截断成 2 条
    assert len(data["items"]) == 2
    assert data["limit"] == 2

    # 规则 15：summary 统计整个日期范围的 4 笔，不受 limit 影响
    assert data["summary"]["operation_count"] == 4
    assert data["summary"]["buy_count"] == 4
    assert_number(data["summary"]["buy_shares"], 400, 4)
    assert_number(data["summary"]["buy_amount"], 4000, 2)

    # 最新的一笔排在最前面（operation_date 倒序、id 倒序）
    assert data["items"][0]["operation_date"] == days_ago(2)
```

手算：4 笔买入各 100 份 / 1000 元，全量合计 `buy_shares = 400`、`buy_amount = 4000`、`operation_count = 4`；`limit=2` 只截断 `items`，不动 `summary`。

```python
def test_date_range_filter_includes_boundaries(client):
    blogger = create_blogger(client, name="区间筛选博主")
    fund = create_fund(client, name="区间筛选基金", fund_code="RECENT000002")

    # 边界外：比 start_date 早一天
    build_operation(client, blogger, fund, "buy", days_ago(6),
                    shares=100, amount=1000)
    # 边界内：正好是 start_date 和 end_date 两天
    build_operation(client, blogger, fund, "buy", days_ago(5),
                    shares=200, amount=2000)
    build_operation(client, blogger, fund, "sell", days_ago(1),
                    shares=300, amount=3000)
    # 边界外：晚于 end_date（今天）
    build_operation(client, blogger, fund, "sell", days_ago(0),
                    shares=400, amount=4000)

    url = f"{BASE_URL}?start_date={days_ago(5)}&end_date={days_ago(1)}"
    response = client.get(url)
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200

    # 只统计 [days_ago(5), days_ago(1)] 闭区间内的两笔
    assert data["summary"]["operation_count"] == 2
    assert data["summary"]["buy_count"] == 1
    assert data["summary"]["sell_count"] == 1
    assert_number(data["summary"]["buy_shares"], 200, 4)
    assert_number(data["summary"]["buy_amount"], 2000, 2)
    assert_number(data["summary"]["sell_shares"], 300, 4)
    assert_number(data["summary"]["sell_amount"], 3000, 2)

    # items 两条，最新的一笔（days_ago(1)）在最前面
    assert len(data["items"]) == 2
    assert data["items"][0]["operation_date"] == days_ago(1)
    assert data["items"][0]["operation_type"] == "sell"
    assert data["items"][-1]["operation_date"] == days_ago(5)
    assert data["items"][-1]["operation_type"] == "buy"
```

手算：查询闭区间 `[今天-5, 今天-1]`。`今天-6` 那笔在区间外，`今天`（也就是 `days_ago(0)`）那笔也在区间外，只有 `今天-5` 和 `今天-1` 两笔参与统计。

---

### 步骤 8：运行测试并自查

**必要性：**
写完必须实际运行。日期窗口和 `summary` 统计口径都是相对今天算的，只有跑一遍才能确认手算和实现一致；尤其是边界那两笔，差一天就会红。

```bash
pytest tests/test_dashboard_recent_operations.py -q
```

预期 9 个测试全部通过。然后执行全量测试，确认没有影响其他模块：

```bash
pytest -q
```

预期全部通过，没有 failed 也没有 error。**再次确认：运行 `pytest` 时连接的是 `fund_test_db`。**

---

## 验证方式

1. **专项测试**：`pytest tests/test_dashboard_recent_operations.py -q` 预期 9 个测试全部通过。
2. **全量测试**：`pytest -q` 预期全部通过，没有 failed 也没有 error。
3. **确认连的是测试库**：`grep -n "fund_test_db" tests/conftest.py` 预期能看到 `os.environ["DB_NAME"] = "fund_test_db"`；`grep -rn "fund_db" tests/` 预期**没有任何输出**。
4. **确认没有写死日期**：`grep -n "2026-\|2025-\|2024-" tests/test_dashboard_recent_operations.py` 预期**没有任何输出**（步骤 6 里查 2020 年那段除外，那是故意选的空区间）。
5. **确认工厂函数没有重复定义**：`grep -rn "def create_" tests/` 预期每个工厂函数只有一处定义，都在 `tests/factories.py`。

## 常见坑

### 1. 连错了数据库，把开发数据清空了
后果最严重的一个错误。`clean_db` 在每个测试前 `TRUNCATE` 表，连到 `fund_db` 就是清空开发库。排查用 `grep -n "DB_NAME" tests/conftest.py`、`grep -n "assert_test_database" tests/conftest.py`；如果 `assert_test_database()` 被注释掉了，恢复它。

### 2. 日期用例写死了日期
「只传 `start_date`」这条如果写死成某个日期，今天超过它之后测试就会因为规则 16（开始日期不得晚于今天）返回 400 而失败，失败原因看起来和窗口计算毫无关系。所有日期一律用 `days_ago(n)` / `days_later(n)` 计算。

### 3. 用 `not data["items"]` 判断空
`[]` 在 Python 里是假值，`None` 也是假值。写 `assert not data["items"]` 的话，实现返回 `[]` 和返回 `null` 都能通过，规则 14 就白测了。必须写 `assert data["items"] == []` 并且补一句 `assert data["items"] is not None`。

### 4. 以为 `summary` 会被 `limit` 截断
不会。规则 15 明确：`summary` 统计全量，`items` 才受 `limit` 截断。测试要**故意**造出「数据条数 > `limit`」的形状（步骤 7 第一个用例造 4 笔、`limit=2`），否则这条规则根本测不到。

### 5. 造操作时用了未来日期
`operation_date` 晚于今天会被接口校验拦下（返回 400 或工厂函数里的 `assert` 直接报错）。本任务所有操作日期都用 `days_ago(n)`，且 `n >= 0`。

### 6. 用 `==` 直接比较浮点数
`summary` 里的 `buy_shares`、`buy_amount`、`sell_amount` 等是浮点数/Decimal 序列化结果。统一用 `assert_number(actual, expected, 4)` 或 `places=2`，它先 `Decimal(str(...)).quantize(..., ROUND_HALF_UP)`（四舍五入到指定位数）再比较，和 046/047 的口径一致——不要用 `round(float, n)`，那是银行家舍入（044 的新概念一节讲过为什么不行）。

### 7. 造基金时 fund_code 重复
同一批测试数据里每只基金的 `fund_code` 必须唯一，否则撞唯一索引返回 409，工厂函数里的 `assert` 会直接报错。

### 8. 把工厂函数当 pytest fixture 传参
见文档开头「先读这一条」里的正反例。本任务新写的测试不要照抄 `tests/factories.py` 里可能存在的历史写法（那些由任务 `043` 统一处理）。

## 完成标准

以下条件全部满足，任务 049 才算完成：

- [ ] `backend/tests/test_dashboard_recent_operations.py` 已创建，9 个测试函数都在。
- [ ] 只传 `start_date` 时 `end_date` 默认今天（规则 10）有测试。
- [ ] `start_date` 晚于今天返回 400 / `VALIDATION_ERROR`（规则 10、16）有测试。
- [ ] 只传 `end_date` 时 `start_date = end_date - 6`（规则 11）有测试。
- [ ] 两个都不传时是最近 7 天含今天（规则 12）有测试。
- [ ] `limit` 非法值（`0` / `101` / `abc`）返回 400，边界值（`1` / `100`）返回 200（规则 13）有测试。
- [ ] `items` 为空时返回 `[]` 而不是 `null`（规则 14）有测试，且顺带断言了 `summary` 全字段补 0。
- [ ] `summary` 统计全量、`items` 受 `limit` 截断，两者条数不相等（规则 15）有测试。
- [ ] 按日期区间筛选**含边界日期**有测试。
- [ ] `pytest tests/test_dashboard_recent_operations.py -q` 与 `pytest -q` 全部通过，没有 failed 也没有 error。
- [ ] 测试全程只连 `fund_test_db`，`grep -rn "fund_db" tests/` 没有任何输出。
- [ ] 没有修改任何业务代码；发现的不一致全部记录待反馈；没有把工厂函数当作 pytest fixture 使用。
- [ ] 步骤数与「必要性：」说明数量一致（都是 8）。

## 场景 ↔ 测试函数对照表

| 场景 | 测试函数 | 步骤 |
| --- | --- | --- |
| 只传 `start_date` → `end_date` 默认今天 | `test_end_date_defaults_to_today` | 4 |
| `start_date` 晚于今天 → 400 | `test_rejects_start_date_later_than_today` | 4 |
| 只传 `end_date` → `start_date = end_date - 6` | `test_start_date_defaults_to_end_date_minus_six` | 4 |
| 两个都不传 → 最近 7 天含今天 | `test_default_range_is_last_seven_days` | 4 |
| `limit` 非法值 → 400 | `test_rejects_invalid_limit` | 5 |
| `limit` 边界 1 / 100 → 200 | `test_accepts_limit_boundaries` | 5 |
| 空数据 → `items` 是 `[]` 不是 `null` | `test_items_empty_returns_empty_list` | 6 |
| `summary` 全量、`items` 被 `limit` 截断 | `test_summary_counts_full_range_not_limited_by_limit` | 7 |
| 日期区间筛选含边界 | `test_date_range_filter_includes_boundaries` | 7 |

## 完成后请反馈

1. 新增和修改的文件列表；`pytest tests/test_dashboard_recent_operations.py -q` 和 `pytest -q` 的完整输出；步骤数与「必要性：」说明数量是否一致。
2. 有没有发现代码和 `docs/api/v1-dashboards.md` 第 5 节或 `api-contract-gaps.md` 5.6 节不一致的地方（列出来，**不要自行修改**）。
3. 实际返回的字段名如果和本文档「被测对象速查」里的名字不一致，逐条列出差异，**不要自行修改接口文档或代码**。
4. 哪些场景没有覆盖、遇到的问题和未完成项。
