# 任务 046：收益模块 Service 层单元测试

## ⚠️ 先读这一条

**测试只允许连接 `fund_test_db`。**

`tests/conftest.py` 里的 `clean_db` 夹具会在**每个测试函数开始前**执行 `TRUNCATE` 把表清空。如果测试连到了开发库 `fund_db`，开发库里的数据会被清空，且无法恢复。

- 不要为了「看看真实数据」把 `DB_NAME` 改成 `fund_db`。
- 不要注释掉 `conftest.py` 里的 `assert_test_database()`。
- 本任务只有步骤 7 需要连数据库（测 `get_nav_on_date_map()`），其余 14 个测试全是纯函数调用，不碰数据库。

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：

1. 本任务共 **15 个测试函数**。其中 14 个是纯函数测试——手造几个字典、调一个函数、写 4–6 行断言，不需要造数据也不需要发请求，每个约 3 分钟，合计约 42 分钟。
2. 剩下 1 个（步骤 7）要连数据库、自己开 cursor，约 8 分钟。
3. 有 5 个用例需要先手算期望值（多初始持仓、同日操作顺序、分红、清仓后再卖、平均成本），每个约 5 分钟，合计约 25 分钟。
4. 检查 `033` 的函数签名、写公共辅助、运行测试与排查失败，约 45 分钟。

合计约 120 分钟，约 2 小时。

如果超时，**优先保证「边界与 null 场景」全部完成**（步骤 4、5、6），happy path 可以后续补充。

## 任务目标

创建：

```text
backend/tests/test_returns_service.py
```

完成后可以：

1. 直接调用 `033` 的三个收益计算函数，验证它们的返回值。
2. 验证成本 ≤ 0 时只有 `return_rate` 是 `null`，市值和收益金额照实返回。
3. 验证成本为负（超额卖出导致）照实返回，不截断到 0。
4. 验证缺净值时返回 `null` 而不是 `0`，并且汇总层在有持仓的前提下绝不为 `0`。
5. 验证「多条初始持仓只取最早一条」等四条计算口径。
6. 验证 `get_nav_on_date_map()` 只匹配精确日期，不用最近一天净值兜底。

## 为什么不测接口

本任务**只测函数，不发 HTTP 请求**。`034`、`035`、`036` 三个接口另有专门的任务测试（`047` 系列），那份文档里会用 Flask Test Client 发请求、断言状态码和响应 JSON。

两份分开的理由：函数级的用例跑得快、失败时定位准（报错直接指向某一行计算）；接口级的用例要造完整的博主 / 基金 / 持仓 / 操作 / 净值链路，写起来慢得多。如果混在一个文件里，接口测试会拖慢函数测试，而函数测试里最多的边界场景又会被接口测试的样板代码淹没。

## 范围说明

包含：

- `calculate_return_metrics()` 的边界测试
- `calculate_position_returns()` 的边界测试
- `calculate_total_returns()` 的边界测试
- `calculate_position_snapshots()` 的四条计算口径测试（多初始持仓、同日操作顺序、现金分红、卖出前份额为 0）
- `get_nav_on_date_map()` 的精确日期测试

不包含：

- `034`/`035`/`036` 三个 HTTP 接口的测试（那是 `047` 系列的范围）
- 看板模块的测试
- 修改任何业务代码（发现问题只反馈，不改）
- 性能测试

## 前置条件

1. 任务 `033` 已完成：`backend/app/services/return_calculation.py` 里存在 `calculate_return_metrics()`、`calculate_position_returns()`、`calculate_total_returns()`；`backend/app/utils/snapshot_data.py` 里有 `get_nav_on_date_map()`。（`033` 本身又依赖 `030` 的 `calculate_position_snapshots()`，本任务步骤 6 会用到它。）
2. 任务 `044` 已完成：步骤 2 要用的 `create_nav_history` 工厂函数由 044 步骤 7 产出到 `tests/factories.py`。
3. 任务 `043` 已完成，工厂函数统一为 `from factories import ...` 的写法。本任务只用到 `create_fund` 和 `create_nav_history` 两个。
4. `pytest -q` 当前全部通过。

