# 任务 011：实现基金列表、新增、编辑接口

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务需要新建一个基金模块，实现 3 个接口，并处理基金代码唯一冲突；查询和写操作的 SQL 都是单表操作，但需要注册新的 Blueprint（蓝图）。

## 任务目标

实现：

```http
GET /api/v1/funds
POST /api/v1/funds
PUT /api/v1/funds/{fund_id}
```

完成后可以：

1. 分页查询基金列表。
2. 按基金名称或基金代码搜索。
3. 新增基金。
4. 编辑基金名称和基金代码。
5. 基金代码重复时返回统一业务错误。

## 范围说明

本任务只处理基金列表、新增和编辑。

不包含：

- 删除基金
- 初始持仓接口
- service 层
- repository 层
- 基金净值、市值、收益计算

## 前置条件

1. 任务 007 已完成，`funds` 表可以创建。
2. 任务 008 已完成，项目里已经有博主列表接口的写法参考。
3. 任务 010 已完成，博主模块具备详情、编辑、删除能力。

## 新概念：完整更新

完整更新的英文是 Full Update。

本项目的编辑基金接口使用 `PUT` 请求。调用时前端必须传完整的业务字段：

- `name`
- `fund_code`

不采用只传变化字段的局部更新。这样可以先保持接口规则简单。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建基金路由文件

**必要性：**  
基金和博主是两个业务模块。把基金路由放到单独文件里，可以避免 `bloggers.py` 越来越大，也方便后面维护。

新建文件：

```text
backend/app/routes/funds.py
```

内容：

