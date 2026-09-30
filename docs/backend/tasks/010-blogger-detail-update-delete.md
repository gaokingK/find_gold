# 任务 010：实现博主详情、编辑、删除接口

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务在任务 008 和 009 的基础上实现 3 个小接口，分别是详情查询、完整更新和删除；核心 SQL 都是单表操作，但需要处理路径参数、重复名称、事务提交和级联删除。

## 任务目标

实现：

```http
GET /api/v1/bloggers/{blogger_id}
PUT /api/v1/bloggers/{blogger_id}
DELETE /api/v1/bloggers/{blogger_id}
```

完成后可以：

1. 查询单个博主详情。
2. 编辑博主名称、所属板块、观察开始日。
3. 删除博主，并删除该博主名下的初始持仓。
4. 所有错误都返回统一 JSON 结构。

## 范围说明

本任务只处理博主详情、编辑和删除。

不包含：

- 基金接口
- 初始持仓接口
- 分层改造
- 归档功能
- 权限校验

## 前置条件

1. 任务 008 已完成，`GET /api/v1/bloggers` 可以查询 MySQL 数据。
2. 任务 009 已完成，`POST /api/v1/bloggers` 可以新增博主。
3. `backend/database/v1-basic-management.sql` 中的表已经初始化成功。

## 新概念：路径参数、PUT 请求、DELETE 请求

### 路径参数（Path Parameter）

路径参数是写在 URL 路径里的参数，例如：

```http
GET /api/v1/bloggers/1
```

这里的 `1` 就是路径参数。

Flask 写法：

```python
@bloggers_bp.get("/api/v1/bloggers/<blogger_id>")
def get_blogger(blogger_id):
    pass
```

### PUT 请求

PUT 请求通常用于更新数据。本项目的第一版使用完整更新，也就是每次编辑博主时，前端必须把 `name`、`sector`、`observe_start_date` 全部传过来。

### DELETE 请求

DELETE 请求通常用于删除数据。本项目的删除博主接口会同时删除该博主的初始持仓。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：修改 `bloggers.py` 的辅助函数

**必要性：**  
详情、编辑、删除都需要根据路径中的博主 ID 定位数据。先添加通用辅助函数，避免三个接口重复写相同的查询和校验逻辑。

修改文件：

```text
backend/app/routes/bloggers.py
```

在已有代码后面新增：

```python
def parse_blogger_id(value):
    if isinstance(value, bool):
        return None

    try:
        blogger_id = int(value)
    except (TypeError, ValueError):
        return None

    if blogger_id <= 0:
        return None

    return blogger_id


def fetch_blogger(cursor, blogger_id):
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

    if row is None:
        return None

    return serialize_blogger(row)


def parse_update_blogger_payload():
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
        details.append({"field": "name", "message": "博主名称不能为空"})

    if not isinstance(sector, str) or not sector.strip():
        details.append({"field": "sector", "message": "所属板块不能为空"})

    if not isinstance(observe_start_date, str):
        details.append({"field": "observe_start_date", "message": "观察开始日不能为空"})
    else:
        try:
            observe_start_date = datetime.strptime(
                observe_start_date,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            details.append(
                {
                    "field": "observe_start_date",
                    "message": "观察开始日格式必须是 YYYY-MM-DD"
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
        "observe_start_date": observe_start_date
    }, None
```

说明：

- `parse_blogger_id()` 用于把路径参数转换成正整数，避免 `0`、负数、非数字进入 SQL。
- `fetch_blogger()` 用于按 ID 查询单个博主，避免详情和编辑接口重复写同一段 SQL。
- `parse_update_blogger_payload()` 用于校验编辑接口的 JSON 请求体。

---

### 步骤 2：新增详情接口

**必要性：**  
前端编辑页通常先查询详情，再填充表单。没有详情接口，编辑功能无法稳定实现。

在 `bloggers.py` 末尾新增：

```python
@bloggers_bp.get("/api/v1/bloggers/<blogger_id>")
def get_blogger(blogger_id):
    blogger_id = parse_blogger_id(blogger_id)

    if blogger_id is None:
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

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            data = fetch_blogger(cursor, blogger_id)
    finally:
        conn.close()

    if data is None:
        return error(
            code="BLOGGER_NOT_FOUND",
            message="博主不存在",
            details=[],
            http_status=404
        )

    return success(data=data)
```

---

### 步骤 3：新增编辑接口

**必要性：**  
博主信息可能录入错误，也可能需要调整观察开始日。编辑后必须重新计算观察天数和状态。

在 `bloggers.py` 末尾新增：

```python
@bloggers_bp.put("/api/v1/bloggers/<blogger_id>")
def update_blogger(blogger_id):
    blogger_id = parse_blogger_id(blogger_id)

    if blogger_id is None:
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

    payload, error_response = parse_update_blogger_payload()

    if error_response is not None:
        return error_response

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM bloggers WHERE id = %s",
                (blogger_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return error(
                    code="BLOGGER_NOT_FOUND",
                    message="博主不存在",
                    details=[],
                    http_status=404
                )

            cursor.execute(
                """
                SELECT id
                FROM bloggers
                WHERE name = %s AND id <> %s
                LIMIT 1
                """,
                (payload["name"], blogger_id)
            )
            duplicated_row = cursor.fetchone()

            if duplicated_row is not None:
                return error(
                    code="BLOGGER_NAME_DUPLICATED",
                    message="博主名称已存在",
                    details=[],
                    http_status=409
                )

            cursor.execute(
                """
                UPDATE bloggers
                SET name = %s,
                    sector = %s,
                    observe_start_date = %s
                WHERE id = %s
                """,
                (
                    payload["name"],
                    payload["sector"],
                    payload["observe_start_date"],
                    blogger_id
                )
            )
            conn.commit()
            data = fetch_blogger(cursor, blogger_id)
    finally:
        conn.close()

    return success(data=data)
```

