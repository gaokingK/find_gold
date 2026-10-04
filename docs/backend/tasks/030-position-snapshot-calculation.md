# 任务 030：单个博主持仓快照计算

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务要把初始持仓和操作记录合成一个可用的快照结果，涉及按基金分组、Decimal 精度、平均成本法、卖出和分红处理。逻辑比单纯 CRUD 复杂，但还不需要接接口。

## 任务目标

创建：

```text
backend/app/services/position_snapshot.py
```

完成后可以：

1. 输入某个博主的初始持仓和操作记录。
2. 按基金分组计算：
   - 初始份额和初始成本
   - 累计买入份额和买入金额
   - 累计卖出份额和卖出金额
   - 累计现金分红金额
   - 当前份额
   - 当前成本
3. 不落库，只返回计算结果。
4. `pytest -q` 仍然全部通过。

## 范围说明

本任务只做纯计算，不接 Flask 路由。

不包含：

- 查询数据库
- 接口路由
- 市值计算
- 收益率计算
- 持仓快照持久化
- 超额卖出校验

## 前置条件

1. 任务 029 已完成，`snapshot_data.py` 可用。
2. `pytest -q` 当前全部通过。
3. 已理解操作记录里的 `buy`、`sell`、`dividend_cash`。

## 新概念：Service 层与平均成本法

### Service 层

Service 层是“业务计算层”。  
它不关心 HTTP 请求，也不直接写 SQL，只负责把输入数据计算成业务结果。

### 平均成本法

平均成本法是指：卖出时按当前持有份额的平均成本扣减成本。  
例如当前持有 100 份、成本 200 元，平均成本是 2 元/份。卖出 30 份，就扣减 60 元成本，剩 140 元成本和 70 份。

本任务会用 `Decimal`。它适合金额计算，可以避免 `float` 的精度误差。

## 执行目录

```bash
cd /d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建 Service 文件

**必要性：**  
持仓快照是业务计算，不是简单的数据格式转换。放在 `services` 目录里，后面收益计算也可以复用类似的分层方式。

新建目录和文件：

```text
backend/app/services/position_snapshot.py
```

先写入：

```python
from collections import defaultdict
from decimal import Decimal


ZERO = Decimal("0")


def _to_decimal(value):
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))
```

说明：

- `defaultdict(list)` 是一种特殊字典。访问不存在的 key 时，会自动创建默认值，这里默认值是空列表。
- `_to_decimal()` 用来把数据库或测试里的数字统一转成 `Decimal`。

---

### 步骤 2：按基金分组初始持仓和操作记录

**必要性：**  
快照必须按“博主 + 基金”计算。分组后才能逐只基金累加买卖和分红。

继续添加：

```python
def _group_initial_positions(initial_positions):
    grouped = defaultdict(list)

    for row in initial_positions:
        grouped[row["fund_id"]].append(row)

    return grouped


def _group_operations(operations):
    grouped = defaultdict(list)

    for row in operations:
        grouped[row["fund_id"]].append(row)

    return grouped
```

---

### 步骤 3：确定每只基金的起点

**必要性：**  
如果同一只基金有多条初始持仓，第一版取最早的一条作为起点，避免重复累加。

继续添加：

```python
def _pick_first_initial_position(rows):
    if not rows:
        return None

    return min(rows, key=lambda row: (row["record_date"], row["id"]))
