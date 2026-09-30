# 任务 031：博主持仓快照接口

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务要把任务 029 的数据读取和任务 030 的计算逻辑接到 Flask 路由上，同时处理路径参数、日期参数、博主校验和响应序列化。逻辑不复杂，但字段较多，需要细心。

## 任务目标

实现：

```http
GET /api/v1/bloggers/{blogger_id}/position-snapshots
```

完成后可以：

1. 按博主查询持仓快照。
2. 支持可选参数 `snapshot_date`。
3. 不传 `snapshot_date` 时默认查今天。
4. 返回博主信息和按基金分组的快照结果。
5. `pytest -q` 仍然全部通过。

## 范围说明

本任务只实现查询接口。

不包含：

- 市值计算
- 收益率计算
- 持仓快照持久化
- 超额卖出校验
- 分页
- 导出

## 前置条件

1. 任务 029 已完成，数据读取工具可用。
2. 任务 030 已完成，快照计算函数可用。
3. `pytest -q` 当前全部通过。

## 新概念：路径参数与查询参数组合

路径参数用来定位资源，例如某个博主：  
`/api/v1/bloggers/12/position-snapshots`

查询参数用来补充查询条件，例如快照日期：  
`?snapshot_date=2026-09-30`

本接口同时使用两者。

## 执行目录

```bash
cd /d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建路由文件

**必要性：**  
持仓快照是新的业务模块，单独建一个路由文件，避免 `operations.py` 越来越大。

新建文件：

```text
backend/app/routes/position_snapshots.py
```

先写入基础结构：

```python
from datetime import date

from flask import Blueprint, request

from app.db import get_connection
from app.services.position_snapshot import calculate_position_snapshots
from app.utils.responses import error, success
from app.utils.snapshot_data import (
    get_initial_positions,
    get_operations,
    parse_snapshot_date,
)


position_snapshots_bp = Blueprint("position_snapshots", __name__)


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


def _to_number(value, places):
    if value is None:
        return None

    return round(float(value), places)
```

说明：

- `parse_positive_int()` 用来校验路径里的博主 ID。
- `_to_number()` 把 `Decimal` 转成 JSON 友好的数字。份额保留 4 位小数，金额保留 2 位小数。

---

### 步骤 2：添加序列化函数

**必要性：**  
数据库和 Service 层里的日期、金额、份额不能直接给前端。需要统一转换。

继续添加：

```python
def _serialize_position_snapshot_item(item):
    initial_record_date = item["initial_record_date"]

    return {
        "fund_id": item["fund_id"],
        "fund_name": item["fund_name"],
        "fund_code": item["fund_code"],
        "initial_record_date": (
            initial_record_date.strftime("%Y-%m-%d")
            if initial_record_date is not None
            else None
        ),
        "initial_shares": _to_number(item["initial_shares"], 4),
        "initial_cost_amount": _to_number(item["initial_cost_amount"], 2),
        "buy_shares": _to_number(item["buy_shares"], 4),
        "buy_amount": _to_number(item["buy_amount"], 2),
        "sell_shares": _to_number(item["sell_shares"], 4),
        "sell_amount": _to_number(item["sell_amount"], 2),
        "dividend_cash_amount": _to_number(item["dividend_cash_amount"], 2),
        "shares": _to_number(item["shares"], 4),
        "cost_amount": _to_number(item["cost_amount"], 2),
    }
```

---

### 步骤 3：实现查询路由

**必要性：**  
这一步把数据读取、业务计算和 HTTP 响应连起来。

继续添加：

```python
@position_snapshots_bp.get("/api/v1/bloggers/<blogger_id>/position-snapshots")
def get_position_snapshots(blogger_id):
    parsed_blogger_id = parse_positive_int(blogger_id)

    if parsed_blogger_id is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "blogger_id",
                    "message": "博主 ID 必须为正整数"
                }
            ],
            http_status=400
        )

    snapshot_date = parse_snapshot_date(request.args.get("snapshot_date"))

    if snapshot_date is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "snapshot_date",
                    "message": "快照日期格式必须是 YYYY-MM-DD"
                }
            ],
            http_status=400
        )

    if snapshot_date > date.today():
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "snapshot_date",
                    "message": "快照日期不能晚于今天"
                }
            ],
            http_status=400
        )

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name FROM bloggers WHERE id = %s",
                (parsed_blogger_id,)
            )
            blogger = cursor.fetchone()

            if blogger is None:
                return error(
                    code="BLOGGER_NOT_FOUND",
                    message="博主不存在",
                    details=[],
                    http_status=404
                )

            initial_positions = get_initial_positions(
                cursor,
                parsed_blogger_id,
                snapshot_date
            )
            operations = get_operations(
                cursor,
                parsed_blogger_id,
                snapshot_date
            )
            items = calculate_position_snapshots(
                initial_positions,
                operations
            )
            serialized_items = [
                _serialize_position_snapshot_item(item)
                for item in items
            ]
    finally:
        conn.close()

    return success(
        data={
            "blogger_id": parsed_blogger_id,
            "blogger_name": blogger["name"],
            "snapshot_date": snapshot_date.strftime("%Y-%m-%d"),
            "items": serialized_items
        }
    )
```

说明：

- 如果博主存在但没有持仓和操作，接口返回 `items: []`，这是正常情况。
- `snapshot_date` 不传时默认今天，这是任务 029 里定义好的行为。
- 不要在这里计算市值或收益率，这是第 8 天的任务。

---

### 步骤 4：注册 Blueprint

**必要性：**  
Flask 只有注册 Blueprint 后，才能访问新路由。

修改文件：

```text
backend/app/__init__.py
```

增加导入：

```python
from app.routes.position_snapshots import position_snapshots_bp
```

在 `create_app()` 中注册：

```python
app.register_blueprint(position_snapshots_bp)
```

---

### 步骤 5：重启服务

**必要性：**  
新增路由后必须重启 Flask，才能确认路由注册成功。

```bash
python run.py
```

---

### 步骤 6：运行已有测试

**必要性：**  
确认新路由没有破坏已有功能。

```bash
pytest -q
```

预期全部通过。第 32 个任务会补快照接口的专项测试。

## 验证方式

### 1. 不传快照日期

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/position-snapshots"
```

预期 HTTP `200`，返回今天日期。

### 2. 传入快照日期

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/position-snapshots?snapshot_date=2026-09-30"
```

预期 HTTP `200`。

### 3. 博主不存在

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/999999/position-snapshots"
```

预期 HTTP `404`，错误码 `BLOGGER_NOT_FOUND`。

### 4. 日期格式错误

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/position-snapshots?snapshot_date=bad-date"
```

预期 HTTP `400`，错误码 `VALIDATION_ERROR`。

## 常见坑

### 1. 把路径参数直接当整数用

路径参数默认是字符串。  
必须先校验并转换。

### 2. 忘记关闭数据库连接

数据库连接要在 `finally` 里关闭。  
否则异常时连接可能不会被释放。

### 3. 在这里顺手算市值

本任务只做持仓快照。  
市值和收益率是第 8 天的任务。

## 完成标准

以下条件全部满足，任务 031 才算完成：

1. `GET /api/v1/bloggers/{blogger_id}/position-snapshots` 可访问。
2. `snapshot_date` 可选，默认今天。
3. 博主不存在时返回 `404`。
4. 日期格式错误或未来日期返回 `400`。
5. `pytest -q` 全部通过。

## 完成后请反馈

1. 新增和修改的文件列表。
2. 成功请求的响应 JSON。
3. 博主不存在和日期错误的响应 JSON。
4. `pytest -q` 的完整输出。
5. 遇到的问题和未完成项。
