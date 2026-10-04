# 任务 026：实现净值手动录入接口

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务需要新建净值模块、实现 POST 接口、校验日期和净值、处理同一基金同一天重复提交的更新逻辑，并注册新的 Blueprint（蓝图）。

## 任务目标

实现：

```http
POST /api/v1/nav-history
```

使用者可以录入某只基金某一天的净值。

本接口的重复提交行为是：

```text
同一 fund_id + nav_date 已有净值时，更新旧值。
```

这样用户录错后可以重新提交同一天净值来修正。

## 范围说明

本任务只实现净值手动录入。

不包含：

- 净值查询接口
- CSV 解析
- CSV 导入接口
- 净值删除接口
- 净值编辑接口
- 自动净值同步
- 分红净值、累计净值、复权净值

## 前置条件

1. 任务 024 已完成，净值表设计已确认。
2. 任务 025 已完成，`nav_history` 表和唯一索引已创建。
3. 数据库里至少存在一个基金。
4. `pytest -q` 全部通过。

## 新概念：Decimal

`Decimal` 是 Python 提供的十进制类型，适合处理金额、净值这类需要精确小数的数据。

浮点数 `float` 有精度问题，例如：

```python
0.1 + 0.2
```

结果不是精确的 `0.3`。  
净值涉及后续市值和收益计算，所以本任务开始用 `Decimal` 处理净值。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建净值路由文件

**必要性：**  
净值是一个新的业务模块，单独放一个文件可以避免路由文件混在一起。

新建文件：

```text
backend/app/routes/nav_history.py
```

先写入基础结构：

```python
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request

from app.db import get_connection
from app.utils.responses import error, success


nav_history_bp = Blueprint("nav_history", __name__)


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


def parse_decimal(value):
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        value = str(value)

    if not isinstance(value, str) or value.strip() == "":
        return None

    try:
        result = Decimal(value.strip())
    except InvalidOperation:
        return None

    if not result.is_finite():
        return None

    return result


def parse_nav_payload():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None, error(
            code="VALIDATION_ERROR",
            message="请求体必须是 JSON 对象",
            details=[],
            http_status=400
        )

    fund_id = parse_positive_int(data.get("fund_id"))
    raw_nav_date = data.get("nav_date")
    nav = parse_decimal(data.get("nav"))
    details = []

    if fund_id is None:
        details.append(
            {
                "field": "fund_id",
                "message": "基金 ID 必须为正整数"
            }
        )

    parsed_nav_date = None

    if not isinstance(raw_nav_date, str):
        details.append(
            {
                "field": "nav_date",
                "message": "净值日期不能为空"
            }
        )
    else:
        try:
            parsed_nav_date = datetime.strptime(
                raw_nav_date,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            details.append(
                {
                    "field": "nav_date",
                    "message": "净值日期格式必须是 YYYY-MM-DD"
                }
            )

    if parsed_nav_date is not None and parsed_nav_date > date.today():
        details.append(
            {
                "field": "nav_date",
                "message": "净值日期不能晚于今天"
            }
        )

    if nav is None:
        details.append(
            {
                "field": "nav",
                "message": "净值必须是数字"
            }
        )
    elif nav <= 0:
        details.append(
            {
                "field": "nav",
                "message": "净值必须大于 0"
            }
        )

    if details:
        return None, error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=details,
            http_status=400
        )

    return {
        "fund_id": fund_id,
        "nav_date": parsed_nav_date,
        "nav": nav
    }, None
```

---

### 步骤 2：新增序列化函数

**必要性：**  
数据库里的 `DATE` 和 `DECIMAL` 不能直接给 JSON，需要转换成前端能处理的结构。

在 `nav_history.py` 中继续添加：

```python
def serialize_nav_history(row):
    nav_date = row["nav_date"]
    created_at = row["created_at"]
    updated_at = row["updated_at"]

    return {
        "nav_id": row["id"],
        "fund_id": row["fund_id"],
        "fund_name": row["fund_name"],
        "fund_code": row["fund_code"],
        "nav_date": nav_date.strftime("%Y-%m-%d"),
        "nav": float(row["nav"]),
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": updated_at.strftime("%Y-%m-%d %H:%M:%S"),
    }
```

---

### 步骤 3：新增数据库辅助函数

**必要性：**  
新增净值前必须确认基金存在；重复提交时需要找到已有记录；返回结果时需要重新查询完整数据。

在 `nav_history.py` 中继续添加：

```python
def check_fund_exists(cursor, fund_id):
    cursor.execute(
        "SELECT id FROM funds WHERE id = %s",
        (fund_id,)
    )
    return cursor.fetchone() is not None


def find_nav_history_id(cursor, fund_id, nav_date):
    cursor.execute(
        """
        SELECT id
        FROM nav_history
        WHERE fund_id = %s
          AND nav_date = %s
        """,
        (fund_id, nav_date)
    )
    row = cursor.fetchone()

    if row is None:
        return None

    return row["id"]


def fetch_nav_history_by_id(cursor, nav_history_id):
    cursor.execute(
        """
        SELECT
            n.id,
            n.fund_id,
            f.name AS fund_name,
            f.fund_code,
            n.nav_date,
            n.nav,
            n.created_at,
            n.updated_at
        FROM nav_history n
        JOIN funds f ON f.id = n.fund_id
        WHERE n.id = %s
        """,
        (nav_history_id,)
    )
    row = cursor.fetchone()

    if row is None:
        return None

    return serialize_nav_history(row)
```

---

