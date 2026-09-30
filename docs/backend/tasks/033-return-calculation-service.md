# 任务 033：简单收益计算服务与精确净值查询工具

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务要新增收益计算 Service，并补充一个「精确日期净值查询」工具。涉及 `Decimal`、空值边界、市值、收益率和总市值聚合；但不涉及 Flask 路由。

## 任务目标

创建：

```text
backend/app/services/return_calculation.py
```

修改：

```text
backend/app/utils/snapshot_data.py
```

完成后可以：

1. 根据成本和市值计算收益金额、收益率。
2. 成本小于等于 0 时，收益率返回 `None`。
3. 市值缺失时，收益金额和收益率都返回 `None`。
4. 根据持仓快照和指定日期净值，计算每只基金的市值和收益。
5. 计算一组收益的总成本、总市值、总收益、总收益率。
6. 精确查询某一天的净值，不用最近一天净值兜底。
7. `pytest -q` 仍然全部通过。

## 范围说明

本任务只做计算和数据读取工具。

不包含：

- Flask 路由
- 权限校验
- 数据持久化
- 最大回撤
- 年化收益
- 夏普比率
- 净值复权

## 前置条件

1. 任务 030 已完成，`calculate_position_snapshots()` 可用。
2. 任务 031、032 已完成，持仓快照接口和测试通过。
3. `pytest -q` 当前全部通过。

## 新概念：Decimal 与精确日期净值

### Decimal

`Decimal` 是 Python 提供的十进制类型，适合金额和收益率计算。  
不要用 `float` 做金额累加，否则容易出现精度误差。

### 精确日期净值

本项目的收益口径要求：  
**只有指定日期当天有净值，才计算市值。**  
如果当天没有净值，市值返回 `null`，收益率也返回 `null`。

任务 029 已经在 `backend/app/utils/snapshot_data.py` 里写好了这个函数：

```python
get_nav_on_date_map()
```

它只匹配 `nav_date = return_date`，不做最近日期兜底。本任务直接用，不需要再写。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：确认精确日期净值查询函数可用

**必要性：**  
收益计算必须严格使用指定日期当天的净值。如果没有当天净值，应该返回 `null`，而不是拿最近一天的数据顶替。这个函数是任务 029 的产出，开始写计算逻辑前先确认它在。

执行：

```bash
grep -n "def get_nav_on_date_map" -A 3 app/utils/snapshot_data.py
```

预期能看到函数定义，并且 SQL 条件里是 `nav_date = %s`，**不是** `nav_date <= %s`。

函数应该长这样（任务 029 已写）：

```python
def get_nav_on_date_map(cursor, fund_ids, nav_date):
    fund_id_list = list(fund_ids)

    if not fund_id_list:
        return {}

    placeholders = ",".join(["%s"] * len(fund_id_list))

    cursor.execute(
        f"""
        SELECT
            fund_id,
            nav_date,
            nav
        FROM nav_history
        WHERE fund_id IN ({placeholders})
          AND nav_date = %s
        """,
        (*fund_id_list, nav_date)
    )

    return {
        row["fund_id"]: row
        for row in cursor.fetchall()
    }
```

要点：

- `nav_date` 是精确日期，不是「截止日期」。
- 返回值格式是 `fund_id -> 当天净值记录`。
- 如果当天没有净值，这个字典里没有该基金，调用方 `.get(fund_id)` 会拿到 `None`。

如果这个函数不存在，或者条件写成了 `nav_date <= %s`，先停下来反馈，不要在本任务里顺手改——那是任务 029 的验收漏项。

---

### 步骤 2：创建收益计算 Service 文件

**必要性：**  
收益计算是业务逻辑，不应该写在 Flask 路由里。单独放在 Service 层，后面单博主、单基金、总体汇总都可以复用。

新建文件：

```text
backend/app/services/return_calculation.py
```

先写入基础工具：

```python
from decimal import Decimal


ZERO = Decimal("0")


def _to_decimal(value):
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))
```

---

### 步骤 3：添加收益指标计算函数

**必要性：**  
收益金额和收益率有一组固定边界规则，必须集中处理，避免每个接口重复写错。

继续添加：

```python
def calculate_return_metrics(cost_amount, market_value):
    cost = _to_decimal(cost_amount)

    if market_value is None:
        return {
            "profit_amount": None,
            "return_rate": None,
        }

    market_value = _to_decimal(market_value)
    profit_amount = market_value - cost

    if cost <= ZERO:
        return_rate = None
    else:
        return_rate = profit_amount / cost

    return {
        "profit_amount": profit_amount,
        "return_rate": return_rate,
    }
```

说明：

- 成本小于等于 `0` 时，收益率返回 `None`。
- 市值缺失时，收益金额和收益率都返回 `None`。
- 这里不处理百分比转换，收益率仍然是小数，例如 `0.1234`。

