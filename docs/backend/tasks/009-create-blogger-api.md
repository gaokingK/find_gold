# 任务 009：实现新增博主接口

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务引入 POST 请求、JSON 请求体、INSERT 语句和重复数据冲突处理；需要完成一个完整的写接口。

## 任务目标

实现：

```text
POST /api/v1/bloggers
```

使用者可以新增博主。

请求示例：

```json
{
  "name": "基金小星",
  "sector": "成长股",
  "observe_start_date": "2026-09-24"
}
```

成功响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "blogger_id": 1,
    "name": "基金小星",
    "sector": "成长股",
    "observe_start_date": "2026-09-24",
    "observe_days": 0,
    "status": "observing",
    "created_at": "2026-09-24 18:00:00",
    "updated_at": "2026-09-24 18:00:00"
  }
}
```

## 范围说明

本任务只做新增博主。

不包含：

- 编辑博主
- 删除博主
- 博主详情接口
- 基金接口
- 初始持仓接口
- service 层

## 前置条件

任务 008 已经完成，`GET /api/v1/bloggers` 可以查询 MySQL 数据。

## 新概念：POST 请求

POST 请求的英文是 POST Request。

GET 请求通常用于查询数据，参数放在 URL 里。  
POST 请求通常用于创建数据，数据放在请求体里。

本任务的请求体是 JSON：

```json
{
  "name": "基金小星",
  "sector": "成长股",
  "observe_start_date": "2026-09-24"
}
```

Flask 里使用：

```python
request.get_json(silent=True)
```

读取 JSON 请求体。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：确认博主列表接口可用

**必要性：**  
先确认任务 008 的基础正确，再写新增接口。

执行：

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers"
```

---

### 步骤 2：修改 `bloggers.py` 的导入

**必要性：**  
新增接口需要解析日期，也需要处理数据库唯一索引冲突。

修改文件：

```text
backend/app/routes/bloggers.py
```

把文件顶部的导入部分改为：

```python
from datetime import date, datetime

from flask import Blueprint, request
from pymysql.err import IntegrityError

from app.db import get_connection
from app.utils.responses import error, success


bloggers_bp = Blueprint("bloggers", __name__)
```

---

### 步骤 3：新增请求体解析函数

**必要性：**  
写接口必须校验请求体。否则空字符串、错误日期、错误类型的数据都会写进数据库。

在 `ALLOWED_SORT_FIELDS = {...}` 后面新增：

```python
def parse_create_blogger_payload():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None, error(
            code="VALIDATION_ERROR",
            message="请求体必须是 JSON 对象",
            details=[],
            http_status=400
        )

    name = data.get("name")
    sector = data.get("sector")
    observe_start_date = data.get("observe_start_date")

    details = []

    if not isinstance(name, str) or not name.strip():
        details.append(
            {
                "field": "name",
                "message": "博主名称不能为空"
            }
        )

    if not isinstance(sector, str) or not sector.strip():
        details.append(
            {
                "field": "sector",
                "message": "所属板块不能为空"
            }
        )

    parsed_date = None

    if not isinstance(observe_start_date, str) or not observe_start_date.strip():
        details.append(
            {
                "field": "observe_start_date",
                "message": "观察开始日不能为空"
            }
        )
    else:
        try:
            parsed_date = datetime.strptime(
                observe_start_date,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            details.append(
                {
                    "field": "observe_start_date",
                    "message": "观察开始日格式必须为 YYYY-MM-DD"
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
        "name": name.strip(),
        "sector": sector.strip(),
        "observe_start_date": parsed_date
    }, None
```

---

### 步骤 4：新增 POST 路由

**必要性：**  
这是本任务的核心接口。它会校验参数、检查重复名称、插入数据库并返回新增后的完整博主信息。

在文件末尾新增：