## 新概念

### 1. Unit Test（单元测试）与 Interface Test（接口测试）

Unit Test 是**直接调用 Python 函数**、验证返回值是否符合预期的测试，不经过 HTTP。

Interface Test 是通过 Flask Test Client **发起 HTTP 请求**，验证状态码和响应 JSON 是否符合预期的测试。

`033` 产出的是纯计算函数，适合用单元测试：造好入参、调一次、断言返回值，几行就写完。`034`–`036` 是 HTTP 接口，只能用接口测试。

### 2. Null 与 0 的区别

`null`（Python 里是 `None`）表示**没有数据**；`0` 表示**数据算出来是 0**。

收益模块里这两者含义完全不同：某只基金当天没净值，市值是 `null`（没数据），不是 `0`（不是一分钱不值）。断言时必须用 `is None`，**不能**用 `not value`——因为 `0` 在 Python 里也是假值，`not 0` 是 `True`，会把「算出来是 0」和「没有数据」混为一谈，测试就白写了。

> `Decimal` 和 `ROUND_HALF_UP` 在任务 `033` 和 `044` 里已经介绍过，本任务直接用，不再重复讲解。

## 执行目录

所有命令都在下面目录执行（每次新开终端都要先激活虚拟环境）：

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 被测对象速查

| 函数 | 位置 | 入参 | 返回 |
| --- | --- | --- | --- |
| `calculate_return_metrics` | `app/services/return_calculation.py` | `cost_amount`、`market_value` | `{"profit_amount", "return_rate"}` |
| `calculate_position_returns` | 同上 | `position_items`（持仓列表）、`nav_map`（`fund_id -> 净值记录`） | 每项追加 `nav`、`nav_date`、`market_value`、`profit_amount`、`return_rate` |
| `calculate_total_returns` | 同上 | `return_items`（上面那个函数的返回） | `{"total_cost_amount", "total_market_value", "profit_amount", "return_rate"}` |
| `calculate_position_snapshots` | `app/services/position_snapshot.py` | `initial_positions`、`operations` | 每项含 `shares`、`cost_amount`、`dividend_cash_amount` 等 |
| `get_nav_on_date_map` | `app/utils/snapshot_data.py` | `cursor`、`fund_ids`、`nav_date` | `fund_id -> {"fund_id", "nav_date", "nav"}` |

三条口径（来自 `docs/api/v1-returns.md` 第 2.4 节的 null 真值表，本任务所有断言都要对照它）：

1. **`0` 只出现在「根本没有任何持仓」这一格。** 只要有持仓且缺净值，一律 `null`，绝不返回 `0`。
2. 成本 ≤ 0 时，`market_value` 和 `profit_amount` **照实返回数值**，只有 `return_rate` 是 `null`。不要把整行都返回 `null`。
3. 成本可以是负数（超额卖出导致），照实返回，不截断到 0，不抛异常。

发现代码和文档不一致时，**先停下来反馈**，不要自己改文档，也不要改断言去迁就代码。

---

## 具体步骤

### 步骤 1：确认 `033` 的函数签名

**必要性：**  
这些函数目前没有任何测试，签名只能以 `033` 的产出为准。先 `grep` 一遍确认名字、参数个数、返回字段名，比写完 15 个测试才发现参数顺序记错了再返工省事得多。

```bash
grep -n "^def " app/services/return_calculation.py app/utils/snapshot_data.py app/services/position_snapshot.py
```

预期能看到 `calculate_return_metrics`、`calculate_position_returns`、`calculate_total_returns`、`get_nav_on_date_map`、`calculate_position_snapshots` 五个函数。**如果任何一个不存在，停下来反馈**——那是 `029`/`030`/`033` 的验收漏项，不要在本任务里自己补实现。

顺手确认 `get_nav_on_date_map` 的 SQL 条件里是 `nav_date = %s` 而不是 `nav_date <= %s`：

