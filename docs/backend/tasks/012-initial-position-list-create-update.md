# 任务 012：实现初始持仓列表、新增、编辑接口

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务需要新建一个多表关联模块，实现 3 个接口；新增和编辑都要校验博主、基金、金额和日期，还要处理唯一索引冲突，工作量比单表接口略大。

## 任务目标

实现：

```http
GET /api/v1/initial-positions
POST /api/v1/initial-positions
PUT /api/v1/initial-positions/{initial_position_id}
```

完成后可以：

1. 分页查询初始持仓。
2. 按博主 ID 或基金 ID 筛选初始持仓。
3. 新增初始持仓。
4. 编辑初始持仓。
5. 返回博主名称、基金名称、基金代码等关联字段。
6. 同一博主、同一基金、同一记录日期不允许重复。

## 范围说明

本任务只处理初始持仓列表、新增和编辑。

不包含：

- 删除初始持仓
- 当前净值、市值、收益、占比计算
- 历史净值同步
- 定时任务
- service 层
- repository 层

## 前置条件

1. 任务 007 已完成，`initial_positions` 表已创建。
2. 任务 010 已完成，博主模块可用。
3. 任务 011 已完成，基金模块可用。
4. 数据库里至少存在一个博主和一个基金。

## 新概念：JOIN 查询与唯一索引兜底

### JOIN 查询

JOIN 查询用于从多张表中按关联字段读取数据。

初始持仓表只保存 `blogger_id` 和 `fund_id`，不保存博主名称、基金名称和基金代码。查询时需要通过 JOIN 从 `bloggers` 和 `funds` 表读取最新名称。

示例：

```sql
SELECT ip.id, b.name AS blogger_name, f.name AS fund_name
FROM initial_positions ip
JOIN bloggers b ON b.id = ip.blogger_id
JOIN funds f ON f.id = ip.fund_id
```

### 唯一索引兜底

唯一索引是数据库层面防止重复数据的机制。  
代码里可以先做重复校验，但并发请求时仍可能出现重复。数据库的唯一索引可以兜底拒绝重复数据。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建初始持仓路由文件

**必要性：**  
初始持仓依赖博主和基金，但它是一个独立业务模块，应放在单独文件中维护。

新建文件：

```text
backend/app/routes/initial_positions.py
```

内容：

