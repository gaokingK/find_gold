# 任务 048：看板 null 三层污染测试

## ⚠️ 先读这一条：测试只连 `fund_test_db`

**测试全程只允许连接测试库 `fund_test_db`。**

`tests/conftest.py` 里的 `clean_db` 夹具会在**每个测试函数开始前**执行 `TRUNCATE`，把相关表全部清空。如果测试连到了开发库 `fund_db`，开发库里的数据会被清空，且无法恢复。

- 不要为了「看看板真实效果」把 `DB_NAME` 改成 `fund_db`。
- 不要注释掉 `conftest.py` 里的 `assert_test_database()`。
- `tests/` 目录下不允许出现字符串 `fund_db`（`fund_test_db` 除外）。执行 `grep -rn "fund_db" tests/` 预期**没有任何输出**；如果有，说明夹具被改错了，立即停止并反馈。

**造数据统一用 `from factories import ...` 导入**，不要把工厂函数当 pytest fixture 传参：

```python
# 正确
from factories import create_blogger


def test_xxx(client):
    blogger = create_blogger(client, name="看板博主甲")


# 错误：不要把工厂函数当 fixture 传参
def test_yyy(client, create_blogger):
    blogger = create_blogger(client)
```

**发现实现与文档不一致时只反馈，不改业务代码。** 下面「038 已知坑」那组用例尤其如此——如果测试变红，那是预期结果。

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：

1. 本任务共 **8 个测试函数**。其中 6 个套用同一个模板（造 2–4 条数据 + 写 5–10 行断言），每个约 9 分钟，合计约 54 分钟。
2. 剩下 3 个是 `038` 已知坑的专项用例，要构造「同一基金被两个博主共用」「缺净值博主 id 更小」这类特殊数据顺序，每个约 15 分钟，合计约 45 分钟。
3. 检查夹具、确认工厂函数、运行测试与排查失败，约 27 分钟。

合计约 120 分钟，约 2 小时。

如果超时，**优先保证 null 三层污染（步骤 4–6）和 `038` 已知坑（步骤 7）**，步骤 4 里的基准对照用例可以最后补。

## 任务目标

创建 `backend/tests/test_dashboard_nulls.py`，完成后可以：

1. 自动验证 `038` 的**基金级** null 规则：缺净值只影响缺的那一只，不牵连其他有净值的基金。
2. 自动验证 `037` 的**博主级** null 规则：名下任意一只缺净值，该博主合计为 `null`。
3. 自动验证**全局级** null 规则：任意一只基金缺净值，总市值/总收益/总收益率为 `null`，且 `/dashboards/funds` 里**所有**基金的 `market_value_ratio` 为 `null`。
4. 自动验证**成本类字段不依赖净值**：`cost_amount` / `total_cost_amount` / `cost_ratio` 任何情况下都照实返回，不为 `null`。
5. 自动验证 `038` 那个「缺净值博主 id 更小时返回 500」的已知坑不会重现。
6. 以后改动看板模块代码时，可以用测试快速发现回归。

## 为什么必须有这个任务

`037`–`039` 这三个看板接口一个测试都没有，完成标准里只有一句「`pytest -q` 全部通过」——这句话只证明没改坏旧代码，证明不了新写的代码是对的：只要接口返回 200，旧测试就是绿的，哪怕看板数字算错、缺净值时返回了 `0`，测试也不会发现。

看板是**前端首屏**要展示的数据：所有人第一眼就看到，而问题往往只在特定数据下出现，比如「某个博主名下有一只基金缺净值」这种状态，手工 curl 很容易碰不到，上线后真实数据里却随时可能出现。

## 断言的依据

所有断言必须对照 `docs/api/v1-dashboards.md` 第 1.4 节（对应 `docs/backend/review/api-contract-gaps.md` 5.6 节）写，**不要**照着 `app/routes/dashboards.py` 的代码写。理由：接口文档是前后端唯一契约，照代码写只是把当前实现固定下来；万一实现和文档不一致，测试还会帮着把错误行为锁死。

`docs/api/v1-dashboards.md` 第 1.4 节的 **null 三层污染规则**是本任务最重要的依据，逐条采用：

| 层级 | 规则 |
| --- | --- |
| **基金级** | 缺净值的基金，自己的 `nav` / `nav_date` / `market_value` / `profit_amount` / `return_rate` / `market_value_ratio` 为 `null`；有净值的基金照实返回自己的数值 |
| **博主级** | 某博主名下**任意**一只基金缺净值，该博主合计的 `total_market_value` / `profit_amount` / `return_rate` 为 `null` |
| **全局级** | **任意**一只基金缺净值，`data` 里的 `total_market_value` / `profit_amount` / `return_rate` 为 `null`，且 `/dashboards/funds` 中**所有**基金的 `market_value_ratio` 为 `null` |