### 步骤 4：实现 POST 路由

**必要性：**  
这是本任务的核心接口。它要处理两种情况：第一次录入，或者同一天重复提交时更新旧值。

在 `nav_history.py` 末尾添加：

```python
@nav_history_bp.post("/api/v1/nav-history")
def upsert_nav_history():
    payload, error_response = parse_nav_payload()

    if error_response is not None:
        return error_response

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            if not check_fund_exists(cursor, payload["fund_id"]):
                return error(
                    code="FUND_NOT_FOUND",
                    message="基金不存在",
                    details=[],
                    http_status=404
                )

            existing_id = find_nav_history_id(
                cursor,
                payload["fund_id"],
                payload["nav_date"]
            )

            if existing_id is None:
                cursor.execute(
                    """
                    INSERT INTO nav_history (
                        fund_id,
                        nav_date,
                        nav
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        payload["fund_id"],
                        payload["nav_date"],
                        payload["nav"]
                    )
                )
                nav_history_id = cursor.lastrowid
            else:
                cursor.execute(
                    """
                    UPDATE nav_history
                    SET nav = %s
                    WHERE id = %s
                    """,
                    (
                        payload["nav"],
                        existing_id
                    )
                )
                nav_history_id = existing_id

            conn.commit()
            data = fetch_nav_history_by_id(cursor, nav_history_id)
    finally:
        conn.close()

    return success(data=data)
```

---

### 步骤 5：注册净值 Blueprint

**必要性：**  
不注册 Blueprint，接口就无法访问。

修改文件：

```text
backend/app/__init__.py
```

增加导入：

```python
from app.routes.nav_history import nav_history_bp
```

在 `create_app()` 中注册：

```python
app.register_blueprint(nav_history_bp)
```

---

### 步骤 6：重启 Flask 服务

**必要性：**  
新增文件和注册路由后必须重启，确认没有语法错误。

```bash
python run.py
```

## 验证方式

### 1. 新增一条净值

假设基金 ID 是 `1`：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/nav-history" \
  -H "Content-Type: application/json" \
  -d '{"fund_id":1,"nav_date":"2026-09-30","nav":1.2345}'
```

预期返回 `code: 0`，并包含 `fund_name`、`fund_code`、`nav_date`、`nav`。

### 2. 同一天重复提交

再执行一次：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/nav-history" \
  -H "Content-Type: application/json" \
  -d '{"fund_id":1,"nav_date":"2026-09-30","nav":1.3000}'
```

预期：

1. 返回 `code: 0`。
2. `nav` 变成 `1.3`。
3. 不是新增第二条记录。

### 3. 验证另一只基金同一天

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/nav-history" \
  -H "Content-Type: application/json" \
  -d '{"fund_id":2,"nav_date":"2026-09-30","nav":2.0000}'
```

预期可以新增，因为 `fund_id` 不同。

### 4. 验证非法日期

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/nav-history" \
  -H "Content-Type: application/json" \
  -d '{"fund_id":1,"nav_date":"2026/09/30","nav":1.2345}'
```

预期返回 `VALIDATION_ERROR`。

### 5. 验证未来日期

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/nav-history" \
  -H "Content-Type: application/json" \
  -d '{"fund_id":1,"nav_date":"2999-12-31","nav":1.2345}'
```

预期返回 `VALIDATION_ERROR`。

### 6. 验证非法净值

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/nav-history" \
  -H "Content-Type: application/json" \
  -d '{"fund_id":1,"nav_date":"2026-09-30","nav":0}'
```

预期返回 `VALIDATION_ERROR`。

### 7. 验证基金不存在

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/nav-history" \
  -H "Content-Type: application/json" \
  -d '{"fund_id":999999,"nav_date":"2026-09-30","nav":1.2345}'
```

预期返回 `FUND_NOT_FOUND`，HTTP 状态码是 `404`。

## 常见坑

### 1. 忘记注册 Blueprint

如果访问 `/api/v1/nav-history` 返回 HTML `404`，通常是 `nav_history_bp` 没有注册。

检查命令：

```bash
grep -n "nav_history_bp" app/__init__.py
```

### 2. 用 float 处理净值

不要在计算或累加时用 `float`。  
本任务解析输入时使用 `Decimal`，返回 JSON 时才转成 `float`。

### 3. 允许重复插入

不要把同一 `fund_id + nav_date` 当成新记录插入。  
必须先查一次，如果存在就更新。

### 4. 允许净值等于 0

净值必须大于 0。  
如果允许 0，后续收益率计算会出现奇怪的除零或负数问题。

### 5. 允许未来日期

净值是历史数据。  
未来日期会干扰持仓快照和收益计算。

### 6. 忘记 `conn.commit()`

没有提交的话，数据库里的净值可能没有真正保存。

## 完成标准

以下条件全部满足，任务 026 才算完成：

1. `backend/app/routes/nav_history.py` 已创建。
2. `nav_history_bp` 已注册。
3. `POST /api/v1/nav-history` 可以新增净值。
4. 同一 `fund_id + nav_date` 重复提交时更新旧值。
5. 净值必须大于 0。
6. 净值日期不能晚于今天。
7. 基金不存在时返回 `404`。
8. 所有响应都是统一 JSON 结构。
9. `pytest -q` 全部通过。

## 完成后请反馈

1. 新增和修改的文件列表。
2. 新增净值和重复提交的验证结果。
3. 非法日期、非法净值、基金不存在的验证结果。
4. `pytest -q` 的完整输出。
5. 遇到的问题和未完成项。