```bash
grep -n "nav_date" app/utils/snapshot_data.py
```

### 步骤 2：新建测试文件并写公共辅助

**必要性：**  
收益测试是收益模块专属的，单独建文件可以避免和 `test_position_snapshots.py` 混在一起。把「断言是某个数值」和「断言是 null」抽成两个辅助函数，是为了让 15 个测试里的断言保持同一种写法——否则有人写 `is None`、有人写 `not value`，后者会漏掉「本该 null 却返回 0」的错误。

新建文件：

```text
backend/tests/test_returns_service.py
```

开头写入：

```python
from decimal import Decimal, ROUND_HALF_UP

from app.db import get_connection
from app.services.position_snapshot import calculate_position_snapshots
from app.services.return_calculation import (
    calculate_position_returns,
    calculate_return_metrics,
    calculate_total_returns,
)
from app.utils.snapshot_data import get_nav_on_date_map
from factories import create_fund, create_nav_history


MONEY = Decimal("0.0001")
RATE = Decimal("0.000001")

RETURN_DATE = "2026-01-31"
MISSING_NAV_DATE = "2026-02-01"


def assert_number(actual, expected, exp=MONEY):
    assert actual is not None, "期望是数值，实际是 None（本该有数据却返回了 null）"
    assert actual.quantize(exp, rounding=ROUND_HALF_UP) == Decimal(
        str(expected)
    ).quantize(exp, rounding=ROUND_HALF_UP)


def assert_null(actual):
    assert actual is None, f"期望是 null，实际是 {actual!r}"
```

说明：

- `from factories import ...` 这样写是因为 `tests` 目录里没有 `__init__.py`，pytest 会把 `tests` 目录本身加入模块搜索路径。**不要**写成 `from tests.factories import ...`。
- `assert_number()` 里先断言 `is not None`，是为了让「本该返回数值却返回了 `null`」这种失败信息更清楚。金额比较一律先 `quantize(..., ROUND_HALF_UP)` 再比较，**不要用 `float` 直接 `==`**——二进制浮点会有表示误差。
- `Decimal(str(expected))` 不要写成 `Decimal(expected)`：后者在 `expected` 是浮点时会把浮点误差原样带进来。
- `RETURN_DATE` 和 `MISSING_NAV_DATE` 是固定日期，不依赖「今天」，这样测试任何时候跑结果都一样。
- 步骤 2 之前先确认 `create_nav_history` 存在：`grep -n "def create_nav_history" tests/factories.py`。如果没有任何输出（即任务 044 尚未执行），先按 **044 步骤 7 的定义**把它补进 `backend/tests/factories.py` 再继续，不要自己另写一份。

---

### 步骤 3：测 `calculate_return_metrics()` 的四条边界

**必要性：**  
这个函数是整个收益模块的口径源头——三个接口的所有收益率最终都由它算出来。在函数层面把「成本 > 0 / = 0 / < 0 / 没有市值」四种情况测掉，后面的测试就只需要关心数据组装，不用再重复覆盖这些边界。

继续添加：

```python
def test_calculate_return_metrics_with_positive_cost():
    result = calculate_return_metrics(Decimal("100"), Decimal("120"))

    assert_number(result["profit_amount"], "20")
    assert_number(result["return_rate"], "0.2", RATE)


def test_calculate_return_metrics_with_zero_cost():
    result = calculate_return_metrics(Decimal("0"), Decimal("120"))

    # 成本为 0：收益金额照实返回 120，只有收益率是 null
    assert_number(result["profit_amount"], "120")
    assert_null(result["return_rate"])


def test_calculate_return_metrics_with_negative_cost():
    result = calculate_return_metrics(Decimal("-30"), Decimal("120"))

    # 成本为负：120 - (-30) = 150，照实返回，不截断到 0
    assert_number(result["profit_amount"], "150")
    assert_null(result["return_rate"])


def test_calculate_return_metrics_without_market_value():
    result = calculate_return_metrics(Decimal("100"), None)

    assert_null(result["profit_amount"])
    assert_null(result["return_rate"])
```

