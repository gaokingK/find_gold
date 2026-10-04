# 任务 039：近期操作统计接口

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务要新增一个日期范围统计接口，包含 SQL 聚合、日期范围校验和最近记录列表。逻辑集中在读取和统计，不涉及写入新表。

## 任务目标

修改：

```text
backend/app/routes/dashboards.py
```

完成后可以：

1. 访问 `GET /api/v1/dashboards/recent-operations`。
2. 不传参数时，默认统计最近 7 天，包含今天。
3. 支持 `start_date`、`end_date`、`limit`。
4. 返回买入、卖出、现金分红的数量、份额、金额汇总。
5. 返回按操作日期倒序排列的最近操作记录。
6. `pytest -q` 仍然全部通过。

## 范围说明

本任务只实现近期操作统计接口。

不包含：

- 操作记录编辑
- 自定义统计维度
- 分页
- 按博主或基金过滤
- 操作频率分析
- 手续费和税费统计

## 前置条件

1. 任务 037 已完成，`dashboards_bp` 已注册。
2. 任务 020、021 已完成，操作记录可创建、可查询。
3. `pytest -q` 当前全部通过。
4. 已阅读 `docs/api/v1-dashboards.md` 中「近期操作统计」部分。

## 新概念说明

### Aggregate Function（聚合函数）

Aggregate Function 是数据库里对多行数据做统计的函数，例如 `COUNT()`、`SUM()`。  
本任务用它统计操作数量、份额合计、金额合计。

### `COALESCE()`

`COALESCE()` 返回第一个不为 `NULL` 的值。  
当日期范围内没有操作记录时，`SUM()` 可能返回 `NULL`，这里用它兜底成 `0`。

### `timedelta`

`timedelta` 表示时间差。  
本任务用 `timedelta(days=6)` 把今天回退 6 天，得到包含今天在内的最近 7 天。

## 执行目录

```bash
cd /d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：补充日期和数量校验工具

**必要性：**  
近期统计需要处理开始日期、结束日期和返回条数上限。先补充校验工具，可以让路由逻辑更清晰。

打开：

```text
backend/app/routes/dashboards.py
```

把顶部日期导入改为：

```python
from datetime import date, timedelta
```

并增加一行导入，复用任务 023 定义的分页上限：

```python
from app.utils.list_params import MAX_PAGE_SIZE
```

在 `_to_number()` 后添加：

```python
def parse_positive_int(value):
    if isinstance(value, bool):
        return None

    try:
        result = int(value)
    except (TypeError, ValueError):
        return None

    if result <= 0:
        return None

    return result
```

说明：

- `parse_positive_int()` 校验 `limit`。
- `limit` 最大值直接用任务 023 的 `MAX_PAGE_SIZE`，**不要再写一个 `100`**。列表上限只应该有一个来源，否则以后调整上限会漏改这里。
- `isinstance(value, bool)` 那一行是必要的：Python 里 `isinstance(True, int)` 是 `True`，不排除的话 `?limit=true` 会被当成 `limit=1`。
- 任务 038 已经在这个文件里定义了 `ZERO = Decimal("0")` 和 `_to_decimal()`，本任务直接用，不要重复定义。

---

### 步骤 2：添加操作记录序列化函数

**必要性：**  
数据库返回的日期是 `date`，金额和份额是 `Decimal`，必须转换成 JSON 友好的数据。

继续添加：

```python
def _serialize_operation_item(row):
    return {
        "operation_id": row["id"],
        "blogger_id": row["blogger_id"],
        "blogger_name": row["blogger_name"],
        "fund_id": row["fund_id"],
        "fund_name": row["fund_name"],
        "fund_code": row["fund_code"],
        "operation_type": row["operation_type"],
        "operation_date": row["operation_date"].strftime("%Y-%m-%d"),
        "shares": _to_number(row["shares"], 4),
        "amount": _to_number(row["amount"], 2)
    }