```python
from datetime import datetime

from flask import Blueprint, request

from app.db import get_connection
from app.utils.responses import error, success


initial_positions_bp = Blueprint("initial_positions", __name__)


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


def parse_non_negative_number(value):
    if isinstance(value, bool):
        return None

    if not isinstance(value, (int, float)):
        return None

    if value < 0:
        return None

    return float(value)


def serialize_initial_position(row):
    record_date = row["record_date"]

    return {
        "initial_position_id": row["id"],
        "blogger_id": row["blogger_id"],
        "blogger_name": row["blogger_name"],
        "fund_id": row["fund_id"],
        "fund_name": row["fund_name"],
        "fund_code": row["fund_code"],
        "shares": float(row["shares"]),
        "cost_amount": float(row["cost_amount"]),
        "record_date": record_date.strftime("%Y-%m-%d"),
    }


def fetch_initial_position(cursor, initial_position_id):
    cursor.execute(
        """
        SELECT
            ip.id,
            ip.blogger_id,
            b.name AS blogger_name,
            ip.fund_id,
            f.name AS fund_name,
            f.fund_code,
            ip.shares,
            ip.cost_amount,
            ip.record_date
        FROM initial_positions ip
        JOIN bloggers b ON b.id = ip.blogger_id
        JOIN funds f ON f.id = ip.fund_id
        WHERE ip.id = %s
        """,
        (initial_position_id,)
    )
    row = cursor.fetchone()

    if row is None:
        return None

    return serialize_initial_position(row)


def parse_list_params():
    details = []
    blogger_id = None
    fund_id = None

    raw_blogger_id = request.args.get("blogger_id")
    raw_fund_id = request.args.get("fund_id")

    if raw_blogger_id not in (None, ""):
        blogger_id = parse_positive_int(raw_blogger_id)

        if blogger_id is None:
            details.append(
                {
                    "field": "blogger_id",
                    "message": "博主 ID 必须为正整数"
                }
            )

    if raw_fund_id not in (None, ""):
        fund_id = parse_positive_int(raw_fund_id)

        if fund_id is None:
            details.append(
                {
                    "field": "fund_id",
                    "message": "基金 ID 必须为正整数"
                }
            )

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
    except (TypeError, ValueError):
        details.append(
            {
                "field": "page",
                "message": "page 和 page_size 必须是整数"
            }
        )
        page = 0
        page_size = 0

    if page <= 0:
        details.append({"field": "page", "message": "page 必须大于 0"})

    if page_size <= 0 or page_size > 100:
        details.append(
            {
                "field": "page_size",
                "message": "page_size 必须在 1 到 100 之间"
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
        "blogger_id": blogger_id,
        "fund_id": fund_id,
        "page": page,
        "page_size": page_size
    }, None


def parse_position_payload():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None, error(
            code="VALIDATION_ERROR",
            message="请求体必须是 JSON 对象",
            details=[],
            http_status=400
        )

    blogger_id = parse_positive_int(data.get("blogger_id"))
    fund_id = parse_positive_int(data.get("fund_id"))
    shares = parse_non_negative_number(data.get("shares"))
    cost_amount = parse_non_negative_number(data.get("cost_amount"))
    record_date = data.get("record_date")
    details = []

    if blogger_id is None:
        details.append(
            {
                "field": "blogger_id",
                "message": "博主 ID 必须为正整数"
            }
        )

    if fund_id is None:
        details.append(
            {
                "field": "fund_id",
                "message": "基金 ID 必须为正整数"
            }
        )

    if shares is None:
        details.append(
            {
                "field": "shares",
                "message": "份额必须是大于等于 0 的数字"
            }
        )

    if cost_amount is None:
        details.append(
            {
                "field": "cost_amount",
                "message": "成本金额必须是大于等于 0 的数字"
            }
        )

    parsed_record_date = None

    if not isinstance(record_date, str):
        details.append(
            {
                "field": "record_date",
                "message": "记录日期不能为空"
            }
        )
    else:
        try:
            parsed_record_date = datetime.strptime(
                record_date,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            details.append(
                {
                    "field": "record_date",
                    "message": "记录日期格式必须是 YYYY-MM-DD"
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
        "blogger_id": blogger_id,
        "fund_id": fund_id,
        "shares": shares,
        "cost_amount": cost_amount,
        "record_date": parsed_record_date
    }, None


def check_blogger_exists(cursor, blogger_id):
    cursor.execute(
        "SELECT id FROM bloggers WHERE id = %s",
        (blogger_id,)
    )
    return cursor.fetchone() is not None


def check_fund_exists(cursor, fund_id):
    cursor.execute(
        "SELECT id FROM funds WHERE id = %s",
        (fund_id,)
    )
    return cursor.fetchone() is not None


@initial_positions_bp.get("/api/v1/initial-positions")
def list_initial_positions():
    params, error_response = parse_list_params()

    if error_response is not None:
        return error_response

    conditions = []
    values = []

    if params["blogger_id"] is not None:
        conditions.append("ip.blogger_id = %s")
        values.append(params["blogger_id"])

    if params["fund_id"] is not None:
        conditions.append("ip.fund_id = %s")
        values.append(params["fund_id"])

    where_sql = " AND ".join(conditions) if conditions else "1 = 1"
    offset = (params["page"] - 1) * params["page_size"]
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            count_sql = f"""
                SELECT COUNT(*) AS total
                FROM initial_positions ip
                WHERE {where_sql}
            """
            cursor.execute(count_sql, values)
            total_row = cursor.fetchone()
            total = total_row["total"]

            list_sql = f"""
                SELECT
                    ip.id,
                    ip.blogger_id,
                    b.name AS blogger_name,
                    ip.fund_id,
                    f.name AS fund_name,
                    f.fund_code,
                    ip.shares,
                    ip.cost_amount,
                    ip.record_date
                FROM initial_positions ip
                JOIN bloggers b ON b.id = ip.blogger_id
                JOIN funds f ON f.id = ip.fund_id
                WHERE {where_sql}
                ORDER BY ip.id DESC
                LIMIT %s OFFSET %s
            """
            query_values = values + [params["page_size"], offset]
            cursor.execute(list_sql, query_values)
            rows = cursor.fetchall()
    finally:
        conn.close()

    return success(
        data={
            "items": [serialize_initial_position(row) for row in rows],
            "page": params["page"],
            "page_size": params["page_size"],
            "total": total
        }
    )


@initial_positions_bp.post("/api/v1/initial-positions")
def create_initial_position():
    payload, error_response = parse_position_payload()

    if error_response is not None:
        return error_response

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            if not check_blogger_exists(cursor, payload["blogger_id"]):
                return error(
                    code="BLOGGER_NOT_FOUND",
                    message="博主不存在",
                    details=[],
                    http_status=404
                )

            if not check_fund_exists(cursor, payload["fund_id"]):
                return error(
                    code="FUND_NOT_FOUND",
                    message="基金不存在",
                    details=[],
                    http_status=404
                )

            cursor.execute(
                """
                SELECT id
                FROM initial_positions
                WHERE blogger_id = %s
                  AND fund_id = %s
                  AND record_date = %s
                LIMIT 1
                """,
                (
                    payload["blogger_id"],
                    payload["fund_id"],
                    payload["record_date"]
                )
            )
            duplicated_row = cursor.fetchone()

            if duplicated_row is not None:
                return error(
                    code="INITIAL_POSITION_DUPLICATED",
                    message="同一博主、同一基金、同一记录日期的初始持仓已存在",
                    details=[],
                    http_status=409
                )

            cursor.execute(
                """
                INSERT INTO initial_positions (
                    blogger_id,
                    fund_id,
                    shares,
                    cost_amount,
                    record_date
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    payload["blogger_id"],
                    payload["fund_id"],
                    payload["shares"],
                    payload["cost_amount"],
                    payload["record_date"]
                )
            )
            initial_position_id = cursor.lastrowid
            conn.commit()
            data = fetch_initial_position(cursor, initial_position_id)
    finally:
        conn.close()

    return success(data=data)


@initial_positions_bp.put("/api/v1/initial-positions/<initial_position_id>")
def update_initial_position(initial_position_id):
    initial_position_id = parse_positive_int(initial_position_id)

    if initial_position_id is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "initial_position_id",
                    "message": "初始持仓 ID 必须为正整数"
                }
            ],
            http_status=400
        )

    payload, error_response = parse_position_payload()

    if error_response is not None:
        return error_response

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM initial_positions WHERE id = %s",
                (initial_position_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return error(
                    code="INITIAL_POSITION_NOT_FOUND",
                    message="初始持仓不存在",
                    details=[],
                    http_status=404
                )

            if not check_blogger_exists(cursor, payload["blogger_id"]):
                return error(
                    code="BLOGGER_NOT_FOUND",
                    message="博主不存在",
                    details=[],
                    http_status=404
                )

            if not check_fund_exists(cursor, payload["fund_id"]):
                return error(
                    code="FUND_NOT_FOUND",
                    message="基金不存在",
                    details=[],
                    http_status=404
                )

            cursor.execute(
                """
                SELECT id
                FROM initial_positions
                WHERE blogger_id = %s
                  AND fund_id = %s
                  AND record_date = %s
                  AND id <> %s
                LIMIT 1
                """,
                (
                    payload["blogger_id"],
                    payload["fund_id"],
                    payload["record_date"],
                    initial_position_id
                )
            )
            duplicated_row = cursor.fetchone()

            if duplicated_row is not None:
                return error(
                    code="INITIAL_POSITION_DUPLICATED",
                    message="同一博主、同一基金、同一记录日期的初始持仓已存在",
                    details=[],
                    http_status=409
                )

            cursor.execute(
                """
                UPDATE initial_positions
                SET blogger_id = %s,
                    fund_id = %s,
                    shares = %s,
                    cost_amount = %s,
                    record_date = %s
                WHERE id = %s
                """,
                (
                    payload["blogger_id"],
                    payload["fund_id"],
                    payload["shares"],
                    payload["cost_amount"],
                    payload["record_date"],
                    initial_position_id
                )
            )
            conn.commit()
            data = fetch_initial_position(cursor, initial_position_id)
    finally:
        conn.close()

    return success(data=data)
```