说明：成本为 `0` 时 `profit_amount = 120 - 0 = 120`，**必须照实返回 `120`**，不能因为收益率为 `null` 就把收益金额也变成 `null`——这正是 null 真值表里最容易写错的一格。

---

### 步骤 4：测 `calculate_position_returns()` 的基金级 null 口径

**必要性：**  
`calculate_return_metrics()` 只管两个数相减，而「整行到底哪些字段变 null」是在 `calculate_position_returns()` 里决定的。这一层最容易犯的错是「成本异常 → 整行都返回 null」，那样前端会把明明有市值的持仓显示成空卡片，必须在这一层单独锁住。

继续添加：

```python
def _position(fund_id, shares, cost_amount):
    return {
        "fund_id": fund_id,
        "fund_name": "测试基金",
        "fund_code": "TEST0001",
        "shares": Decimal(str(shares)),
        "cost_amount": Decimal(str(cost_amount)),
    }


def test_calculate_position_returns_missing_nav_returns_null():
    positions = [_position(1, "10000", "20000")]
    results = calculate_position_returns(positions, {})

    item = results[0]

    # 份额和成本不依赖净值，照实返回
    assert_number(item["shares"], "10000")
    assert_number(item["cost_amount"], "20000")

    # 净值相关字段全部是 null，不是 0
    assert_null(item["nav"])
    assert_null(item["nav_date"])
    assert_null(item["market_value"])
    assert_null(item["profit_amount"])
    assert_null(item["return_rate"])


def test_calculate_position_returns_zero_cost_keeps_numbers():
    positions = [_position(1, "1000", "0")]
    nav_map = {1: {"fund_id": 1, "nav_date": RETURN_DATE, "nav": Decimal("2.5")}}
    results = calculate_position_returns(positions, nav_map)

    item = results[0]

    # 成本 = 0：市值和收益金额照实返回数值，不是整行 null
    assert_number(item["market_value"], "2500")
    assert_number(item["profit_amount"], "2500")

    # 只有收益率是 null
    assert_null(item["return_rate"])


def test_calculate_position_returns_negative_cost_not_truncated():
    positions = [_position(1, "-500", "-500")]
    nav_map = {1: {"fund_id": 1, "nav_date": RETURN_DATE, "nav": Decimal("2.5")}}
    results = calculate_position_returns(positions, nav_map)

    item = results[0]

    # 负数份额和负数成本照实返回，不截断到 0
    assert_number(item["shares"], "-500")
    assert_number(item["cost_amount"], "-500")

    # 市值 = -500 × 2.5 = -1250；收益金额 = -1250 - (-500) = -750
    assert_number(item["market_value"], "-1250")
    assert_number(item["profit_amount"], "-750")
    assert_null(item["return_rate"])
```

说明：`nav_map` 里**没有**某个 `fund_id`，就表示这只基金当天没有净值（`get_nav_on_date_map()` 的返回也是这个语义）。`test_calculate_position_returns_missing_nav_returns_null` 传了空字典 `{}` 就是这个意思。

---

### 步骤 5：测 `calculate_total_returns()` 的汇总口径

**必要性：**  
这个函数决定「汇总层什么时候是 `null`、什么时候是 `0`」，是最容易写错、也最容易被前端感知的一处。「全部基金缺净值却返回总市值 0」这种错误会一路传到看板上，必须锁死。

继续添加：