另外一条独立规则：

> 成本类字段（`cost_amount`、`total_cost_amount`、`cost_ratio`）不依赖净值，**任何情况下都照实返回，不为 `null`**。

发现代码和文档不一致时，**先停下来反馈**，不要自己改文档，也不要改断言去迁就代码。

## 范围说明

本任务只测 **null 三层污染**：

- `GET /api/v1/dashboards/bloggers`（`037`）
- `GET /api/v1/dashboards/funds`（`038`）

不包含：`GET /api/v1/dashboards/recent-operations`（`039`）的测试（那是任务 `049` 的范围）；收益模块测试（任务 `046`）；持仓快照模块测试（任务 `032`）；修改任何业务代码（发现问题只反馈，不改）；性能测试、前端测试。

## 前置条件

1. 任务 `037`、`038`、`039` 已完成，三个看板接口可访问。
2. 任务 `043` 已完成，`tests/factories.py` 已统一整理，`create_blogger` / `create_fund` / `create_initial_position` / `create_nav_history` / `create_operation` 都可用。
3. 任务 `033` 的收益计算逻辑可用（看板的 null 口径依赖同一套计算）；任务 `015` 已完成，`client` 与 `clean_db` 夹具可用。
4. `pytest -q` 当前全部通过。

## 新概念

### 概念 1：null 三层污染（基金级 / 博主级 / 全局级）

英文写作 three-level null propagation，指**「缺净值」这件事会沿着数据聚合的方向往上传染**。三层的规则方向不一样，记混就写反了：**基金级**只影响缺的那一只**自己**，不牵连同层其他基金；**博主级**向上传染一层，名下**任意**一只缺，整个博主合计就为 `null`；**全局级**传染到顶，**任意**一只缺，全局合计为 `null`，且 `/dashboards/funds` 里**所有**基金的市值占比都为 `null`。

### 概念 2：Ratio（占比）与「分母不完整」

Ratio 中文叫**占比**，是某个值占合计值的比例，例如 `cost_ratio = 该基金成本 / 所有基金总成本`、`market_value_ratio = 该基金市值 / 总市值`。

占比的特点是：**分母不完整时，占比本身也不可信。** 所以只要有任意一只基金缺净值（总市值算不出来），`/dashboards/funds` 里**所有**基金的 `market_value_ratio` 都要返回 `null`——哪怕某只基金自己有净值、市值算得出来。否则前端的饼图加起来不是 100%，而且看不出哪里不对。成本占比 `cost_ratio` 不受影响，因为它的分母（总成本）不依赖净值，永远完整。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 被测对象速查

| 接口 | 路径 | 参数 |
| --- | --- | --- |
| 037 博主总览看板 | `GET /api/v1/dashboards/bloggers` | `return_date`（可选，不传默认今天） |
| 038 基金分布看板 | `GET /api/v1/dashboards/funds` | `return_date`（可选，不传默认今天） |

响应字段：

- `037` 的 `data`：`return_date`、`blogger_count`、`position_count`、`total_cost_amount`、`total_market_value`、`profit_amount`、`return_rate`、`items[]`
  - `items[]`：`blogger_id`、`blogger_name`、`fund_count`、`total_cost_amount`、`total_market_value`、`profit_amount`、`return_rate`
  - `037` 的 `items[]` 里**没有** `funds` 数组，那是 `/api/v1/returns/summary`（任务 `036`）的结构
- `038` 的 `data`：`return_date`、`fund_count`、`total_cost_amount`、`total_market_value`、`items[]`
  - `items[]`：`fund_id`、`fund_name`、`fund_code`、`blogger_count`、`shares`、`cost_amount`、`nav`、`nav_date`、`market_value`、`cost_ratio`、`market_value_ratio`，按 `cost_amount` 从高到低排序

两个接口只有 `400 VALIDATION_ERROR`，没有 `404`——博主或基金不存在时返回 `200` 和空 `items`。**取行一律按 `blogger_id` / `fund_id` 建字典，不要用 `items[0]`。**

## 具体步骤

### 步骤 1：确认 `clean_db` 覆盖了本模块需要的表

**必要性：**
看板测试要造博主、基金、初始持仓、操作记录和净值记录。`015` 建夹具时只有三张表需要清空，如果 `operations` 和 `nav_history` 没被加进 `clean_db`，上一个测试的净值会串到下一个测试里，「缺净值」类断言就会随机失败，而且失败与否取决于测试执行顺序，很难查。

执行：

```bash
grep -n "TRUNCATE" tests/conftest.py
```

