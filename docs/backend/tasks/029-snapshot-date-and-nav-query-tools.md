# 任务 029：快照日期与数据读取工具

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务要新建一个独立的查询工具文件，统一处理快照日期解析、初始持仓读取、操作记录读取和指定日期净值查询。SQL 条件较多，但都是单表或简单 JOIN，不涉及写入。

## 任务目标

创建：

```text
backend/app/utils/snapshot_data.py
```

完成后可以：

1. 把字符串格式的快照日期解析成 `datetime.date`。
2. 默认日期是今天。
3. 查询某个博主在指定日期前的初始持仓。
4. 查询某个博主在指定日期前的操作记录。
5. 查询一批基金在**指定日期当天**的净值（当天没有就查不到，不做最近日期兜底）。
6. `pytest -q` 仍然全部通过。

## 范围说明

本任务只做数据读取和日期解析。

不包含：

- 持仓快照计算
- Flask 路由
- 写数据库
- 收益计算
- 导出 CSV
- 权限校验

## 前置条件

1. 任务 028 已完成，净值模块和测试都通过。
2. `pytest -q` 当前全部通过。
3. 数据库中已经存在 `bloggers`、`funds`、`initial_positions`、`operations`、`nav_history` 表。

## 新概念：查询辅助函数

查询辅助函数是把“数据库怎么查”和“接口怎么响应”分开。

这样做的目的：

1. 后面第 30、31 个任务可以直接复用这些函数。
2. 第 8 天的收益计算也能复用日期和净值查询。
3. 查询逻辑出问题时，只需要改一个文件。

本任务会用到 `datetime.strptime()`。它用于把字符串按指定格式解析成 Python 的日期对象。

## 执行目录

```bash
cd /d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建工具文件

**必要性：**  
快照模块会在接口、服务、测试里反复用到同一批数据读取逻辑。提前独立成文件，后面不需要复制 SQL。

新建文件：

```text
backend/app/utils/snapshot_data.py
```

先写入日期解析函数：

```python
from datetime import date, datetime


def parse_snapshot_date(raw_snapshot_date):
    if raw_snapshot_date in (None, ""):
        return date.today()

    try:
        return datetime.strptime(
            raw_snapshot_date,
            "%Y-%m-%d"
        ).date()
    except (TypeError, ValueError):
        return None
```

说明：

- `raw_snapshot_date` 是字符串，例如 `"2026-09-30"`。
- 如果没有传日期，默认使用今天。
- 解析失败时返回 `None`，由路由统一返回参数错误。

---

### 步骤 2：添加初始持仓查询函数

**必要性：**  
快照以初始持仓为起点。没有这个函数，后面的计算模块就无法拿到起点数据。

继续添加：

```python
def get_initial_positions(cursor, blogger_id, snapshot_date):
    cursor.execute(
        """
        SELECT
            ip.id,
            ip.blogger_id,
            ip.fund_id,
            ip.shares,
            ip.cost_amount,
            ip.record_date,
            f.name AS fund_name,
            f.fund_code
        FROM initial_positions AS ip
        JOIN funds AS f ON f.id = ip.fund_id
        WHERE ip.blogger_id = %s
          AND ip.record_date <= %s
        ORDER BY ip.fund_id, ip.record_date, ip.id
        """,
        (blogger_id, snapshot_date)
    )
    return cursor.fetchall()
```

说明：

- `record_date <= snapshot_date` 表示只取快照日期之前或当天的初始持仓。
- `JOIN funds` 是为了把基金名称和基金代码一起带出来，避免后面再查一次。
- `ORDER BY ip.fund_id, ip.record_date, ip.id` 让同一只基金的多条初始持仓按时间排列。

---

### 步骤 3：添加操作记录查询函数

**必要性：**  
快照要在初始持仓基础上叠加买入、卖出和分红。操作记录必须按时间排序，否则计算结果不稳定。

继续添加：

```python
def get_operations(cursor, blogger_id, snapshot_date):
    cursor.execute(
        """
        SELECT
            o.id,
            o.blogger_id,
            o.fund_id,
            o.operation_type,
            o.operation_date,
            o.shares,
            o.amount,
            f.name AS fund_name,
            f.fund_code
        FROM operations AS o
        JOIN funds AS f ON f.id = o.fund_id
        WHERE o.blogger_id = %s
          AND o.operation_date <= %s
        ORDER BY o.fund_id, o.operation_date, o.id
        """,
        (blogger_id, snapshot_date)
    )
    return cursor.fetchall()