```python
def test_calculate_total_returns_empty_items_returns_zero():
    result = calculate_total_returns([])

    # 空列表是唯一允许汇总层返回 0 的场景
    assert_number(result["total_cost_amount"], "0")
    assert_number(result["total_market_value"], "0")
    assert_number(result["profit_amount"], "0")
    assert_null(result["return_rate"])


def test_calculate_total_returns_all_missing_nav_never_returns_zero():
    items = [
        {"cost_amount": Decimal("100"), "market_value": None},
        {"cost_amount": Decimal("50"), "market_value": None},
    ]
    result = calculate_total_returns(items)

    # 有持仓但全部缺净值：绝不能返回 0
    assert result["total_market_value"] is None
    assert result["total_market_value"] != 0
    assert_null(result["total_market_value"])
    assert_null(result["profit_amount"])
    assert_null(result["return_rate"])

    # 成本不依赖净值，照实累加
    assert_number(result["total_cost_amount"], "150")


def test_calculate_total_returns_partial_missing_nav_is_null():
    items = [
        {"cost_amount": Decimal("100"), "market_value": Decimal("120")},
        {"cost_amount": Decimal("50"), "market_value": None},
    ]
    result = calculate_total_returns(items)

    # 只要有一项缺净值，总市值就是 null，不要把有市值的部分加起来（是 null 不是 170）
    assert_null(result["total_market_value"])
    assert_null(result["profit_amount"])
    assert_null(result["return_rate"])
    assert_number(result["total_cost_amount"], "150")
```

说明：`assert result["total_market_value"] != 0` 这一行是专门拦「把没数据当 0 返回」的，不要删。它和紧接着的 `assert_null()` 看起来重复，但前者能给出更直观的失败信息。

---

### 步骤 6：测 `calculate_position_snapshots()` 的四条计算口径

**必要性：**  
这四条口径是文档修订时定下来的，一旦有人「顺手优化」成累加或按日期分组，数字就全变了，而且接口不会报错——只是收益率悄悄不对了。用测试把口径锁住，比写在文档里可靠：文档会有人不读，测试不会有人不跑。

继续添加：

