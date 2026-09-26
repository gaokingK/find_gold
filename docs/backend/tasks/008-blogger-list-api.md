# 任务 008：实现博主列表查询接口

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务要把临时接口改为真实数据库查询，并实现筛选、排序和分页； SQL 条件拼接需要小心。

## 任务目标

实现：

```text
GET /api/v1/bloggers
```

支持：

- `keyword`：按博主名称模糊搜索
- `sector`：按板块精确筛选
- `status`：`observing` 或 `active`
- `page`：页码
- `page_size`：每页数量
- `sort_by`：排序字段
- `order`：`asc` 或 `desc`

成功响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [],
    "page": 1,
    "page_size": 20,
    "total": 0
  }
}
```

## 范围说明

本任务只做博主列表查询。

不包含：

- 新增博主
- 编辑博主
- 删除博主
- 基金接口
- 初始持仓接口
- ORM
- service 层

## 前置条件

任务 007 已经完成，数据库中已经有 `bloggers` 表。

## 新概念：分页查询

分页查询的英文是 Pagination。

它的作用是不要一次返回所有数据，而是每次返回一页。

假设每页 20 条：

- 第 1 页：返回第 1 到第 20 条
- 第 2 页：返回第 21 到第 40 条

SQL 里常用：

```sql
LIMIT 20 OFFSET 0
```

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：确认数据库表已创建

**必要性：**  
接口要查询 `bloggers` 表。先确认表存在，可以减少后续排查范围。

执行：

```bash
python -m scripts.init_db
```

---

### 步骤 2：修改博主路由文件

**必要性：**  
任务 004 的 `/api/v1/bloggers` 只是练习读取参数。本任务要把它改成真正的数据库查询。

修改文件：

```text
backend/app/routes/bloggers.py
```

把文件内容替换为：

```python
from datetime import date

from flask import Blueprint, request

from app.db import get_connection
from app.utils.responses import error, success


bloggers_bp = Blueprint("bloggers", __name__)


ALLOWED_SORT_FIELDS = {
    "name": "b.name",
    "observe_start_date": "b.observe_start_date",
    "observe_days": "observe_days",
    "created_at": "b.created_at",
}


def calculate_status(observe_days):
    if observe_days is None:
        return "inactive"

    if observe_days < 30:
        return "observing"

    return "active"