预期能看到至少 5 条 `TRUNCATE`：`operations`、`nav_history`、`initial_positions`、`funds`、`bloggers`。如果缺少 `operations` 或 `nav_history`，按 `conftest.py` 里已有 `TRUNCATE` 的写法补上，顺序保持「先子表后父表」。**这一步不做任何业务代码修改，只动 `tests/conftest.py`。**

---

### 步骤 2：确认工厂函数齐全且没有重复定义

**必要性：**
本任务 8 个用例每个都要先建博主、建基金、建初始持仓。这些造数据的代码集中在 `tests/factories.py` 里，才能保证 8 个用例造出来的数据结构一致，字段以后改了也只需要改一处。缺 `create_nav_history` 的话「缺净值」场景根本构造不出来（没法对照「有净值」）。

执行：

```bash
grep -n "^def " tests/factories.py
grep -rn "def create_" tests/
```

第一条预期至少能看到 `create_blogger()`、`create_fund()`、`create_initial_position()`、`create_nav_history()`、`create_operation()`。第二条预期每个工厂函数**只有一处定义**，都在 `tests/factories.py`。

任务 `043` 已经把 `create_nav_history` 列为标准工厂函数之一，正常情况下不需要新增。如果确实没有，在 `backend/tests/factories.py` 末尾新增（`POST /api/v1/nav-history` 是任务 `026` 产出的「录入或更新净值」接口，`nav` 必须大于 0，`nav_date` 不能晚于今天）：

```python
def create_nav_history(client, fund_id, nav_date, nav="1.2345"):
    response = client.post("/api/v1/nav-history",
                           json={"fund_id": fund_id, "nav_date": nav_date, "nav": nav})
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    return body["data"]
```

兜底定义的**签名与默认值以 044 步骤 7 为准**（`nav="1.2345"`），不要用别的默认值另写一份。

---

### 步骤 3：新建测试文件并写公共辅助

**必要性：**
null 断言是本任务的验收重点，`0` 和 `null` 的区分必须靠统一的判断方式。如果不同用例有的用 `is None`、有的用 `not`，那么实现返回 `0` 时一部分用例通过、一部分失败，排查方向会被引偏。所以先抽两个辅助函数把所有用例的判断方式锁死。

新建 `backend/tests/test_dashboard_nulls.py`，开头写入：

```python
from decimal import Decimal, ROUND_HALF_UP

from factories import (
    create_blogger,
    create_fund,
    create_initial_position,
    create_nav_history,
)


RETURN_DATE = "2026-01-31"


def assert_number(actual, expected, places):
    exp = Decimal("1").scaleb(-places)
    assert actual is not None
    assert Decimal(str(actual)).quantize(exp, rounding=ROUND_HALF_UP) == \
        Decimal(str(expected)).quantize(exp, rounding=ROUND_HALF_UP)


def assert_null(actual):
    assert actual is None


def build_position(
    client,
    blogger,
    fund,
    shares=10000,
    cost_amount=20000,
    record_date="2026-01-01",
    nav=None,
    nav_date=RETURN_DATE
):
    create_initial_position(
        client,
        blogger_id=blogger["blogger_id"],
        fund_id=fund["fund_id"],
        shares=shares,
        cost_amount=cost_amount,
        record_date=record_date
    )

    if nav is not None:
        create_nav_history(
            client,
            fund_id=fund["fund_id"],
            nav_date=nav_date,
            nav=nav
        )


def items_by(data, key):
    return {item[key]: item for item in data["items"]}
```

要点：

- `from factories import ...` 这样写是因为 `tests` 目录里没有 `__init__.py`，pytest 会把 `tests` 目录本身加入模块搜索路径。**不要**写成 `from tests.factories import ...`。
- `assert_null()` 里用 `is None`，**不要**用 `not actual`。看板里 `0` 是合法值（「没有任何持仓」时总市值就是 `0`），用 `not` 会把合法的 `0` 和缺失的 `null` 混在一起，测试就白写了。
- `build_position()` **不创建博主和基金**，只把一个已存在的博主和一个已存在的基金关联成一条初始持仓，并按需录一条净值；`nav=None` 表示**不录净值**，用来构造缺净值场景。造基金时 `fund_code` 必须各不相同，否则撞唯一索引返回 409。

---

### 步骤 4：写有净值的基准对照用例和基金级 null 用例

**必要性：**
先测「净值齐全」再测「缺净值」，两组结果放在一起才有说服力——只测 `null` 的话，实现一旦把所有字段都置成 `null`，测试照样全绿。基金级规则又是三层里最基础的一层：「缺净值只影响缺的那一只，不牵连其他有净值的基金」。这条如果写反，前端会以为整个看板都没数据。