```python
def test_calculate_position_snapshots_uses_only_earliest_initial_position():
    fund_id = 1
    initial_positions = [
        {"id": 1, "fund_id": fund_id, "fund_name": "甲", "fund_code": "F001",
         "record_date": "2026-01-01", "shares": "1000", "cost_amount": "1000"},
        {"id": 2, "fund_id": fund_id, "fund_name": "甲", "fund_code": "F001",
         "record_date": "2026-01-05", "shares": "500", "cost_amount": "600"},
        {"id": 3, "fund_id": fund_id, "fund_name": "甲", "fund_code": "F001",
         "record_date": "2026-01-10", "shares": "200", "cost_amount": "300"},
    ]
    operations = [
        {"id": 1, "fund_id": fund_id, "fund_name": "甲", "fund_code": "F001",
         "operation_type": "buy", "operation_date": "2026-01-20",
         "shares": "100", "amount": "110"},
    ]
    results = calculate_position_snapshots(initial_positions, operations)

    item = results[0]

    # 只取 record_date 最早的那一條（1000 份 / 1000 元），其余两条完全不累加
    # 再加买入 100 份 / 110 元：份额 1100，成本 1110
    assert_number(item["shares"], "1100")
    assert_number(item["cost_amount"], "1110")


def test_calculate_position_snapshots_same_day_operations_ordered_by_id():
    fund_id = 1
    initial_positions = [
        {"id": 1, "fund_id": fund_id, "fund_name": "甲", "fund_code": "F001",
         "record_date": "2026-01-01", "shares": "1000", "cost_amount": "1000"},
    ]
    # 同一天两笔：先买（id 小）后卖（id 大）
    operations = [
        {"id": 1, "fund_id": fund_id, "fund_name": "甲", "fund_code": "F001",
         "operation_type": "buy", "operation_date": "2026-01-10",
         "shares": "1000", "amount": "1200"},
        {"id": 2, "fund_id": fund_id, "fund_name": "甲", "fund_code": "F001",
         "operation_type": "sell", "operation_date": "2026-01-10",
         "shares": "500", "amount": "700"},
    ]
    results = calculate_position_snapshots(initial_positions, operations)

    item = results[0]

    # 按 operation_id 升序：先买 → 份额 2000、成本 2200，单位成本 1.1
    # 再卖 → 卖出成本 500 × 1.1 = 550，份额 1500、成本 1650
    # 如果实现改成先卖后买，成本会是 1700，这个断言就会失败
    assert_number(item["shares"], "1500")
    assert_number(item["cost_amount"], "1650")


def test_calculate_position_snapshots_dividend_cash_not_counted_in_profit():
    fund_id = 1
    initial_positions = [
        {"id": 1, "fund_id": fund_id, "fund_name": "甲", "fund_code": "F001",
         "record_date": "2026-01-01", "shares": "1000", "cost_amount": "1000"},
    ]
    operations = [
        {"id": 1, "fund_id": fund_id, "fund_name": "甲", "fund_code": "F001",
         "operation_type": "dividend_cash", "operation_date": "2026-01-15",
         "shares": "0", "amount": "120"},
    ]
    snapshots = calculate_position_snapshots(initial_positions, operations)
    item = snapshots[0]

    # 现金分红不改变份额，也不改变成本（120 元只记在 dividend_cash_amount 里）
    assert_number(item["shares"], "1000")
    assert_number(item["cost_amount"], "1000")
    assert_number(item["dividend_cash_amount"], "120")

    # 第一版分红不计入收益金额：市值 1000 × 2.5 = 2500，收益 2500 - 1000 = 1500
    nav_map = {fund_id: {"fund_id": fund_id, "nav_date": RETURN_DATE, "nav": Decimal("2.5")}}
    returns = calculate_position_returns(snapshots, nav_map)

    assert_number(returns[0]["market_value"], "2500")
    assert_number(returns[0]["profit_amount"], "1500")
    assert_number(returns[0]["return_rate"], "1.5", RATE)


def test_calculate_position_snapshots_sell_when_shares_already_zero():
    fund_id = 1
    initial_positions = [
        {"id": 1, "fund_id": fund_id, "fund_name": "甲", "fund_code": "F001",
         "record_date": "2026-01-01", "shares": "1000", "cost_amount": "1000"},
    ]
    operations = [
        # 第一次卖出：清仓，份额 0，成本 0
        {"id": 1, "fund_id": fund_id, "fund_name": "甲", "fund_code": "F001",
         "operation_type": "sell", "operation_date": "2026-01-10",
         "shares": "1000", "amount": "1500"},
        # 第二次卖出：卖出前份额已经是 0，本次卖出成本记 0，不能抛除零异常
        {"id": 2, "fund_id": fund_id, "fund_name": "甲", "fund_code": "F001",
         "operation_type": "sell", "operation_date": "2026-01-20",
         "shares": "500", "amount": "750"},
    ]
    results = calculate_position_snapshots(initial_positions, operations)

    item = results[0]

    # 份额 -500，成本 0（不是负数，也不是报错）
    assert_number(item["shares"], "-500")
    assert_number(item["cost_amount"], "0")
```

说明：

- 入参是**普通字典列表**，不是数据库行。这些键名来自 `030`：`initial_positions` 需要 `id`、`fund_id`、`fund_name`、`fund_code`、`record_date`、`shares`、`cost_amount`；`operations` 需要 `id`、`fund_id`、`fund_name`、`fund_code`、`operation_type`、`operation_date`、`shares`、`amount`。
- 排序键是 `(record_date, id)` 和 `(operation_date, id)`，所以造数据时 `id` 必须给，而且**同日两笔的先后由 `id` 决定**，不是由列表顺序决定。
- 「同日先买后卖」和「同日先卖后买」的期望值不同（一个是 `1650`，一个是 `1700`），所以只写一个用例也能拦住「按日期分组后乱序处理」这类改动。
- 清仓后再卖出时「卖出前平均单位成本」的分子分母都是 0，实现必须单独处理成 0，不能直接做除法。如果这一步抛 `ZeroDivisionError`，说明 `030` 的实现漏了这个分支，**停下来反馈**，不要在本任务里改业务代码。

---

### 步骤 7：测 `get_nav_on_date_map()` 只匹配精确日期