def serialize_blogger(row):
    observe_start_date = row["observe_start_date"]
    created_at = row["created_at"]
    updated_at = row["updated_at"]

    return {
        "blogger_id": row["id"],
        "name": row["name"],
        "sector": row["sector"],
        "observe_start_date": observe_start_date.strftime("%Y-%m-%d"),
        "observe_days": row["observe_days"],
        "status": calculate_status(row["observe_days"]),
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": updated_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


def parse_common_params():
    keyword = request.args.get("keyword", "").strip()
    sector = request.args.get("sector", "").strip()
    status = request.args.get("status", "").strip()
    sort_by = request.args.get("sort_by", "created_at")
    order = request.args.get("order", "desc").lower()

    try:
        page = int(request.args.get("page", "1"))
        page_size = int(request.args.get("page_size", "20"))
    except ValueError:
        return None, error(
            code="VALIDATION_ERROR",
            message="分页参数不合法",
            details=[
                {
                    "field": "page/page_size",
                    "message": "page 和 page_size 必须是整数"
                }
            ],
            http_status=400
        )

    if page < 1:
        return None, error(
            code="VALIDATION_ERROR",
            message="page 参数不合法",
            details=[
                {
                    "field": "page",
                    "message": "page 必须大于等于 1"
                }
            ],
            http_status=400
        )

    if page_size < 1 or page_size > 100:
        return None, error(
            code="VALIDATION_ERROR",
            message="page_size 参数不合法",
            details=[
                {
                    "field": "page_size",
                    "message": "page_size 必须在 1 到 100 之间"
                }
            ],
            http_status=400
        )

    if status and status not in ["observing", "active"]:
        return None, error(
            code="VALIDATION_ERROR",
            message="status 参数不合法",
            details=[
                {
                    "field": "status",
                    "message": "status 只允许 observing 或 active"
                }
            ],
            http_status=400
        )

    if sort_by not in ALLOWED_SORT_FIELDS:
        return None, error(
            code="VALIDATION_ERROR",
            message="sort_by 参数不合法",
            details=[
                {
                    "field": "sort_by",
                    "message": "sort_by 只允许 name、observe_start_date、observe_days、created_at"
                }
            ],
            http_status=400
        )

    if order not in ["asc", "desc"]:
        return None, error(
            code="VALIDATION_ERROR",
            message="order 参数不合法",
            details=[
                {
                    "field": "order",
                    "message": "order 只允许 asc 或 desc"
                }
            ],
            http_status=400
        )

    params = {
        "keyword": keyword,
        "sector": sector,
        "status": status,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "page_size": page_size,
    }
    return params, None


def build_conditions(params):
    conditions = []
    values = []

    if params["keyword"]:
        conditions.append("b.name LIKE %s")
        values.append(f"%{params['keyword']}%")

    if params["sector"]:
        conditions.append("b.sector = %s")
        values.append(params["sector"])

    if params["status"] == "observing":
        conditions.append("DATEDIFF(CURDATE(), b.observe_start_date) < 30")

    if params["status"] == "active":
        conditions.append("DATEDIFF(CURDATE(), b.observe_start_date) >= 30")

    where_sql = " AND ".join(conditions) if conditions else "1 = 1"
    return where_sql, values


@bloggers_bp.get("/api/v1/bloggers")
def list_bloggers():
    params, error_response = parse_common_params()

    if error_response is not None:
        return error_response

    where_sql, values = build_conditions(params)
    sort_column = ALLOWED_SORT_FIELDS[params["sort_by"]]
    order_sql = "ASC" if params["order"] == "asc" else "DESC"
    offset = (params["page"] - 1) * params["page_size"]

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            count_sql = f"SELECT COUNT(*) AS total FROM bloggers b WHERE {where_sql}"
            cursor.execute(count_sql, values)
            total_row = cursor.fetchone()
            total = total_row["total"]

            list_sql = f"""
                SELECT
                    b.id,
                    b.name,
                    b.sector,
                    b.observe_start_date,
                    DATEDIFF(CURDATE(), b.observe_start_date) AS observe_days,
                    b.created_at,
                    b.updated_at
                FROM bloggers b
                WHERE {where_sql}
                ORDER BY {sort_column} {order_sql}
                LIMIT %s OFFSET %s
            """
            query_values = values + [params["page_size"], offset]
            cursor.execute(list_sql, query_values)
            rows = cursor.fetchall()
    finally:
        conn.close()

    return success(
        {
            "items": [serialize_blogger(row) for row in rows],
            "page": params["page"],
            "page_size": params["page_size"],
            "total": total
        }
    )
```

---

### 步骤 3：插入测试数据

**必要性：**  
空表只能验证响应结构，不能验证筛选和分页是否正确。

进入 MySQL：

```bash
mysql -u root -p fund_db
```

执行：

```sql
INSERT INTO bloggers (name, sector, observe_start_date)
VALUES
('测试博主A', '成长股', '2026-01-01'),
('测试博主B', '消费股', '2026-09-01'),
('测试博主C', '成长股', '2026-09-20');
```

退出 MySQL：

```sql
EXIT;
```

---

### 步骤 4：重启 Flask 服务

**必要性：**  
确保服务加载最新代码。

```bash
python run.py
```

## 验证方式

### 1. 查询全部

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers"
```

预期返回 `code=0`，并且包含 `items`、`page`、`page_size`、`total`。

### 2. 按关键字查询

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers?keyword=A"
```

预期只返回名称包含 `A` 的博主。

### 3. 按状态查询

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers?status=observing"
curl "http://127.0.0.1:5000/api/v1/bloggers?status=active"
```

### 4. 按页码查询

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers?page=1&page_size=2"
curl "http://127.0.0.1:5000/api/v1/bloggers?page=2&page_size=2"
```

### 5. 非法参数

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers?page=0"
curl -i "http://127.0.0.1:5000/api/v1/bloggers?page_size=101"
curl -i "http://127.0.0.1:5000/api/v1/bloggers?status=xxx"
```

预期都返回 `400`。

## 常见坑

### 1. SQL 注入风险

不要这样写：

```python
sql = f"... WHERE b.name LIKE '%{keyword}%'"
```

要使用参数化查询：

```python
cursor.execute(sql, values)
```

排序字段也不能直接使用用户输入，必须通过 `ALLOWED_SORT_FIELDS` 白名单转换。

---

### 2. 日期对象无法直接返回

MySQL 返回的日期是 Python 的 `date` 对象。  
接口返回前要转换成字符串：

```python
row["observe_start_date"].strftime("%Y-%m-%d")
```

---

### 3. `ORDER BY` 拼接错误

排序字段必须来自白名单。  
不要把用户输入的 `sort_by` 直接拼进 SQL。

---

### 4. 分页参数错误

`page` 从 `1` 开始，不是从 `0` 开始。  
`page_size` 最大值先限制为 `100`。

---

### 5. 忘记关闭数据库连接

使用：

```python
conn = get_connection()

try:
    ...
finally:
    conn.close()
```

## 完成标准

1. `GET /api/v1/bloggers` 使用真实 MySQL 查询。
2. 支持 `keyword`、`sector`、`status` 筛选。
3. 支持 `page`、`page_size` 分页。
4. 支持 `sort_by`、`order` 排序。
5. 非法参数返回 `400` 和统一错误结构。
6. 空表或无匹配数据时返回空数组，不报错。

## 完成后请反馈

请把下面命令的输出发给后端协调人：

```bash
sed -n '1,240p' app/routes/bloggers.py
curl "http://127.0.0.1:5000/api/v1/bloggers?page=1&page_size=2"
curl -i "http://127.0.0.1:5000/api/v1/bloggers?page=0"
```

任务 008 验收通过后，再进入任务 009：实现新增博主接口。