继续添加：

```python
def test_fund_dashboard_all_nav_present(client):
    blogger = create_blogger(client, name="基准博主")
    fund_a = create_fund(client, name="基准基金A", fund_code="NULL000001")
    fund_b = create_fund(client, name="基准基金B", fund_code="NULL000002")

    build_position(client, blogger, fund_a, shares=10000,
                   cost_amount=20000, nav=2.5)
    build_position(client, blogger, fund_b, shares=5000,
                   cost_amount=10000, nav=3.6)

    response = client.get(f"/api/v1/dashboards/funds?return_date={RETURN_DATE}")
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200
    assert data["fund_count"] == 2

    # 净值齐全：市值、占比、总市值全都是数值，没有一个是 null
    assert_number(data["total_cost_amount"], 30000, 2)
    assert_number(data["total_market_value"], 43000, 2)

    by_fund_id = items_by(data, "fund_id")

    assert_number(by_fund_id[fund_a["fund_id"]]["market_value"], 25000, 2)
    assert_number(by_fund_id[fund_a["fund_id"]]["market_value_ratio"], 0.581395, 6)
    assert_number(by_fund_id[fund_b["fund_id"]]["market_value"], 18000, 2)
    assert_number(by_fund_id[fund_b["fund_id"]]["market_value_ratio"], 0.418605, 6)
```

手算：基金A 市值 `10000 × 2.5 = 25000`，基金B 市值 `5000 × 3.6 = 18000`，总市值 `43000`；占比 `25000 / 43000 = 0.581395`、`18000 / 43000 = 0.418605`。

```python
def test_fund_dashboard_missing_nav_isolates_single_fund(client):
    blogger = create_blogger(client, name="基金级缺净值博主")
    fund_with_nav = create_fund(client, name="基金级有净值基金", fund_code="NULL000003")
    fund_without_nav = create_fund(client, name="基金级缺净值基金", fund_code="NULL000004")

    # 只给第一只基金录 RETURN_DATE 的净值，第二只当天没有净值
    build_position(client, blogger, fund_with_nav, shares=10000,
                   cost_amount=20000, nav=2.5)
    build_position(client, blogger, fund_without_nav, shares=5000,
                   cost_amount=10000, nav=None)

    response = client.get(f"/api/v1/dashboards/funds?return_date={RETURN_DATE}")
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200
    assert data["fund_count"] == 2

    by_fund_id = items_by(data, "fund_id")

    # 有净值的基金：净值、市值照实返回
    item_with_nav = by_fund_id[fund_with_nav["fund_id"]]
    assert_number(item_with_nav["nav"], 2.5, 4)
    assert item_with_nav["nav_date"] == RETURN_DATE
    assert_number(item_with_nav["market_value"], 25000, 2)

    # 缺净值的基金：只有它自己变 null，而且不是 0
    item_without_nav = by_fund_id[fund_without_nav["fund_id"]]
    assert_null(item_without_nav["nav"])
    assert_null(item_without_nav["nav_date"])
    assert_null(item_without_nav["market_value"])
    assert item_without_nav["market_value"] != 0
    assert_null(item_without_nav["market_value_ratio"])

    # 两只基金的成本和成本占比都照实返回（成本不依赖净值）
    assert_number(item_with_nav["cost_amount"], 20000, 2)
    assert_number(item_without_nav["cost_amount"], 10000, 2)
    assert_number(item_with_nav["cost_ratio"], 0.666667, 6)
    assert_number(item_without_nav["cost_ratio"], 0.333333, 6)
```

注意 `assert_null(...["market_value"])` 和 `assert ... != 0` 要**都写**：前者保证是 `null`，后者保证实现不是拿 `0` 充数。

---

### 步骤 5：写博主级和全局级 null 用例

**必要性：**
博主级规则（名下**任意**一只缺 → 整个博主合计为 `null`）和基金级规则（只影响自己）方向相反，两个方向记混实现就写反了，必须单独测。全局级是最容易漏的一条：**所有**基金的 `market_value_ratio` 都要为 `null`，包括那些自己有净值的基金——如果实现只对缺净值那只置 `null`、其他基金照常算占比，前端饼图加起来就不是 100%。

继续添加：