```python
@bloggers_bp.post("/api/v1/bloggers")
def create_blogger():
    payload, error_response = parse_create_blogger_payload()

    if error_response is not None:
        return error_response

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM bloggers WHERE name = %s",
                (payload["name"],)
            )
            existing = cursor.fetchone()

            if existing:
                return error(
                    code="BLOGGER_NAME_DUPLICATED",
                    message="博主名称已存在",
                    details=[],
                    http_status=409
                )

            cursor.execute(
                """
                INSERT INTO bloggers (name, sector, observe_start_date)
                VALUES (%s, %s, %s)
                """,
                (
                    payload["name"],
                    payload["sector"],
                    payload["observe_start_date"]
                )
            )
            blogger_id = cursor.lastrowid

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    sector,
                    observe_start_date,
                    DATEDIFF(CURDATE(), observe_start_date) AS observe_days,
                    created_at,
                    updated_at
                FROM bloggers
                WHERE id = %s
                """,
                (blogger_id,)
            )
            row = cursor.fetchone()

        conn.commit()
    finally:
        conn.close()

    return success(serialize_blogger(row))
```

---

### 步骤 5：重启 Flask 服务

**必要性：**  
POST 接口是新增代码，必须重启服务后才能访问。

先停止旧服务：

```text
Ctrl + C
```

再执行：

```bash
python run.py
```

## 验证方式

### 1. 新增成功

另开终端执行：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/bloggers" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试新增博主","sector":"成长股","observe_start_date":"2026-09-24"}'
```

预期：

```text
HTTP/1.1 200 OK
```

响应体中：

```json
{
  "code": 0,
  "message": "ok"
}
```

### 2. 查询列表确认新增

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers?keyword=测试新增博主"
```

应能看到刚才新增的数据。

### 3. 重复名称

再执行一次相同的新增请求：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/bloggers" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试新增博主","sector":"成长股","observe_start_date":"2026-09-24"}'
```

预期返回 `409`：

```json
{
  "code": "BLOGGER_NAME_DUPLICATED",
  "message": "博主名称已存在",
  "details": []
}
```

### 4. 缺少字段

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/bloggers" \
  -H "Content-Type: application/json" \
  -d '{"name":"","sector":"","observe_start_date":""}'
```

预期返回 `400` 和详细校验错误。

### 5. 日期格式错误

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/bloggers" \
  -H "Content-Type: application/json" \
  -d '{"name":"日期错误","sector":"成长股","observe_start_date":"2026/09/24"}'
```

预期返回 `400`。

## 常见坑

### 1. 请求体不是 JSON

`curl` 必须带：

```bash
-H "Content-Type: application/json"
```

否则 Flask 可能拿不到 JSON。

---

### 2. 忘记 `conn.commit()`

执行 `INSERT` 后必须提交：

```python
conn.commit()
```

否则数据库不会真正保存数据。

---

### 3. 重复校验不能只靠代码

代码里先查重，数据库里还有唯一索引兜底。  
两者都需要。

---

### 4. 不要把用户输入直接拼进 SQL

继续使用参数化查询：

```python
cursor.execute(sql, values)
```

---

### 5. 新增成功后要返回完整数据

不要只返回：

```json
{"blogger_id": 1}
```

前端通常需要立即展示新增后的完整博主信息。

## 完成标准

1. `POST /api/v1/bloggers` 可以写入数据库。
2. `name`、`sector`、`observe_start_date` 都会校验。
3. 重复名称返回 `409`。
4. 参数错误返回 `400`。
5. 新增成功后返回完整博主信息。
6. 数据真正写入 MySQL。

## 完成后请反馈

请把下面命令的输出发给后端协调人：

```bash
sed -n '1,320p' app/routes/bloggers.py
curl -X POST "http://127.0.0.1:5000/api/v1/bloggers" \
  -H "Content-Type: application/json" \
  -d '{"name":"反馈测试博主","sector":"成长股","observe_start_date":"2026-09-24"}'
curl "http://127.0.0.1:5000/api/v1/bloggers?keyword=反馈测试博主"
```

任务 009 验收通过后，第 2 天任务结束。下一步进入第 3 天任务 010：实现博主详情、编辑、删除接口。
