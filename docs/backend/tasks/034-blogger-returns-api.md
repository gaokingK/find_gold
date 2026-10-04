# 任务 034：单博主累计收益率接口

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务要新建一个收益查询路由，串联持仓快照、精确净值、收益计算和 JSON 序列化。业务计算已经在任务 033 完成，所以主要是路由和响应字段处理，不涉及新表和新依赖。

## 任务目标

创建：

```text
backend/app/routes/returns.py
```

修改：

```text
backend/app/__init__.py
```

完成后可以：

1. 访问 `GET /api/v1/bloggers/{blogger_id}/returns`。
2. 按可选参数 `return_date` 计算收益，不传时默认今天。
3. 返回博主总成本、总市值、总收益金额、总收益率。
4. 返回按基金拆分的收益明细。
5. 博主不存在时返回 `404 BLOGGER_NOT_FOUND`。
6. 日期格式错误或未来日期返回 `400 VALIDATION_ERROR`。
7. `pytest -q` 仍然全部通过。

## 范围说明

本任务只实现单博主收益查询接口。

不包含：

- 单基金收益接口
- 总体收益汇总接口
- 收益结果持久化
- 最近一天净值兜底
- 最大回撤、年化收益、夏普比率
- 登录和权限

## 前置条件

1. 任务 033 已完成，`calculate_position_returns()`、`calculate_total_returns()`、`get_nav_on_date_map()` 可用。
2. 任务 031、032 已完成，持仓快照计算和测试可用。
3. `pytest -q` 当前全部通过。
4. 已阅读 `docs/api/v1-returns.md` 中「查询单博主累计收益」部分。

## 新概念说明

### Route（路由）

Route 是 URL 和 Python 函数的对应关系。  
本任务把 `/api/v1/bloggers/{blogger_id}/returns` 映射到一个查询函数。

### Serialization（序列化）

Serialization 是把 Python 里的 `Decimal`、`date` 等对象转换成前端能处理的 JSON 数据。  
数据库里的金额通常是 `Decimal`，日期通常是 `date`，不能直接原样返回给 JSON。

## 执行目录

```bash
cd /d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建收益路由文件

**必要性：**  
收益是新业务模块，单独建路由文件，避免持仓快照和收益逻辑混在一个文件里。

新建文件：

```text
backend/app/routes/returns.py
```

先写入基础结构：

```python
from datetime import date

from flask import Blueprint, request

from app.db import get_connection
from app.services.position_snapshot import calculate_position_snapshots
from app.services.return_calculation import (
    calculate_position_returns,
    calculate_total_returns,
)
from app.utils.responses import error, success
from app.utils.snapshot_data import (
    get_initial_positions,
    get_nav_on_date_map,
    get_operations,
    parse_snapshot_date,
)


returns_bp = Blueprint("returns", __name__)


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

- `Blueprint（蓝图）` 用来把一组路由组织成独立模块，最后仍要在应用工厂里注册。
- `parse_positive_int()` 校验路径参数里的博主 ID。
- `_to_number()` 把 `Decimal` 转成 JSON 友好的数字，并控制小数位。

---

### 步骤 2：添加收益明细序列化函数

**必要性：**  
Service 返回的收益数据里有 `Decimal` 和 `date`，直接放进 Flask 响应会报错，必须先转换。

继续添加：

```python
def _serialize_return_item(item):
    nav_date = item.get("nav_date")

    return {
        "fund_id": item["fund_id"],
        "fund_name": item["fund_name"],
        "fund_code": item["fund_code"],
        "shares": _to_number(item["shares"], 4),
        "cost_amount": _to_number(item["cost_amount"], 2),
        "nav": _to_number(item["nav"], 4),
        "nav_date": (
            nav_date.strftime("%Y-%m-%d")
            if nav_date is not None
            else None
        ),
        "market_value": _to_number(item["market_value"], 2),
        "profit_amount": _to_number(item["profit_amount"], 2),
        "return_rate": _to_number(item["return_rate"], 6),
    }
```

说明：

- `dict.get()` 用于读取字典中的字段；字段不存在时返回 `None`，不会抛 `KeyError`。
- 份额保留 4 位小数，金额保留 2 位小数，收益率保留 6 位小数。

---

### 步骤 3：实现单博主收益查询路由

**必要性：**  
这一步把「读取数据 → 计算快照 → 查当天净值 → 计算收益 → 返回 JSON」串成完整接口。

继续添加：