---

### 步骤 4：添加单基金收益计算函数

**必要性：**  
持仓快照只算份额和成本，本任务要在此基础上补市值和收益。

继续添加：

```python
def calculate_position_returns(position_items, nav_map):
    result = []

    for item in position_items:
        fund_id = item["fund_id"]
        nav_record = nav_map.get(fund_id)

        if nav_record is None:
            nav = None
            nav_date = None
            market_value = None
        else:
            nav = _to_decimal(nav_record["nav"])
            nav_date = nav_record["nav_date"]
            market_value = _to_decimal(item["shares"]) * nav

        metrics = calculate_return_metrics(
            item["cost_amount"],
            market_value
        )

        result.append(
            {
                **item,
                "nav": nav,
                "nav_date": nav_date,
                "market_value": market_value,
                "profit_amount": metrics["profit_amount"],
                "return_rate": metrics["return_rate"],
            }
        )

    return result
```

说明：

- `position_items` 来自 `calculate_position_snapshots()`。
- `nav_map` 来自 `get_nav_on_date_map()`。
- 如果某只基金当天没有净值，它的 `market_value`、`profit_amount`、`return_rate` 都是 `None`。

---

### 步骤 5：添加总收益计算函数

**必要性：**  
单博主和总体汇总都需要“总成本、总市值、总收益、总收益率”。统一一个函数可以避免重复口径。

继续添加：

```python
def calculate_total_returns(return_items):
    total_cost_amount = ZERO

    for item in return_items:
        total_cost_amount += _to_decimal(item["cost_amount"])

    if any(item["market_value"] is None for item in return_items):
        total_market_value = None
    else:
        total_market_value = ZERO

        for item in return_items:
            total_market_value += _to_decimal(item["market_value"])

    metrics = calculate_return_metrics(
        total_cost_amount,
        total_market_value
    )

    return {
        "total_cost_amount": total_cost_amount,
        "total_market_value": total_market_value,
        "profit_amount": metrics["profit_amount"],
        "return_rate": metrics["return_rate"],
    }
```

说明：

- 只要有一只基金当天没有净值，总市值就是 `None`。
- 总成本仍然可以计算，因为成本来自持仓和操作记录，不依赖净值。
- 如果 `return_items` 为空，总成本是 `0`，总市值是 `0`，收益率是 `None`。

---

### 步骤 6：语法检查

**必要性：**  
先确认新文件没有语法错误，再进入接口开发。

执行：

```bash
python -m py_compile app/services/return_calculation.py
python -m py_compile app/utils/snapshot_data.py
```

预期都没有输出，并且退出码是 `0`。

---

### 步骤 7：运行已有测试

**必要性：**  
确认新增文件没有影响已有模块。

执行：

```bash
pytest -q
```

预期全部通过。

## 验证方式

### 1. 语法检查

```bash
python -m py_compile app/services/return_calculation.py
python -m py_compile app/utils/snapshot_data.py
```

预期没有输出。

### 2. 已有测试

```bash
pytest -q
```

预期全部通过。

### 3. 手动调用收益计算

在 `backend` 目录执行：

```bash
python -c "from app.services.return_calculation import calculate_return_metrics; print(calculate_return_metrics(100, 120)); print(calculate_return_metrics(0, 120)); print(calculate_return_metrics(100, None))"
```

预期输出类似：

```text
{'profit_amount': Decimal('20'), 'return_rate': Decimal('0.2')}
{'profit_amount': Decimal('120'), 'return_rate': None}
{'profit_amount': None, 'return_rate': None}
```

## 常见坑

### 1. 使用最近一天净值兜底

收益接口必须使用指定日期当天的净值。  
不要使用 `get_latest_nav_map()`。

### 2. 用 float 累加金额

金额、市值、成本、收益都应该用 `Decimal`。  
不要用 `float`。

### 3. 成本为 0 时继续除法

成本小于等于 `0` 时，收益率必须返回 `None`。  
否则会出现除零错误。

### 4. 忽略部分基金缺净值

只要有一只基金缺当天净值，总市值就应该返回 `None`。  
不要只加有净值的部分。

## 完成标准

以下条件全部满足，任务 033 才算完成：

1. `backend/app/utils/snapshot_data.py` 中存在 `get_nav_on_date_map()`。
2. `backend/app/services/return_calculation.py` 已创建。
3. `calculate_return_metrics()`、`calculate_position_returns()`、`calculate_total_returns()` 都存在。
4. 成本小于等于 0 时收益率是 `None`。
5. 缺净值时市值、收益金额、收益率都是 `None`。
6. `pytest -q` 全部通过。

## 完成后请反馈

1. 新增和修改的文件列表。
2. 语法检查输出。
3. `pytest -q` 的完整输出。
4. 手动调用收益计算的输出。
5. 遇到的问题和未完成项。