```python
def test_blogger_dashboard_missing_nav_makes_blogger_total_null(client):
    blogger_a = create_blogger(client, name="博主级缺净值甲")
    blogger_b = create_blogger(client, name="博主级净值齐全乙")
    fund_a = create_fund(client, name="博主级有净值基金", fund_code="NULL000005")
    fund_b = create_fund(client, name="博主级缺净值基金", fund_code="NULL000006")
    fund_c = create_fund(client, name="博主级全净值基金", fund_code="NULL000007")

    # 博主甲：一只缺净值、一只有净值 → 合计为 null
    build_position(client, blogger_a, fund_a, shares=10000,
                   cost_amount=20000, nav=2.5)
    build_position(client, blogger_a, fund_b, shares=5000,
                   cost_amount=10000, nav=None)

    # 博主乙：名下净值齐全 → 合计照实返回数值
    build_position(client, blogger_b, fund_c, shares=2000,
                   cost_amount=4000, nav=1.5)

    response = client.get(f"/api/v1/dashboards/bloggers?return_date={RETURN_DATE}")
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200
    assert data["blogger_count"] == 2

    by_blogger_id = items_by(data, "blogger_id")

    # 博主甲：名下有一只缺净值 → 合计为 null，但总成本照实返回
    item_a = by_blogger_id[blogger_a["blogger_id"]]
    assert item_a["fund_count"] == 2
    assert_number(item_a["total_cost_amount"], 30000, 2)
    assert_null(item_a["total_market_value"])
    assert_null(item_a["profit_amount"])
    assert_null(item_a["return_rate"])

    # 博主乙：净值齐全，合计照实返回数值
    item_b = by_blogger_id[blogger_b["blogger_id"]]
    assert item_b["fund_count"] == 1
    assert_number(item_b["total_cost_amount"], 4000, 2)
    assert_number(item_b["total_market_value"], 3000, 2)
    assert_number(item_b["profit_amount"], -1000, 2)
```

手算：博主甲基金A 市值 `10000 × 2.5 = 25000`，基金B 缺净值 → `null`，合计市值 `null`，合计成本 `20000 + 10000 = 30000`。博主乙基金C 市值 `2000 × 1.5 = 3000`，成本 `4000`，收益 `3000 − 4000 = −1000`。

```python
def test_dashboards_missing_nav_makes_global_total_null(client):
    blogger_a = create_blogger(client, name="全局级有净值甲")
    blogger_b = create_blogger(client, name="全局级缺净值乙")
    fund_with_nav = create_fund(client, name="全局有净值基金", fund_code="NULL000008")
    fund_without_nav = create_fund(client, name="全局缺净值基金", fund_code="NULL000009")

    build_position(client, blogger_a, fund_with_nav, shares=10000,
                   cost_amount=20000, nav=2.5)
    build_position(client, blogger_b, fund_without_nav, shares=5000,
                   cost_amount=10000, nav=None)

    # 037 博主总览看板：全局级三个字段都是 null，但总成本照实返回
    response = client.get(f"/api/v1/dashboards/bloggers?return_date={RETURN_DATE}")
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200
    assert_number(data["total_cost_amount"], 30000, 2)
    assert_null(data["total_market_value"])
    assert_null(data["profit_amount"])
    assert_null(data["return_rate"])

    # 038 基金分布看板
    response = client.get(f"/api/v1/dashboards/funds?return_date={RETURN_DATE}")
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200
    assert data["fund_count"] == 2

    by_fund_id = items_by(data, "fund_id")

    # 缺净值的基金：自己的四个字段是 null
    missing_item = by_fund_id[fund_without_nav["fund_id"]]
    assert_null(missing_item["nav"])
    assert_null(missing_item["nav_date"])
    assert_null(missing_item["market_value"])
    assert_null(missing_item["market_value_ratio"])

    # 有净值的基金：market_value 照实返回，但 market_value_ratio 也是 null（分母不完整）
    present_item = by_fund_id[fund_with_nav["fund_id"]]
    assert_number(present_item["nav"], 2.5, 4)
    assert_number(present_item["market_value"], 25000, 2)
    assert_null(present_item["market_value_ratio"])

    # 总市值是 null
    assert_null(data["total_market_value"])
```

---

### 步骤 6：写成本类字段不为 null 的专项用例

**必要性：**
这条是三层污染规则的**例外项**，最容易被一起改坏。有人写「缺净值就把数值字段置 null」时，很容易顺手把 `cost_amount` 也置了，但成本来自初始持仓和操作记录，**完全不依赖净值**。必须有专门用例只测成本类字段，让这个例外项单独可见——否则它混在别的用例里，出问题时看不出是哪条规则坏了。

继续添加：