---

### 步骤 2：注册初始持仓 Blueprint

**必要性：**  
路由文件创建后，还必须注册到 Flask 应用，否则接口不可访问。

修改文件：

```text
backend/app/__init__.py
```

增加导入：

```python
from app.routes.initial_positions import initial_positions_bp
```

在 `create_app()` 中注册：

```python
app.register_blueprint(initial_positions_bp)
```

完整示例：

```python
from flask import Flask

from app.routes.health import health_bp
from app.routes.bloggers import bloggers_bp
from app.routes.funds import funds_bp
from app.routes.initial_positions import initial_positions_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(health_bp)
    app.register_blueprint(bloggers_bp)
    app.register_blueprint(funds_bp)
    app.register_blueprint(initial_positions_bp)

    return app
```

---

### 步骤 3：重启 Flask 服务

**必要性：**  
新增模块后必须重新加载服务，验证没有语法错误和路由注册问题。

```bash
python run.py
```

## 验证方式

### 1. 准备博主和基金

如果还没有测试数据，先新增：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/bloggers" \
  -H "Content-Type: application/json" \
  -d '{"name":"任务012测试博主","sector":"成长股","observe_start_date":"2026-09-30"}'

curl -X POST "http://127.0.0.1:5000/api/v1/funds" \
  -H "Content-Type: application/json" \
  -d '{"name":"任务012测试基金","fund_code":"TASK012"}'
```

假设博主 ID 是 `1`，基金 ID 是 `1`。

### 2. 新增初始持仓

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/initial-positions" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"shares":12000,"cost_amount":15600,"record_date":"2026-09-30"}'
```

预期返回 `code: 0`，HTTP 状态码是 `200`，并包含博主名称、基金名称、基金代码。