```python
@returns_bp.get("/api/v1/bloggers/<blogger_id>/returns")
def get_blogger_returns(blogger_id):
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

    return_date = parse_snapshot_date(request.args.get("return_date"))

    if return_date is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "return_date",
                    "message": "收益日期格式必须是 YYYY-MM-DD"
                }
            ],
            http_status=400
        )

    if return_date > date.today():
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "return_date",
                    "message": "收益日期不能晚于今天"
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
                return_date
            )
            operations = get_operations(
                cursor,
                parsed_blogger_id,
                return_date
            )
            position_items = calculate_position_snapshots(
                initial_positions,
                operations
            )
            fund_ids = [item["fund_id"] for item in position_items]
            nav_map = get_nav_on_date_map(
                cursor,
                fund_ids,
                return_date
            )
            return_items = calculate_position_returns(
                position_items,
                nav_map
            )
            summary = calculate_total_returns(return_items)
            serialized_items = [
                _serialize_return_item(item)
                for item in return_items
            ]
    finally:
        conn.close()

    return success(
        data={
            "blogger_id": parsed_blogger_id,
            "blogger_name": blogger["name"],
            "return_date": return_date.strftime("%Y-%m-%d"),
            "total_cost_amount": _to_number(
                summary["total_cost_amount"],
                2
            ),
            "total_market_value": _to_number(
                summary["total_market_value"],
                2
            ),
            "profit_amount": _to_number(
                summary["profit_amount"],
                2
            ),
            "return_rate": _to_number(
                summary["return_rate"],
                6
            ),
            "items": serialized_items
        }
    )
```

说明：

- `parse_snapshot_date()` 虽然名字里带 snapshot，但它本质上是一个「解析 YYYY-MM-DD 字符串」的工具，这里复用它解析收益日期。
- `get_nav_on_date_map()` 只查指定日期当天的净值，不做最近日期兜底。
- 如果博主没有持仓和操作，接口正常返回空明细和零值汇总。

---

### 步骤 4：注册收益 Blueprint

**必要性：**  
Flask 只有注册 Blueprint 后，才能访问新路由。

修改文件：

```text
backend/app/__init__.py
```

增加导入：

```python
from app.routes.returns import returns_bp
```

在 `create_app()` 中注册：

```python
app.register_blueprint(returns_bp)
```

---

### 步骤 5：语法检查

**必要性：**  
先确认新文件没有语法错误，再启动服务和联调。

执行：

```bash
python -m py_compile app/routes/returns.py
python -m py_compile app/__init__.py
```

预期没有输出，并且退出码是 `0`。

---

### 步骤 6：启动服务并手动验证

**必要性：**  
语法通过不代表路由注册和数据库查询正确，必须请求一次接口。

启动服务：

```bash
python run.py
```

另开一个终端，在 `backend` 目录执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/returns?return_date=2026-09-30"
```

如果数据库里没有 ID 为 `1` 的博主，可以换成实际存在的博主 ID。

预期返回 HTTP `200`，响应结构符合 `docs/api/v1-returns.md`。

---

### 步骤 7：运行已有测试

**必要性：**  
确认新路由没有破坏已有模块。

停止服务后，在 `backend` 目录执行：

```bash
pytest -q
```

预期全部通过。

## 验证方式

### 1. 语法检查

```bash
python -m py_compile app/routes/returns.py
python -m py_compile app/__init__.py
```

预期没有输出。

### 2. 成功请求

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/returns?return_date=2026-09-30"
```

预期 HTTP `200`，字段与接口文档一致。

### 3. 缺净值场景

使用一个当天没有净值的博主或基金请求：

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/returns?return_date=2026-09-29"
```

预期相关基金和汇总里的市值、收益金额、收益率是 `null`。

### 4. 错误场景

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/abc/returns"
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/returns?return_date=bad-date"
curl -i "http://127.0.0.1:5000/api/v1/bloggers/999999/returns"
```

预期分别是 HTTP `400`、HTTP `400`、HTTP `404`。

### 5. 已有测试

```bash
pytest -q
```

预期全部通过。

## 常见坑

### 1. 使用最近一天净值兜底

本模块的口径是「指定日期当天必须有净值」。  
不要使用 `get_latest_nav_map()`，必须使用 `get_nav_on_date_map()`。

### 2. 直接返回 Decimal 或 date

`Decimal` 和 `date` 不能直接放进 Flask JSON 响应。  
必须使用序列化函数转换。

### 3. 成本为 0 时自己再除一次

收益率已经在 `calculate_return_metrics()` 里处理了。  
路由里不要重复写 `(市值 - 成本) / 成本`。

### 4. 忘记注册 Blueprint

只在 `returns.py` 里定义 `returns_bp` 还不够。  
必须在 `app/__init__.py` 中注册，否则访问会返回 `404`。

## 完成标准

以下条件全部满足，任务 034 才算完成：

1. `GET /api/v1/bloggers/{blogger_id}/returns` 可访问。
2. `return_date` 可选，默认今天。
3. 响应字段和 `docs/api/v1-returns.md` 一致。
4. 缺净值时相关字段返回 `null`。
5. 博主不存在、日期非法、未来日期的错误响应正确。
6. `pytest -q` 全部通过。

## 完成后请反馈

1. 新增和修改的文件列表。
2. 语法检查输出。
3. 成功请求的完整响应 JSON。
4. 缺净值和错误场景的响应 JSON。
5. `pytest -q` 的完整输出。
6. 遇到的问题和未完成项。