**必要性：**  
「缺净值返回 null」这条口径的数据源头就是这个函数。如果它哪天被改成用最近一天净值兜底（`nav_date <= %s`），缺净值的场景就会算出市值而不是 `null`，而前面 14 个测试全是手造 `nav_map` 的，**一个都拦不住**。所以必须有一个真实查库的用例。

继续添加：

```python
def test_get_nav_on_date_map_only_matches_exact_date(client):
    fund = create_fund(client, name="净值查询基金", fund_code="RETSVC01")
    create_nav_history(client, fund["fund_id"], RETURN_DATE, "2.5000")

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            # 净值录在 RETURN_DATE：查同一天能取到
            nav_map = get_nav_on_date_map(cursor, [fund["fund_id"]], RETURN_DATE)

            assert fund["fund_id"] in nav_map
            assert_number(nav_map[fund["fund_id"]]["nav"], "2.5000")
            assert str(nav_map[fund["fund_id"]]["nav_date"]) == RETURN_DATE

            # 查 MISSING_NAV_DATE：当天没有净值，必须返回空字典，不能用最近一天兜底
            missing_map = get_nav_on_date_map(
                cursor, [fund["fund_id"]], MISSING_NAV_DATE
            )

            assert missing_map == {}

            # 空 fund_ids 直接返回空字典
            assert get_nav_on_date_map(cursor, [], RETURN_DATE) == {}
    finally:
        conn.close()
```

说明：

- 这是本任务**唯一**连数据库的用例，所以函数签名里要有 `client`（`clean_db` 夹具才会生效）。它连的是 `fund_test_db`，由 `conftest.py` 设置，不要自己改。
- `conn` 必须放在 `try / finally` 里关闭，否则连接泄漏。
- `create_nav_history(client, fund_id, nav_date, nav)` 是工厂函数，`nav` 传字符串即可（026 的接口会转成 `Decimal` 存库）。

---

### 步骤 8：运行测试

**必要性：**  
写完必须实际运行。步骤 6 里有四条需要手算期望值的用例，只有真正跑一遍才能确认手算和实现一致。

```bash
pytest tests/test_returns_service.py -q
pytest -q
```

预期：本文件 15 个测试全部通过；全量没有 failed 也没有 error。

**再次确认：运行 `pytest` 时连接的是 `fund_test_db`。**

---

## 验证方式

### 1. 专项测试

```bash
pytest tests/test_returns_service.py -q
```

预期 15 个测试全部通过。

### 2. 全量测试

```bash
pytest -q
```

预期全部通过，没有 failed 也没有 error。

### 3. 确认连的是测试库

```bash
grep -n "fund_test_db" tests/conftest.py
grep -rn "fund_db" tests/
```

第一条预期能看到 `DB_NAME` 被设成 `fund_test_db`；第二条预期**没有任何输出**（`fund_test_db` 不算，它是测试库名）。如果 `tests/` 下出现裸的 `fund_db`，说明夹具被改错了，立即停止并反馈。

### 4. 确认工厂函数没有重复定义

```bash
grep -rn "def create_" tests/
```

预期每个工厂函数只有一处定义，都在 `tests/factories.py`。

---

## 常见坑

### 1. 连错了数据库，把开发数据清空了

这是本项目测试里后果最严重的一个错误。`clean_db` 会在每个测试前 `TRUNCATE` 表，连到 `fund_db` 就是清空开发库。

排查：`grep -n "DB_NAME" tests/conftest.py` 和 `grep -n "assert_test_database" tests/conftest.py`。如果 `assert_test_database()` 被注释掉了，恢复它（它在任何 `TRUNCATE` 之前检查数据库名）。

### 2. 用 `not value` 判断 null

`0` 在 Python 里是假值。缺净值时如果写 `assert not item["market_value"]`，即使实现返回了 `0` 也会通过——测试就失去意义了。必须写 `assert item["market_value"] is None`（本任务的 `assert_null()` 就是干这个的）。

### 3. 用 `float` 直接 `==` 比较金额