```

---

### 步骤 4：实现快照计算函数

**必要性：**  
这是本任务的核心。它要把起点、买入、卖出、分红合成为一个结果。

继续添加：

```python
def calculate_position_snapshots(initial_positions, operations):
    grouped_initial_positions = _group_initial_positions(initial_positions)
    grouped_operations = _group_operations(operations)

    fund_ids = set(grouped_initial_positions) | set(grouped_operations)
    result = []

    for fund_id in sorted(fund_ids):
        initial_position = _pick_first_initial_position(
            grouped_initial_positions.get(fund_id, [])
        )
        fund_operations = grouped_operations.get(fund_id, [])
        fund_operations.sort(key=lambda row: (row["operation_date"], row["id"]))

        if initial_position is None:
            fund_name = fund_operations[0]["fund_name"]
            fund_code = fund_operations[0]["fund_code"]
            initial_record_date = None
            initial_shares = ZERO
            initial_cost_amount = ZERO
        else:
            fund_name = initial_position["fund_name"]
            fund_code = initial_position["fund_code"]
            initial_record_date = initial_position["record_date"]
            initial_shares = _to_decimal(initial_position["shares"])
            initial_cost_amount = _to_decimal(initial_position["cost_amount"])

        shares = initial_shares
        cost_amount = initial_cost_amount
        buy_shares = ZERO
        buy_amount = ZERO
        sell_shares = ZERO
        sell_amount = ZERO
        dividend_cash_amount = ZERO

        for row in fund_operations:
            operation_type = row["operation_type"]
            row_shares = _to_decimal(row["shares"])
            row_amount = _to_decimal(row["amount"])

            if operation_type == "buy":
                shares += row_shares
                cost_amount += row_amount
                buy_shares += row_shares
                buy_amount += row_amount

            elif operation_type == "sell":
                shares_before_sell = shares

                if shares_before_sell > ZERO:
                    average_cost = cost_amount / shares_before_sell
                    cost_amount -= average_cost * row_shares
                else:
                    # 第一版不校验超额卖出。
                    # 如果卖出前没有正份额，成本保持不变，只继续减少份额。
                    pass

                shares -= row_shares
                sell_shares += row_shares
                sell_amount += row_amount

            elif operation_type == "dividend_cash":
                dividend_cash_amount += row_amount

        result.append(
            {
                "fund_id": fund_id,
                "fund_name": fund_name,
                "fund_code": fund_code,
                "initial_record_date": initial_record_date,
                "initial_shares": initial_shares,
                "initial_cost_amount": initial_cost_amount,
                "buy_shares": buy_shares,
                "buy_amount": buy_amount,
                "sell_shares": sell_shares,
                "sell_amount": sell_amount,
                "dividend_cash_amount": dividend_cash_amount,
                "shares": shares,
                "cost_amount": cost_amount,
            }
        )

    return result
```

---

### 步骤 5：语法检查

**必要性：**  
先确认计算模块没有语法错误，再进入接口开发。

执行：

```bash
python -m py_compile app/services/position_snapshot.py
```

预期没有输出，并且退出码是 `0`。

---

### 步骤 6：运行已有测试

**必要性：**  
确认新增 Service 没有影响已有功能。

执行：

```bash
pytest -q
```

预期全部通过。

## 验证方式

### 1. 语法检查

```bash
python -m py_compile app/services/position_snapshot.py
```

预期没有输出。

### 2. 已有测试

```bash
pytest -q
```

预期全部通过。

### 3. 手动小样例

在 `backend` 目录执行：

```bash
python -c "from app.services.position_snapshot import calculate_position_snapshots; print(calculate_position_snapshots([], []))"
```

预期输出：

```text
[]
```

## 常见坑

### 1. 用 float 算金额

不要用 `float` 计算成本和金额。  
请使用 `Decimal`。

### 2. 忘记排序操作记录

同一基金、同一天可能有多笔操作。  
必须按 `operation_date` 和 `id` 排序，否则结果可能不稳定。

### 3. 把现金分红当成份额变化

本项目中 `dividend_cash` 只记录现金分红金额。  
它不增加份额，也不减少份额。

### 4. 试图在这里做超额卖出校验

第一版明确不校验超额卖出。  
份额可以为负，成本也可能为 0 或负数，接口照实返回。

## 完成标准

以下条件全部满足，任务 030 才算完成：

1. `backend/app/services/position_snapshot.py` 已创建。
2. `calculate_position_snapshots()` 存在。
3. 买入、卖出、分红三种操作都能参与计算。
4. 输出结果包含初始值、累计买卖、分红、当前份额和当前成本。
5. `pytest -q` 全部通过。

## 完成后请反馈

1. 新增和修改的文件列表。
2. 语法检查输出。
3. `pytest -q` 的完整输出。
4. 手动小样例输出。
5. 遇到的问题和未完成项。