```python
def test_dashboards_cost_fields_never_null(client):
    blogger = create_blogger(client, name="成本字段博主")
    fund = create_fund(client, name="缺净值但成本正常基金", fund_code="NULL000010")

    # 有持仓，但当天没有净值
    build_position(client, blogger, fund, shares=10000,
                   cost_amount=20000, nav=None)

    # 037 博主总览看板
    response = client.get(f"/api/v1/dashboards/bloggers?return_date={RETURN_DATE}")
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200

    # 博主级和全局级的成本照实返回，不是 null
    assert_number(data["items"][0]["total_cost_amount"], 20000, 2)
    assert_number(data["total_cost_amount"], 20000, 2)

    # 同一个响应里，市值相关字段是 null
    assert_null(data["items"][0]["total_market_value"])
    assert_null(data["total_market_value"])

    # 038 基金分布看板
    response = client.get(f"/api/v1/dashboards/funds?return_date={RETURN_DATE}")
    body = response.get_json()
    data = body["data"]

    assert response.status_code == 200
    assert len(data["items"]) == 1

    item = data["items"][0]

    # 成本类字段照实返回
    assert_number(item["cost_amount"], 20000, 2)
    assert_number(data["total_cost_amount"], 20000, 2)

    # 只有一只基金，成本占比是 1（100%），不是 null
    assert_number(item["cost_ratio"], 1, 6)

    # 市值相关字段是 null
    assert_null(item["market_value"])
    assert_null(item["market_value_ratio"])
```

---

### 步骤 7：写 `038` 已知坑的回归用例

**必要性：**
任务 `038` 的常见坑第 1 条记录了一个只在特定数据顺序下才出现的 `TypeError`：聚合时如果把 `group["market_value"]` 直接赋成 `None`，那么「先处理缺净值的贡献者、再处理有净值的贡献者」时就会执行 `None += Decimal(...)` 而崩溃，接口返回 `500`。

这个 bug 有两个特点，决定了它必须靠测试守住：**只在特定顺序下触发**（换个博主顺序就复现不了，手工验证基本碰不到）；**看板的 `bloggers` 是 `ORDER BY id` 查出来的**，所以「缺净值的博主 id 更小」就是它的触发条件。

> **重要：如果实现本来就带这个 bug，这三个用例会变红。这是预期结果——只把结果反馈给协调人，不要在本任务里改业务代码。**

继续添加：

```python
def test_fund_dashboard_missing_nav_with_smaller_blogger_id(client):
    # 先创建的博主 id 更小，他持有的基金缺净值
    blogger_missing = create_blogger(client, name="顺序甲缺净值")
    fund_missing = create_fund(client, name="顺序甲缺净值基金", fund_code="NULL000011")
    build_position(client, blogger_missing, fund_missing, shares=10000,
                   cost_amount=20000, nav=None)

    # 后创建的博主 id 更大，他持有的基金有净值
    blogger_present = create_blogger(client, name="顺序乙有净值")
    fund_present = create_fund(client, name="顺序乙有净值基金", fund_code="NULL000012")
    build_position(client, blogger_present, fund_present, shares=4000,
                   cost_amount=10000, nav=2.5)

    response = client.get(f"/api/v1/dashboards/funds?return_date={RETURN_DATE}")
    body = response.get_json()

    # 本用例的核心：不能是 500
    assert response.status_code == 200
    assert body["code"] == 0

    data = body["data"]
    assert data["fund_count"] == 2

    by_fund_id = items_by(data, "fund_id")

    missing_item = by_fund_id[fund_missing["fund_id"]]
    assert_null(missing_item["nav"])
    assert_null(missing_item["nav_date"])
    assert_null(missing_item["market_value"])
    assert_null(missing_item["market_value_ratio"])

    present_item = by_fund_id[fund_present["fund_id"]]
    assert_number(present_item["nav"], 2.5, 4)
    assert_number(present_item["market_value"], 10000, 2)
    assert_null(present_item["market_value_ratio"])

    assert_null(data["total_market_value"])
    assert_number(data["total_cost_amount"], 30000, 2)


def test_fund_dashboard_missing_nav_with_larger_blogger_id(client):
    # 反过来的顺序：先创建的博主 id 更小且净值齐全
    blogger_present = create_blogger(client, name="反向甲有净值")
    fund_present = create_fund(client, name="反向甲有净值基金", fund_code="NULL000013")
    build_position(client, blogger_present, fund_present, shares=10000,
                   cost_amount=20000, nav=2.5)

    # 后创建的博主 id 更大且缺净值
    blogger_missing = create_blogger(client, name="反向乙缺净值")
    fund_missing = create_fund(client, name="反向乙缺净值基金", fund_code="NULL000014")
    build_position(client, blogger_missing, fund_missing, shares=5000,
                   cost_amount=10000, nav=None)

    response = client.get(f"/api/v1/dashboards/funds?return_date={RETURN_DATE}")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    data = body["data"]
    by_fund_id = items_by(data, "fund_id")

    assert_null(by_fund_id[fund_missing["fund_id"]]["market_value"])
    assert_number(by_fund_id[fund_present["fund_id"]]["market_value"], 25000, 2)
    assert_null(data["total_market_value"])


def test_fund_dashboard_same_fund_missing_nav_for_two_bloggers(client):
    blogger_a = create_blogger(client, name="共用基金甲")
    blogger_b = create_blogger(client, name="共用基金乙")
    shared_fund = create_fund(client, name="共用缺净值基金", fund_code="NULL000015")

    # 两个博主持有同一只基金（同一个 fund_id），该基金当天没有净值。
    # 只创建一次基金，把同一个 fund 变量传给两条持仓，避免 fund_code 重复。
    build_position(client, blogger_a, shared_fund, shares=10000,
                   cost_amount=20000, nav=None)
    build_position(client, blogger_b, shared_fund, shares=4000,
                   cost_amount=8000, nav=None)

    response = client.get(f"/api/v1/dashboards/funds?return_date={RETURN_DATE}")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    data = body["data"]

    # 同一只基金被两个博主持有，items 里仍然只有一行
    assert data["fund_count"] == 1
    assert len(data["items"]) == 1

    item = data["items"][0]

    # blogger_count 是去重的博主数
    assert item["blogger_count"] == 2

    # 份额和成本跨博主累加
    assert_number(item["shares"], 14000, 4)
    assert_number(item["cost_amount"], 28000, 2)

    # 缺净值：市值和市值占比是 null
    assert_null(item["market_value"])
    assert_null(item["market_value_ratio"])

    # 成本占比照实返回：28000 / 28000 = 1
    assert_number(item["cost_ratio"], 1, 6)
```