```

---

### 步骤 3：实现近期操作统计路由

**必要性：**  
这一步把日期范围校验、范围汇总和最近记录列表组合成一个完整接口。

在 `backend/app/routes/dashboards.py` 末尾添加：

```python
@dashboards_bp.get("/api/v1/dashboards/recent-operations")
def get_recent_operation_statistics():
    raw_end_date = request.args.get("end_date")
    end_date = parse_snapshot_date(raw_end_date)

    if end_date is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "end_date",
                    "message": "结束日期格式必须是 YYYY-MM-DD"
                }
            ],
            http_status=400
        )

    if end_date > date.today():
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "end_date",
                    "message": "结束日期不能晚于今天"
                }
            ],
            http_status=400
        )

    raw_start_date = request.args.get("start_date")

    if raw_start_date in (None, ""):
        start_date = end_date - timedelta(days=6)
    else:
        start_date = parse_snapshot_date(raw_start_date)

        if start_date is None:
            return error(
                code="VALIDATION_ERROR",
                message="参数校验失败",
                details=[
                    {
                        "field": "start_date",
                        "message": "开始日期格式必须是 YYYY-MM-DD"
                    }
                ],
                http_status=400
            )

        if start_date > end_date:
            return error(
                code="VALIDATION_ERROR",
                message="参数校验失败",
                details=[
                    {
                        "field": "start_date",
                        "message": "开始日期不能晚于结束日期"
                    }
                ],
                http_status=400
            )

    limit = parse_positive_int(request.args.get("limit", 20))

    if limit is None or limit > MAX_PAGE_SIZE:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "limit",
                    "message": f"limit 必须是 1 到 {MAX_PAGE_SIZE} 之间的正整数"
                }
            ],
            http_status=400
        )

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    operation_type,
                    COUNT(*) AS operation_count,
                    COALESCE(SUM(shares), 0) AS total_shares,
                    COALESCE(SUM(amount), 0) AS total_amount
                FROM operations
                WHERE operation_date >= %s
                  AND operation_date <= %s
                GROUP BY operation_type
                """,
                (start_date, end_date)
            )
            summary_rows = cursor.fetchall()

            summary = {
                "operation_count": 0,
                "buy_count": 0,
                "buy_shares": _to_number(ZERO, 4),
                "buy_amount": _to_number(ZERO, 2),
                "sell_count": 0,
                "sell_shares": _to_number(ZERO, 4),
                "sell_amount": _to_number(ZERO, 2),
                "dividend_cash_count": 0,
                "dividend_cash_amount": _to_number(ZERO, 2)
            }

            for row in summary_rows:
                operation_type = row["operation_type"]
                summary["operation_count"] += row["operation_count"]

                if operation_type == "buy":
                    summary["buy_count"] = row["operation_count"]
                    summary["buy_shares"] = _to_number(row["total_shares"], 4)
                    summary["buy_amount"] = _to_number(row["total_amount"], 2)

                if operation_type == "sell":
                    summary["sell_count"] = row["operation_count"]
                    summary["sell_shares"] = _to_number(row["total_shares"], 4)
                    summary["sell_amount"] = _to_number(row["total_amount"], 2)

                if operation_type == "dividend_cash":
                    summary["dividend_cash_count"] = row["operation_count"]
                    summary["dividend_cash_amount"] = _to_number(row["total_amount"], 2)

            cursor.execute(
                """
                SELECT
                    o.id,
                    o.blogger_id,
                    b.name AS blogger_name,
                    o.fund_id,
                    f.name AS fund_name,
                    f.fund_code,
                    o.operation_type,
                    o.operation_date,
                    o.shares,
                    o.amount
                FROM operations AS o
                JOIN bloggers AS b ON b.id = o.blogger_id
                JOIN funds AS f ON f.id = o.fund_id
                WHERE o.operation_date >= %s
                  AND o.operation_date <= %s
                ORDER BY o.operation_date DESC, o.id DESC
                LIMIT %s
                """,
                (start_date, end_date, limit)
            )
            operation_rows = cursor.fetchall()
            operation_items = [
                _serialize_operation_item(row)
                for row in operation_rows
            ]
    finally:
        conn.close()

    return success(
        data={
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "limit": limit,
            "summary": summary,
            "items": operation_items
        }
    )
```

说明：

- `summary` 统计整个日期范围。
- `items` 只返回最近 `limit` 条记录。
- `ORDER BY ... DESC` 表示倒序，最新日期和更大 ID 排在前面。
- `summary` 的初始值用 `_to_number(ZERO, ...)` 而不是整数 `0`。这样范围内没有买入记录时，`buy_shares` 返回 `0.0` 而不是 `0`，和有数据时的 `1000.0` 是同一种类型，也和 `docs/api/v1-dashboards.md` 的空数据示例一致。前端不用为「有数据」和「没数据」写两套类型判断。

---

### 步骤 4：语法检查

**必要性：**  
先确认修改后的路由文件没有语法错误，再启动服务。

执行：

```bash
python -m py_compile app/routes/dashboards.py
```

预期没有输出，并且退出码是 `0`。

---

### 步骤 5：启动服务并手动验证

**必要性：**  
统计接口涉及 SQL 聚合，必须实际请求一次，确认汇总值和记录列表正确。

启动服务：

```bash
python run.py
```

另开一个终端，在 `backend` 目录执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/recent-operations?start_date=2026-09-24&end_date=2026-09-30&limit=20"
```

预期返回 HTTP `200`，响应结构符合 `docs/api/v1-dashboards.md`。

---

### 步骤 6：运行已有测试

**必要性：**  
确认新统计接口没有破坏已有功能。

停止服务后，在 `backend` 目录执行：

```bash
pytest -q
```

预期全部通过。

## 验证方式

### 1. 语法检查

```bash
python -m py_compile app/routes/dashboards.py
```

预期没有输出。

### 2. 默认最近 7 天

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/recent-operations"
```

预期 HTTP `200`，`end_date` 是今天，`start_date` 是 `end_date - 6`。

### 3. 指定日期范围

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/recent-operations?start_date=2026-09-24&end_date=2026-09-30&limit=20"
```

预期 HTTP `200`。

### 4. 空数据场景

使用一个没有操作记录的日期范围：

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/recent-operations?start_date=2026-01-01&end_date=2026-01-07"
```

预期 HTTP `200`，`items` 是 `[]`，`summary` 的所有字段都在，其中：

- `operation_count`、`buy_count`、`sell_count`、`dividend_cash_count` 是 `0`。
- `buy_shares`、`sell_shares` 带 4 位小数，`buy_amount`、`sell_amount`、`dividend_cash_amount` 带 2 位小数，不是裸的整数 `0`。

### 5. 错误场景

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/recent-operations?start_date=bad-date&end_date=2026-09-30"
curl -i "http://127.0.0.1:5000/api/v1/dashboards/recent-operations?start_date=2026-09-30&end_date=2999-12-31"
curl -i "http://127.0.0.1:5000/api/v1/dashboards/recent-operations?start_date=2026-09-30&end_date=2026-09-01"
curl -i "http://127.0.0.1:5000/api/v1/dashboards/recent-operations?limit=0"
curl -i "http://127.0.0.1:5000/api/v1/dashboards/recent-operations?limit=101"
```

预期都返回 HTTP `400 VALIDATION_ERROR`。

### 6. 已有测试

```bash
pytest -q
```

预期全部通过。

## 常见坑

### 1. `summary` 只统计了返回的 items

`summary` 必须统计整个日期范围。  
`items` 只是被 `limit` 截断的最近记录，两者数量可能不同。

### 2. 忘记日期范围包含两端

`operation_date >= start_date AND operation_date <= end_date` 表示包含开始和结束日期。  
只写 `BETWEEN` 也是包含两端，但必须保证开始日期不晚于结束日期。

### 3. 开始日期晚于结束日期

如果不校验日期范围，SQL 可能总是返回空数据，新手很难发现问题。  
必须在进入数据库查询前返回 `400`。

### 4. `SUM()` 结果是 `None`

范围内没有数据时，`SUM()` 可能返回 `NULL`。  
必须使用 `COALESCE(SUM(amount), 0)` 或在 Python 里兜底，不能直接返回 `None` 给金额汇总。

### 5. 空范围时 `summary` 返回整数 0

`summary` 的初始值要用 `_to_number(ZERO, 4)` / `_to_number(ZERO, 2)`，不要写成整数 `0`。

写成 `0` 的话，同一个字段在有数据时是 `1000.0`、没数据时是 `0`，JSON 里一个带小数点一个不带。接口文档的空数据示例写的是 `0.0000`，前端按文档写了格式化逻辑就会对不上。

### 6. 把 `limit` 上限写死成 100

用任务 023 的 `MAX_PAGE_SIZE`，不要在这个文件里再写一个 `100`。  
两处各写一个数字，以后调整上限必然漏改一处。

## 完成标准

以下条件全部满足，任务 039 才算完成：

1. `GET /api/v1/dashboards/recent-operations` 可访问。
2. 默认统计最近 7 天。
3. `summary` 和 `items` 的字段与接口文档一致。
4. 空范围时返回 `200`，`summary` 的所有字段都存在，`*_count` 是 `0`，`*_shares` 和 `*_amount` 带小数位。
5. 日期和 `limit` 错误时返回 `400 VALIDATION_ERROR`。
6. `limit` 上限来自 `MAX_PAGE_SIZE`，没有再写死 `100`。
7. `pytest -q` 全部通过。

## 完成后请反馈

1. 修改的文件列表。
2. 语法检查输出。
3. 成功请求的完整响应 JSON。
4. 空数据和错误场景的响应 JSON。
5. `pytest -q` 的完整输出。
6. 遇到的问题和未完成项。