本项目所有接口的成功响应统一使用 `200`，新增接口也不例外。  
`success()` 函数（任务 003 定义）没有 `http_status` 参数，不要给它传 `http_status=201`，否则会报 `TypeError`。

### 3. 查询初始持仓列表

```bash
curl "http://127.0.0.1:5000/api/v1/initial-positions"
```

预期返回分页字段和 `data.items`。

```bash
curl "http://127.0.0.1:5000/api/v1/initial-positions?blogger_id=1"
curl "http://127.0.0.1:5000/api/v1/initial-positions?fund_id=1"
```

预期分别按博主和基金筛选。

### 4. 编辑初始持仓

假设初始持仓 ID 是 `1`：

```bash
curl -X PUT "http://127.0.0.1:5000/api/v1/initial-positions/1" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"shares":13000,"cost_amount":16000,"record_date":"2026-09-30"}'
```

预期返回 `code: 0`，`shares` 变为 `13000`，`cost_amount` 变为 `16000`。

### 5. 验证重复数据

再次执行相同的新增请求：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/initial-positions" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"shares":12000,"cost_amount":15600,"record_date":"2026-09-30"}'
```

预期返回 `INITIAL_POSITION_DUPLICATED`，HTTP 状态码是 `409`。

### 6. 验证博主或基金不存在

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/initial-positions" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":999999,"fund_id":1,"shares":12000,"cost_amount":15600,"record_date":"2026-09-30"}'

curl -X POST "http://127.0.0.1:5000/api/v1/initial-positions" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":999999,"shares":12000,"cost_amount":15600,"record_date":"2026-09-30"}'
```

第一个预期返回 `BLOGGER_NOT_FOUND`。  
第二个预期返回 `FUND_NOT_FOUND`。

### 7. 验证参数错误

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/initial-positions" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":0,"fund_id":0,"shares":-1,"cost_amount":-1,"record_date":"2026/09/30"}'
```

预期返回 `VALIDATION_ERROR`，HTTP 状态码是 `400`。

## 常见坑

### 1. 没有关联查询名称

如果返回结果里只有 `blogger_id` 和 `fund_id`，说明 SQL 没有使用 JOIN。接口要求返回：

- `blogger_name`
- `fund_name`
- `fund_code`

### 2. `DECIMAL` 不能直接给 JSON

MySQL 的 `DECIMAL` 类型在 Python 中通常会被 PyMySQL 转成 `Decimal`。  
JSON 序列化可能报错，所以序列化时使用：

```python
float(row["shares"])
```

第一版可以这样做，后续如果对金额精度要求更高，再和前端约定字符串格式。

### 3. 忘记检查博主和基金是否存在

虽然数据库有外键，直接插入会报数据库错误，但业务接口应该返回统一 JSON：

- `BLOGGER_NOT_FOUND`
- `FUND_NOT_FOUND`

不要把数据库原始异常直接抛给前端。

### 4. 编辑时唯一性校验没有排除当前记录

错误写法：

```sql
WHERE blogger_id = %s AND fund_id = %s AND record_date = %s
```

正确写法：

```sql
WHERE blogger_id = %s
  AND fund_id = %s
  AND record_date = %s
  AND id <> %s
```

否则未修改关键字的记录也会被误判为重复。

### 5. 并发请求产生重复数据

代码里的重复检查不是绝对安全。如果两个请求几乎同时提交，可能都通过检查。  
数据库里的唯一索引会兜底。出现这种情况应返回 `INITIAL_POSITION_DUPLICATED`。

### 6. 忘记注册 Blueprint

如果访问 `/api/v1/initial-positions` 返回 HTML `404`，通常是 `initial_positions_bp` 没有注册。

检查命令：

```bash
grep -n "initial_positions_bp" app/__init__.py
```

## 完成标准

以下条件全部满足，任务 012 才算完成：

1. `GET /api/v1/initial-positions` 支持分页。
2. 列表支持按 `blogger_id` 和 `fund_id` 筛选。
3. 列表返回博主名称、基金名称、基金代码。
4. `POST /api/v1/initial-positions` 可以新增初始持仓。
5. 博主或基金不存在时返回对应 `404` 错误。
6. 份额和成本金额小于 0 时返回 `400`。
7. 记录日期格式错误时返回 `400`。
8. 同一博主、同一基金、同一记录日期重复时返回 `409`。
9. `PUT /api/v1/initial-positions/{initial_position_id}` 可以完整更新初始持仓。
10. 所有响应都是统一 JSON 结构。

## 完成后请反馈

1. 新增和修改的文件列表。
2. 初始持仓新增、列表、编辑的验证命令和输出。
3. 重复数据、博主不存在、基金不存在的验证结果。
4. 遇到的问题和未完成项。