前两个用例造的数据完全一样，**只有博主的创建顺序不同**，因此 id 大小关系不同——这正是那个 `TypeError` 的触发/不触发条件，两个方向都要跑。第三个用例验证跨博主分组：两个博主引用同一个 `shared_fund`，`items` 里仍然只有一行。

---

### 步骤 8：运行测试并自查

**必要性：**
写完必须实际运行。null 断言和占比期望值都是手算的，只有真正跑一遍才能确认手算和实现一致——尤其 `market_value_ratio` 保留 6 位，差一位就会红。

```bash
pytest tests/test_dashboard_nulls.py -q
```

预期 8 个测试全部通过。然后执行全量测试，确认没有影响其他模块：

```bash
pytest -q
```

预期全部通过，没有 failed 也没有 error。**再次确认：运行 `pytest` 时连接的是 `fund_test_db`。**

---

## 验证方式

1. **专项测试**：`pytest tests/test_dashboard_nulls.py -q` 预期 8 个测试全部通过。
2. **全量测试**：`pytest -q` 预期全部通过，没有 failed 也没有 error。
3. **确认连的是测试库**：`grep -n "fund_test_db" tests/conftest.py` 预期能看到 `os.environ["DB_NAME"] = "fund_test_db"`；`grep -rn "fund_db" tests/` 预期**没有任何输出**。
4. **确认工厂函数没有重复定义**：`grep -rn "def create_" tests/` 预期每个工厂函数只有一处定义，都在 `tests/factories.py`。

## 常见坑

### 1. 连错了数据库，把开发数据清空了
后果最严重的一个错误。`clean_db` 在每个测试前 `TRUNCATE` 表，连到 `fund_db` 就是清空开发库。排查用 `grep -n "DB_NAME" tests/conftest.py`、`grep -n "assert_test_database" tests/conftest.py`；如果 `assert_test_database()` 被注释掉了，恢复它（它在任何 `TRUNCATE` 之前检查数据库名）。

### 2. 用 `not value` 判断 null
`0` 在 Python 里是假值。看板里「没有任何持仓」时总市值就是合法的 `0`。写 `assert not data["total_market_value"]` 的话，实现返回 `0` 和返回 `null` 都能通过，测试就白写了。必须写 `assert data["total_market_value"] is None`，也就是用步骤 3 的 `assert_null()`。

### 3. 把 `037` 的 `items[]` 当成有 `funds` 数组
`/dashboards/bloggers` 的 `items[]` 里只有 `fund_count`，**没有** `funds` 数组；`funds` 是 `/api/v1/returns/summary`（任务 `036`）的结构。

### 4. 以为 `038` 里缺净值的基金会让别人也变 null
不会。基金级规则是「只影响缺的那一只自己」；被连坐的是**总市值**和**所有** `market_value_ratio`。这两句话要**分开断言**：有净值基金的 `market_value` 是数值，有净值基金的 `market_value_ratio` 是 `null`。混成一个循环里写，出问题时看不出是哪条坏了。