```python
from flask import Blueprint, request

from app.db import get_connection
from app.utils.responses import error, success


funds_bp = Blueprint("funds", __name__)


def parse_fund_id(value):
    if isinstance(value, bool):
        return None

    try:
        fund_id = int(value)
    except (TypeError, ValueError):
        return None

    if fund_id <= 0:
        return None

    return fund_id


def serialize_fund(row):
    created_at = row["created_at"]
    updated_at = row["updated_at"]

    return {
        "fund_id": row["id"],
        "name": row["name"],
        "fund_code": row["fund_code"],
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": updated_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


def fetch_fund(cursor, fund_id):
    cursor.execute(
        """
        SELECT
            id,
            name,
            fund_code,
            created_at,
            updated_at
        FROM funds
        WHERE id = %s
        """,
        (fund_id,)
    )
    row = cursor.fetchone()

    if row is None:
        return None

    return serialize_fund(row)


def parse_list_params():
    keyword = request.args.get("keyword", "").strip()

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
    except (TypeError, ValueError):
        return None, error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "page",
                    "message": "page 和 page_size 必须是整数"
                }
            ],
            http_status=400
        )

    if page <= 0:
        return None, error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "page",
                    "message": "page 必须大于 0"
                }
            ],
            http_status=400
        )

    if page_size <= 0 or page_size > 100:
        return None, error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "page_size",
                    "message": "page_size 必须在 1 到 100 之间"
                }
            ],
            http_status=400
        )

    return {
        "keyword": keyword,
        "page": page,
        "page_size": page_size
    }, None


def parse_fund_payload():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None, error(
            code="VALIDATION_ERROR",
            message="请求体必须是 JSON 对象",
            details=[],
            http_status=400
        )

    name = data.get("name")
    fund_code = data.get("fund_code")
    details = []

    if not isinstance(name, str) or not name.strip():
        details.append({"field": "name", "message": "基金名称不能为空"})

    if not isinstance(fund_code, str) or not fund_code.strip():
        details.append({"field": "fund_code", "message": "基金代码不能为空"})

    if details:
        return None, error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=details,
            http_status=400
        )

    return {
        "name": name.strip(),
        "fund_code": fund_code.strip()
    }, None


@funds_bp.get("/api/v1/funds")
def list_funds():
    params, error_response = parse_list_params()

    if error_response is not None:
        return error_response

    conditions = []
    values = []

    if params["keyword"]:
        conditions.append("(name LIKE %s OR fund_code LIKE %s)")
        values.extend(
            [
                f"%{params['keyword']}%",
                f"%{params['keyword']}%"
            ]
        )

    where_sql = " AND ".join(conditions) if conditions else "1 = 1"
    offset = (params["page"] - 1) * params["page_size"]
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            count_sql = f"SELECT COUNT(*) AS total FROM funds WHERE {where_sql}"
            cursor.execute(count_sql, values)
            total_row = cursor.fetchone()
            total = total_row["total"]

            list_sql = f"""
                SELECT
                    id,
                    name,
                    fund_code,
                    created_at,
                    updated_at
                FROM funds
                WHERE {where_sql}
                ORDER BY id ASC
                LIMIT %s OFFSET %s
            """
            query_values = values + [params["page_size"], offset]
            cursor.execute(list_sql, query_values)
            rows = cursor.fetchall()
    finally:
        conn.close()

    return success(
        data={
            "items": [serialize_fund(row) for row in rows],
            "page": params["page"],
            "page_size": params["page_size"],
            "total": total
        }
    )


@funds_bp.post("/api/v1/funds")
def create_fund():
    payload, error_response = parse_fund_payload()

    if error_response is not None:
        return error_response

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM funds
                WHERE fund_code = %s
                LIMIT 1
                """,
                (payload["fund_code"],)
            )
            duplicated_row = cursor.fetchone()

            if duplicated_row is not None:
                return error(
                    code="FUND_CODE_DUPLICATED",
                    message="基金代码已存在",
                    details=[],
                    http_status=409
                )

            cursor.execute(
                """
                INSERT INTO funds (name, fund_code)
                VALUES (%s, %s)
                """,
                (payload["name"], payload["fund_code"])
            )
            fund_id = cursor.lastrowid
            conn.commit()
            data = fetch_fund(cursor, fund_id)
    finally:
        conn.close()

    return success(data=data)


@funds_bp.put("/api/v1/funds/<fund_id>")
def update_fund(fund_id):
    fund_id = parse_fund_id(fund_id)

    if fund_id is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "fund_id",
                    "message": "基金 ID 必须为正整数"
                }
            ],
            http_status=400
        )

    payload, error_response = parse_fund_payload()

    if error_response is not None:
        return error_response

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM funds WHERE id = %s",
                (fund_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return error(
                    code="FUND_NOT_FOUND",
                    message="基金不存在",
                    details=[],
                    http_status=404
                )

            cursor.execute(
                """
                SELECT id
                FROM funds
                WHERE fund_code = %s AND id <> %s
                LIMIT 1
                """,
                (payload["fund_code"], fund_id)
            )
            duplicated_row = cursor.fetchone()

            if duplicated_row is not None:
                return error(
                    code="FUND_CODE_DUPLICATED",
                    message="基金代码已存在",
                    details=[],
                    http_status=409
                )

            cursor.execute(
                """
                UPDATE funds
                SET name = %s,
                    fund_code = %s
                WHERE id = %s
                """,
                (
                    payload["name"],
                    payload["fund_code"],
                    fund_id
                )
            )
            conn.commit()
            data = fetch_fund(cursor, fund_id)
    finally:
        conn.close()

    return success(data=data)
```

---

### 步骤 2：注册基金 Blueprint

**必要性：**  
`Blueprint（蓝图）` 用来把一组路由组织成独立模块。创建 `funds.py` 后，还必须在应用入口注册，否则访问基金接口会返回 `404`。

修改文件：

```text
backend/app/__init__.py
```

把导入和注册部分调整为：

```python
from flask import Flask

from app.routes.health import health_bp
from app.routes.bloggers import bloggers_bp
from app.routes.funds import funds_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(health_bp)
    app.register_blueprint(bloggers_bp)
    app.register_blueprint(funds_bp)

    return app
```

如果你当前 `app/__init__.py` 里已经注册了 `bloggers_bp`，只需要增加 `funds_bp` 相关的两行：

```python
from app.routes.funds import funds_bp
```

```python
app.register_blueprint(funds_bp)
```

---