`Decimal` 除法（算收益率时）可能产生无限小数，转成 `float` 再比较会有表示误差。统一用 `assert_number(actual, expected, exp)`，它先 `quantize(..., ROUND_HALF_UP)` 再比较。

### 4. 把工厂函数当 pytest fixture 传参

错误写法：

```python
def test_xxx(client, create_fund):     # 错误
    fund = create_fund(client)
```

`create_fund` 是普通函数不是 fixture，pytest 会报 `fixture 'create_fund' not found`。正确写法是 `from factories import create_fund`，然后在函数体里调用。

### 5. 造初始持仓 / 操作时漏了 `id` 字段

`calculate_position_snapshots()` 的排序键是 `(record_date, id)` 和 `(operation_date, id)`。字典里不给 `id` 会抛 `KeyError`；给了重复的 `id` 则同日顺序不确定，测试会随机失败。

### 6. 用「今天」当净值日期

净值日期不能用 `datetime.today()` 这类动态值，否则周末和节假日没有净值，测试会随机失败。统一用 `RETURN_DATE` / `MISSING_NAV_DATE` 这两个固定日期常量。

### 7. 指望 `assert_number` 能比较 `None`

`assert_number()` 里第一行就是 `assert actual is not None`。如果你想断言某个字段是 `null`，用 `assert_null()`，不要用 `assert_number(x, "0")`。

---

## 完成标准

以下条件全部满足，任务 046 才算完成：

- [ ] `backend/tests/test_returns_service.py` 已创建，包含 15 个测试函数。
- [ ] 成本 = 0 的用例断言了 `profit_amount` 照实返回数值、只有 `return_rate` 是 `null`（不是整行 `null`）。
- [ ] 成本为负的用例断言了负数成本照实返回，不截断到 0。
- [ ] 缺净值的用例断言了 `nav` / `nav_date` / `market_value` / `profit_amount` / `return_rate` 全部是 `null`，不是 `0`。
- [ ] 「有持仓但全部基金缺净值」的用例断言了汇总层**不是** `0`。
- [ ] 「部分基金缺净值」的用例断言了汇总层是 `null`，而不是只把有市值的部分加起来。
- [ ] 「空列表」的用例断言了汇总层是 `0`、收益率是 `null`（这是唯一返回 `0` 的场景）。
- [ ] 有多初始持仓只取 `record_date` 最早一条的用例，且断言了其余两条完全不累加。
- [ ] 有同日多笔操作按 `id` 升序处理的用例，且期望值与「先卖后买」不同。
- [ ] 有现金分红不改变份额和成本、且不计入收益金额的用例。
- [ ] 有卖出前份额为 0 时本次卖出成本记 0、不抛除零异常的用例。
- [ ] 有 `get_nav_on_date_map()` 只匹配精确日期、不用最近一天兜底的用例。
- [ ] 金额比较全部走 `Decimal` + `ROUND_HALF_UP`，没有用 `float` 直接 `==`。
- [ ] `pytest tests/test_returns_service.py -q` 全部通过。
- [ ] `pytest -q` 全部通过，没有 failed 也没有 error。
- [ ] 测试全程只连 `fund_test_db`，`tests/` 目录下没有任何裸的 `fund_db`。
- [ ] 没有修改任何业务代码；发现的不一致全部记录待反馈。
- [ ] 没有把工厂函数当作 pytest fixture 使用。

---

## 完成后请反馈

1. 新增和修改的文件列表。
2. `pytest tests/test_returns_service.py -q` 的完整输出（15 个测试）。
3. `pytest -q` 的完整输出。
4. 「场景 ↔ 测试函数」对照表（15 行即可，一行一个测试函数 + 它守的是哪条口径）。
5. 步骤数与「必要性：」说明数量是否一致（应为 8 对 8）。
6. 有没有发现代码和 `docs/api/v1-returns.md` 或 `api-contract-gaps.md` 5.5 节不一致的地方（列出来，不要自行修改）。
7. 哪些场景没有覆盖，原因是什么。
8. 遇到的问题和未完成项。