### 5. 依赖 `items` 的下标顺序
`037` 的 `items` 按博主遍历顺序，`038` 的 `items` 按 `cost_amount` 降序。取行时用步骤 3 的 `items_by(data, "fund_id")` / `items_by(data, "blogger_id")` 建字典，不要写 `items[0]`。

### 6. 用 `==` 直接比较浮点数
看板返回的 `cost_ratio`、`market_value_ratio` 是保留 6 位的浮点数。统一用 `assert_number(actual, expected, 6)`，它先 `Decimal(str(...)).quantize(..., ROUND_HALF_UP)`（四舍五入到指定位数）再比较，和 046/047 的口径一致——不要用 `round(float, n)`，那是银行家舍入（044 的新概念一节讲过为什么不行）。

### 7. 造基金时 fund_code 重复
同一批测试数据里每只基金的 `fund_code` 必须唯一，否则撞唯一索引返回 409，工厂函数里的 `assert` 会直接报错。反过来，希望两个博主共用同一只基金时只创建一次，把同一个 `fund` 变量传给两条持仓——步骤 7 第三个用例就是这么写的。

### 8. 把工厂函数当 pytest fixture 传参
见文档开头「先读这一条」里的正反例。本任务新写的测试不要照抄 `tests/factories.py` 里可能存在的历史写法（那些由任务 `043` 统一处理）。

## 完成标准

以下条件全部满足，任务 048 才算完成：

- [ ] `backend/tests/test_dashboard_nulls.py` 已创建，8 个测试函数都在。
- [ ] 有「净值齐全」的基准对照用例，断言市值、占比、总市值全都不是 `null`；基金级规则有测试：缺净值基金自己的 `nav` / `nav_date` / `market_value` / `market_value_ratio` 为 `null`，有净值基金照实返回。
- [ ] 博主级 null 规则有测试：名下任意一只缺净值，该博主合计为 `null`，但 `total_cost_amount` 照实返回。
- [ ] 全局级 null 规则有测试：任意基金缺净值 → 总市值/总收益/总收益率为 `null`，且 `/dashboards/funds` 里**所有**基金的 `market_value_ratio` 为 `null`。
- [ ] 成本类字段（`cost_amount`、`total_cost_amount`、`cost_ratio`）不为 `null` 有专门测试覆盖。
- [ ] `038` 已知坑的三个顺序用例都在，都断言不返回 500；「同一基金被两个博主共用」还断言了 `items` 只有一行、`blogger_count == 2`。
- [ ] `pytest tests/test_dashboard_nulls.py -q` 与 `pytest -q` 全部通过，没有 failed 也没有 error。
- [ ] 测试全程只连 `fund_test_db`，`grep -rn "fund_db" tests/` 没有任何输出。
- [ ] 没有修改任何业务代码；发现的不一致全部记录待反馈；没有把工厂函数当作 pytest fixture 使用。
- [ ] 步骤数与「必要性：」说明数量一致（都是 8）。

## 场景 ↔ 测试函数对照表

| 场景 | 测试函数 | 步骤 |
| --- | --- | --- |
| 净值齐全，全部返回数值（基准对照） | `test_fund_dashboard_all_nav_present` | 4 |
| 基金级：缺净值只影响自己 | `test_fund_dashboard_missing_nav_isolates_single_fund` | 4 |
| 博主级：名下任意一只缺 → 合计 null | `test_blogger_dashboard_missing_nav_makes_blogger_total_null` | 5 |
| 全局级：总市值 null + 所有占比 null | `test_dashboards_missing_nav_makes_global_total_null` | 5 |
| 成本类字段任何情况下不为 null | `test_dashboards_cost_fields_never_null` | 6 |
| `038` 坑：缺净值博主 id 更小 | `test_fund_dashboard_missing_nav_with_smaller_blogger_id` | 7 |
| `038` 坑：缺净值博主 id 更大 | `test_fund_dashboard_missing_nav_with_larger_blogger_id` | 7 |
| `038` 坑：同一基金被两个博主共用 | `test_fund_dashboard_same_fund_missing_nav_for_two_bloggers` | 7 |

## 完成后请反馈

1. 新增和修改的文件列表；`pytest tests/test_dashboard_nulls.py -q` 和 `pytest -q` 的完整输出；步骤数与「必要性：」说明数量是否一致。
2. 有没有发现代码和 `docs/api/v1-dashboards.md` 第 1.4 节或 `api-contract-gaps.md` 5.6 节不一致的地方（列出来，**不要自行修改**）。
3. 「缺净值博主 id 更小」那个回归测试是否真的变红过。**如果实现本来就有 bug，说明测试写对了，只反馈，不要在本任务里改业务代码。**
4. 哪些场景没有覆盖、遇到的问题和未完成项。