说明：  
`conn.commit()` 会把当前事务里的修改真正写入数据库。没有 `commit()`，服务重启后修改可能丢失。

---

### 步骤 4：新增删除接口

**必要性：**  
使用者可能不再需要追踪某个博主。删除博主时必须同步删除其初始持仓，否则数据库里会留下没有归属的数据。

在 `bloggers.py` 末尾新增：

```python
@bloggers_bp.delete("/api/v1/bloggers/<blogger_id>")
def delete_blogger(blogger_id):
    blogger_id = parse_blogger_id(blogger_id)

    if blogger_id is None:
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

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM bloggers WHERE id = %s",
                (blogger_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return error(
                    code="BLOGGER_NOT_FOUND",
                    message="博主不存在",
                    details=[],
                    http_status=404
                )

            cursor.execute(
                "DELETE FROM initial_positions WHERE blogger_id = %s",
                (blogger_id,)
            )
            cursor.execute(
                "DELETE FROM bloggers WHERE id = %s",
                (blogger_id,)
            )
            conn.commit()
    finally:
        conn.close()

    return success(data={})
```

说明：  
当前表结构的外键没有设置 `ON DELETE CASCADE`，所以这里先删除 `initial_positions`，再删除 `bloggers`。

---

### 步骤 5：重启 Flask 服务

**必要性：**  
修改 Python 文件后需要重新加载服务，确认没有语法错误。

```bash
python run.py
```

如果已启动，先停止后重新启动。

## 验证方式

### 1. 新增一个测试博主

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/bloggers" \
  -H "Content-Type: application/json" \
  -d '{"name":"任务010测试博主","sector":"成长股","observe_start_date":"2026-09-30"}'
```

预期返回 `code: 0`，并包含 `blogger_id`。

### 2. 查询详情

假设新增后的 ID 是 `1`：

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers/1"
```

预期返回完整博主数据。

### 3. 编辑博主

```bash
curl -X PUT "http://127.0.0.1:5000/api/v1/bloggers/1" \
  -H "Content-Type: application/json" \
  -d '{"name":"任务010修改后博主","sector":"价值股","observe_start_date":"2026-09-01"}'
```

预期：

- 返回 `code: 0`。
- 返回新的 `name`、`sector`、`observe_start_date`。
- `observe_days` 和 `status` 按新日期重新计算。

### 4. 验证重复名称

再新增一个博主后，尝试把 ID `1` 的名称改成另一个博主的名称：

```bash
curl -X PUT "http://127.0.0.1:5000/api/v1/bloggers/1" \
  -H "Content-Type: application/json" \
  -d '{"name":"已存在的博主名称","sector":"价值股","observe_start_date":"2026-09-01"}'
```

预期返回 `BLOGGER_NAME_DUPLICATED`，HTTP 状态码是 `409`。

### 5. 验证参数错误

```bash
curl -X PUT "http://127.0.0.1:5000/api/v1/bloggers/1" \
  -H "Content-Type: application/json" \
  -d '{"name":"","sector":"","observe_start_date":"2026/09/01"}'
```

预期返回 `VALIDATION_ERROR`，HTTP 状态码是 `400`。

### 6. 验证删除

```bash
curl -X DELETE "http://127.0.0.1:5000/api/v1/bloggers/1"
curl "http://127.0.0.1:5000/api/v1/bloggers/1"
```

第一次删除预期返回 `code: 0`。  
第二次查询预期返回 `BLOGGER_NOT_FOUND`，HTTP 状态码是 `404`。

## 常见坑

### 1. 路径参数没有转换成整数

如果直接把字符串传给 SQL，虽然参数化 SQL 可以避免 SQL 注入，但业务规则仍然要求博主 ID 是正整数。

排查命令：

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/abc"
curl -i "http://127.0.0.1:5000/api/v1/bloggers/0"
```

预期都返回统一 JSON 错误。

### 2. 编辑时没有排除自己

如果查询重复名称时写成：

```sql
WHERE name = %s
```

会把当前博主自己也当成重复。正确写法是：

```sql
WHERE name = %s AND id <> %s
```

### 3. 删除博主后初始持仓残留

先删除博主，再删除初始持仓，可能因为外键约束失败。

正确顺序是：

```sql
DELETE FROM initial_positions WHERE blogger_id = %s;
DELETE FROM bloggers WHERE id = %s;
```

### 4. 忘记 `conn.commit()`

如果执行了 `UPDATE` 或 `DELETE` 但没有提交，数据库连接关闭后修改可能没有真正生效。

再次调用查询接口确认数据变化。

### 5. 编辑成功但响应里日期对象报错

如果返回类似：

```text
TypeError: Object of type date is not JSON serializable
```

说明没有使用 `serialize_blogger()`。日期必须转换成 `YYYY-MM-DD` 字符串。

## 完成标准

以下条件全部满足，任务 010 才算完成：

1. `GET /api/v1/bloggers/{blogger_id}` 可以返回单个博主。
2. `PUT /api/v1/bloggers/{blogger_id}` 可以完整更新博主。
3. 编辑后 `observe_days` 和 `status` 会重新计算。
4. 博主名称重复时返回 `409`。
5. `DELETE /api/v1/bloggers/{blogger_id}` 可以删除博主。
6. 删除博主后，该博主的初始持仓也被删除。
7. 所有成功和错误响应都是统一 JSON 结构。
8. 重启服务后功能仍然正常。

## 完成后请反馈

1. 修改的文件列表。
2. `GET`、`PUT`、`DELETE` 的验证命令和输出。
3. 重复名称验证结果。
4. 删除博主后初始持仓是否同步删除。
5. 遇到的问题和未完成项。