### 步骤 3：重启 Flask 服务

**必要性：**  
新增路由文件和注册代码后必须重启，Flask 才能识别新接口。

```bash
python run.py
```

## 验证方式

### 1. 新增基金

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/funds" \
  -H "Content-Type: application/json" \
  -d '{"name":"华夏成长混合","fund_code":"000001"}'
```

预期返回 `code: 0`，HTTP 状态码是 `200`。

本项目所有接口的成功响应统一使用 `200`，新增接口也不例外。  
`success()` 函数（任务 003 定义）没有 `http_status` 参数，不要给它传 `http_status=201`，否则会报 `TypeError`。

### 2. 查询全部基金

```bash
curl "http://127.0.0.1:5000/api/v1/funds"
```

预期返回 `data.items`、`data.page`、`data.page_size`、`data.total`。

### 3. 按关键字搜索

```bash
curl "http://127.0.0.1:5000/api/v1/funds?keyword=华夏"
```

预期返回名称包含 `华夏` 的基金。

```bash
curl "http://127.0.0.1:5000/api/v1/funds?keyword=000001"
```

预期返回代码包含 `000001` 的基金。

### 4. 编辑基金

假设基金 ID 是 `1`：

```bash
curl -X PUT "http://127.0.0.1:5000/api/v1/funds/1" \
  -H "Content-Type: application/json" \
  -d '{"name":"华夏成长混合修改","fund_code":"000001"}'
```

预期返回 `code: 0` 和新名称。

### 5. 验证重复代码

先用另一个代码新增基金：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/funds" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试基金","fund_code":"TEST001"}'
```

再尝试把 ID `1` 的代码改成 `TEST001`：

```bash
curl -X PUT "http://127.0.0.1:5000/api/v1/funds/1" \
  -H "Content-Type: application/json" \
  -d '{"name":"华夏成长混合修改","fund_code":"TEST001"}'
```

预期返回 `FUND_CODE_DUPLICATED`，HTTP 状态码是 `409`。

### 6. 验证参数错误

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/funds" \
  -H "Content-Type: application/json" \
  -d '{"name":"","fund_code":""}'
```

预期返回 `VALIDATION_ERROR`，HTTP 状态码是 `400`。

## 常见坑

### 1. 忘记注册 Blueprint

如果访问 `/api/v1/funds` 返回 HTML `404`，通常是 `funds_bp` 没有注册。

检查命令：

```bash
grep -n "funds_bp" app/__init__.py
```

确认有：

```python
app.register_blueprint(funds_bp)
```

### 2. 编辑时重复校验没有排除当前基金

错误写法：

```sql
WHERE fund_code = %s
```

正确写法：

```sql
WHERE fund_code = %s AND id <> %s
```

否则基金没有修改代码时也可能被误判为重复。

### 3. `LIKE` 拼接用户输入

不要把关键字直接拼进 SQL。应使用：

```python
cursor.execute(sql, values)
```

并把 `%关键字%` 放进参数列表里，避免 SQL 注入。

### 4. 分页参数超过限制

接口文档约定 `page_size` 最大 `100`。不要只判断是否是整数，还要判断范围。

### 5. 新增成功忘记 `conn.commit()`

如果没有提交，`cursor.lastrowid` 可能返回了 ID，但再次查询时数据库里没有这条数据。

## 完成标准

以下条件全部满足，任务 011 才算完成：

1. `GET /api/v1/funds` 支持分页和关键字搜索。
2. `POST /api/v1/funds` 可以新增基金。
3. `PUT /api/v1/funds/{fund_id}` 可以编辑基金。
4. 基金代码重复时返回 `FUND_CODE_DUPLICATED`。
5. 基金不存在时返回 `FUND_NOT_FOUND`。
6. 所有响应都是统一 JSON 结构。
7. 重启服务后功能仍然正常。

## 完成后请反馈

1. 新增和修改的文件列表。
2. 新增、查询、编辑基金的验证命令和输出。
3. 基金代码重复的验证结果。
4. 遇到的问题和未完成项。