```

说明：

- `operation_date <= snapshot_date` 表示只统计快照日期之前或当天的操作。
- `ORDER BY o.fund_id, o.operation_date, o.id` 保证同一基金、同一天的多笔操作按 ID 顺序处理。

---

### 步骤 4：添加指定日期净值查询函数

**必要性：**  
第 8 天的收益计算需要「指定日期**当天**的净值」。这个函数先在这里准备好，避免第 8 天同时写业务逻辑和查询逻辑。

本项目的收益口径是：**只有指定日期当天有净值，才计算市值；当天没有净值，市值和收益率都返回 `null`。**  
所以这个函数只匹配 `nav_date = %s`，**不做「最近一天净值」兜底**。前端需要能区分「亏到 0」和「没数据」，拿前一天的净值顶替会把这两种情况混在一起。

继续添加：

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

说明：

- `fund_ids` 是基金 ID 列表。
- `nav_date` 是精确日期，不是「截止日期」。
- 返回值是字典，格式是 `fund_id -> 当天净值记录`。
- **如果某只基金当天没有净值，这个字典里就没有这个 `fund_id`。** 调用方用 `nav_map.get(fund_id)` 取不到就当作「缺净值」，返回 `null`。
- 动态生成的 `placeholders` 只包含 `%s` 占位符，真正的基金 ID 仍然通过参数传入，不会拼接用户输入。
- 这个函数本任务先准备好，第 8 天的任务 033 计算市值时会用。

**不要**顺手写一个「取指定日期或之前最近一天净值」的版本（用 `MAX(nav_date)` 子查询那种）。第 8 天和第 9 天的所有收益、看板接口都明确禁止用最近净值兜底，写了也是死代码，而且很容易有人误用。

---

### 步骤 5：语法检查

**必要性：**  
先确认文件本身没有语法错误，再继续写业务计算。

执行：

```bash
python -m py_compile app/utils/snapshot_data.py
```

预期没有输出，并且退出码是 `0`。

---

### 步骤 6：运行已有测试

**必要性：**  
确认新文件没有影响已有模块。

执行：

```bash
pytest -q
```

预期全部通过。

## 验证方式

### 1. 语法检查

```bash
python -m py_compile app/utils/snapshot_data.py
```

预期没有输出。

### 2. 已有测试

```bash
pytest -q
```

预期全部通过。

### 3. 手动调用日期解析

在 `backend` 目录执行：

```bash
python -c "from app.utils.snapshot_data import parse_snapshot_date; print(parse_snapshot_date('2026-09-30')); print(parse_snapshot_date('bad-date')); print(parse_snapshot_date(None))"
```

预期输出类似：

```text
2026-09-30
None
2026-09-30
```

第三行是你执行命令时的今天日期。

## 常见坑

### 1. 日期写成字符串比较

数据库里的 `DATE` 字段在 Python 中通常是 `datetime.date`。  
不要把它当成字符串手动比较。

### 2. 忘记 `ORDER BY`

同一只基金可能有多条初始持仓或多笔操作。  
如果没有排序，计算结果可能不稳定。

### 3. 把用户输入直接拼进 SQL

基金 ID 列表必须通过 `%s` 参数传入。  
不要把 ID 直接拼进 SQL 字符串。

### 4. 忘记处理空基金列表

`IN ()` 不是合法 SQL。  
`get_nav_on_date_map()` 必须在 `fund_id_list` 为空时直接返回 `{}`。

### 5. 用「最近一天净值」兜底

`get_nav_on_date_map()` 的条件必须是 `nav_date = %s`，不是 `nav_date <= %s` 加 `MAX()`。

本项目所有收益和看板接口的口径都是：当天没有净值就返回 `null`。  
拿前一天的净值顶替，前端就分不清「亏到 0」和「没数据」了。

## 完成标准

以下条件全部满足，任务 029 才算完成：

1. `backend/app/utils/snapshot_data.py` 已创建。
2. `parse_snapshot_date()` 存在。
3. `get_initial_positions()` 存在。
4. `get_operations()` 存在。
5. `get_nav_on_date_map()` 存在，且条件是 `nav_date = %s`。
6. 文件里**没有**「取最近一天净值」的函数。
7. `pytest -q` 全部通过。

## 完成后请反馈

1. 新增和修改的文件列表。
2. 语法检查输出。
3. `pytest -q` 的完整输出。
4. 手动调用 `parse_snapshot_date()` 的输出。
5. 遇到的问题和未完成项。
