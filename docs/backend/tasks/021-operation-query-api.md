# 任务 021：实现操作记录查询接口

## 预计完成时间

预计完成时间：约 1.5 小时。

估算依据：本任务需要实现操作记录分页查询，支持博主、基金、操作类型、日期区间和备注关键字筛选。SQL 涉及 JOIN 和动态条件，但整体写法和任务 008 的博主列表接口高度相似，`serialize_operation()` 和 `parse_positive_int()` 也在任务 020 写好了，可以直接用。

## 任务目标

实现：

```http
GET /api/v1/operations
```

使用者可以查询操作记录列表。

支持：

1. 分页查询。
2. 按博主筛选。
3. 按基金筛选。
4. 按操作类型筛选。
5. 按操作日期区间筛选。
6. 按备注关键字搜索。
7. 返回博主名称、基金名称、基金代码。

## 范围说明

本任务只实现操作记录列表查询。

不包含：

- 单条详情接口（第一版不做）
- 编辑操作记录（第一版不做）
- 删除操作记录（任务 022）
- 持仓快照计算
- 收益计算
- 导出 CSV
- 权限校验

## 前置条件

1. 任务 020 已完成，`POST /api/v1/operations` 可用。
2. 数据库中已经存在测试用操作记录（至少 3 条，覆盖三种类型）。
3. `serialize_operation()` 和 `parse_positive_int()` 已经存在于 `operations.py`。

## 实现依据

接口契约在：

```text
docs/api/v1-operations.md
```

第 5 节列出了全部 10 个查询参数、各自的默认值和 7 条业务规则。  
**写代码前先通读第 5 节**，特别是默认值：`page` 默认 `1`、`page_size` 默认 `20`、`sort_by` 默认 `created_at`、`order` 默认 `desc`。这些默认值前端已经按文档实现了，不要自己改。

## 新概念：日期区间筛选

日期区间筛选是指只查询某个日期范围内的数据。  
SQL 中常用：

```sql
operation_date >= %s AND operation_date <= %s
```

本任务用 `date_from` 和 `date_to` 两个参数实现。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：添加查询参数解析函数

**必要性：**  
查询接口必须校验分页、日期、ID 和类型参数。否则非法参数会进入 SQL，导致错误查询或安全问题。

在 `backend/app/routes/operations.py` 中添加：

```python
ALLOWED_OPERATION_SORT_FIELDS = {
    "operation_date": "o.operation_date",
    "amount": "o.amount",
    "created_at": "o.created_at",
}


def parse_operation_list_params():
    details = []

    blogger_id = None
    fund_id = None
    operation_type = request.args.get("operation_type")

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

    if operation_type not in (None, "") and operation_type not in ALLOWED_OPERATION_TYPES:
        details.append(
            {
                "field": "operation_type",
                "message": "操作类型只允许 buy、sell、dividend_cash"
            }
        )

    date_from = None
    date_to = None

    raw_date_from = request.args.get("date_from")
    raw_date_to = request.args.get("date_to")

    if raw_date_from not in (None, ""):
        try:
            date_from = datetime.strptime(
                raw_date_from,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            details.append(
                {
                    "field": "date_from",
                    "message": "date_from 格式必须是 YYYY-MM-DD"
                }
            )

    if raw_date_to not in (None, ""):
        try:
            date_to = datetime.strptime(
                raw_date_to,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            details.append(
                {
                    "field": "date_to",
                    "message": "date_to 格式必须是 YYYY-MM-DD"
                }
            )

    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        details.append(
            {
                "field": "date_from",
                "message": "date_from 不能晚于 date_to"
            }
        )

    keyword = request.args.get("keyword", "").strip()

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
        details.append(
            {
                "field": "page",
                "message": "page 必须大于 0"
            }
        )

    if page_size <= 0 or page_size > 100:
        details.append(
            {
                "field": "page_size",
                "message": "page_size 必须在 1 到 100 之间"
            }
        )

    sort_by = request.args.get("sort_by", "created_at")
    order = request.args.get("order", "desc")

    if sort_by not in ALLOWED_OPERATION_SORT_FIELDS:
        details.append(
            {
                "field": "sort_by",
                "message": "排序字段只允许 operation_date、amount、created_at"
            }
        )

    if order not in ("asc", "desc"):
        details.append(
            {
                "field": "order",
                "message": "order 只允许 asc 或 desc"
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
        "operation_type": operation_type,
        "date_from": date_from,
        "date_to": date_to,
        "keyword": keyword,
        "page": page,
        "page_size": page_size,
        "sort_by": sort_by,
        "order": order
    }, None
```

---

### 步骤 2：添加查询条件构造函数

**必要性：**  
动态筛选条件不要直接拼用户输入。  
应先把条件写进 SQL 模板，把值放入参数列表。

在 `operations.py` 中添加：

```python
def build_operation_conditions(params):
    conditions = []
    values = []

    if params["blogger_id"] is not None:
        conditions.append("o.blogger_id = %s")
        values.append(params["blogger_id"])

    if params["fund_id"] is not None:
        conditions.append("o.fund_id = %s")
        values.append(params["fund_id"])

    if params["operation_type"] not in (None, ""):
        conditions.append("o.operation_type = %s")
        values.append(params["operation_type"])

    if params["date_from"] is not None:
        conditions.append("o.operation_date >= %s")
        values.append(params["date_from"])

    if params["date_to"] is not None:
        conditions.append("o.operation_date <= %s")
        values.append(params["date_to"])

    if params["keyword"]:
        conditions.append("o.remark LIKE %s")
        values.append(f"%{params['keyword']}%")

    where_sql = " AND ".join(conditions) if conditions else "1 = 1"

    return where_sql, values
```

---

### 步骤 3：新增查询路由

**必要性：**  
这是本任务的核心接口，负责分页查询操作记录并返回关联字段。

在 `operations.py` 末尾添加：

```python
@operations_bp.get("/api/v1/operations")
def list_operations():
    params, error_response = parse_operation_list_params()

    if error_response is not None:
        return error_response

    where_sql, values = build_operation_conditions(params)
    sort_column = ALLOWED_OPERATION_SORT_FIELDS[params["sort_by"]]
    order_sql = "ASC" if params["order"] == "asc" else "DESC"
    offset = (params["page"] - 1) * params["page_size"]

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            count_sql = f"""
                SELECT COUNT(*) AS total
                FROM operations o
                WHERE {where_sql}
            """
            cursor.execute(count_sql, values)
            total_row = cursor.fetchone()
            total = total_row["total"]

            list_sql = f"""
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
                    o.amount,
                    o.remark,
                    o.created_at,
                    o.updated_at
                FROM operations o
                JOIN bloggers b ON b.id = o.blogger_id
                JOIN funds f ON f.id = o.fund_id
                WHERE {where_sql}
                ORDER BY {sort_column} {order_sql}, o.id DESC
                LIMIT %s OFFSET %s
            """
            query_values = values + [params["page_size"], offset]
            cursor.execute(list_sql, query_values)
            rows = cursor.fetchall()
    finally:
        conn.close()

    return success(
        data={
            "items": [serialize_operation(row) for row in rows],
            "page": params["page"],
            "page_size": params["page_size"],
            "total": total
        }
    )
```

---

### 步骤 4：重启 Flask 服务

**必要性：**  
修改路由文件后需要重新加载服务，确认没有语法错误。

```bash
python run.py
```

如果服务已经在运行，先停止再启动。

## 验证方式

### 1. 查询全部操作记录

```bash
curl "http://127.0.0.1:5000/api/v1/operations"
```

预期返回：

- `data.items`
- `data.page`
- `data.page_size`
- `data.total`

### 2. 按博主筛选

假设博主 ID 是 `1`：

```bash
curl "http://127.0.0.1:5000/api/v1/operations?blogger_id=1"
```

预期只返回博主 1 的操作记录。

### 3. 按基金筛选

假设基金 ID 是 `1`：

```bash
curl "http://127.0.0.1:5000/api/v1/operations?fund_id=1"
```

预期只返回基金 1 的操作记录。

### 4. 按操作类型筛选

```bash
curl "http://127.0.0.1:5000/api/v1/operations?operation_type=buy"
curl "http://127.0.0.1:5000/api/v1/operations?operation_type=sell"
curl "http://127.0.0.1:5000/api/v1/operations?operation_type=dividend_cash"
```

预期分别返回对应类型的记录。

### 5. 按日期区间筛选

```bash
curl "http://127.0.0.1:5000/api/v1/operations?date_from=2026-09-01&date_to=2026-09-30"
```

预期只返回这个日期区间内的记录。

### 6. 按备注关键字搜索

```bash
curl "http://127.0.0.1:5000/api/v1/operations?keyword=第一次买入"
```

预期返回备注中包含关键字的记录。

### 7. 验证分页

```bash
curl "http://127.0.0.1:5000/api/v1/operations?page=1&page_size=2"
curl "http://127.0.0.1:5000/api/v1/operations?page=2&page_size=2"
```

预期返回不同页的数据，并且 `page_size` 是 `2`。

### 8. 验证排序

```bash
curl "http://127.0.0.1:5000/api/v1/operations?sort_by=amount&order=desc"
curl "http://127.0.0.1:5000/api/v1/operations?sort_by=amount&order=asc"
```

预期分别按金额从大到小、从小到大排序。

### 9. 验证非法参数

```bash
curl -i "http://127.0.0.1:5000/api/v1/operations?page=0"
curl -i "http://127.0.0.1:5000/api/v1/operations?page_size=101"
curl -i "http://127.0.0.1:5000/api/v1/operations?operation_type=transfer"
curl -i "http://127.0.0.1:5000/api/v1/operations?sort_by=password"
curl -i "http://127.0.0.1:5000/api/v1/operations?order=middle"
```

预期都返回 `VALIDATION_ERROR`，HTTP 状态码是 `400`。

## 常见坑

### 1. 动态条件拼错

多个筛选条件之间必须使用：

```sql
AND
```

如果没有任何条件，可以使用：

```sql
WHERE 1 = 1
```

方便后面统一拼接 `AND`。

### 2. 直接拼接排序字段

排序字段不能直接使用用户输入。  
必须使用 `ALLOWED_OPERATION_SORT_FIELDS` 白名单。

### 3. LIKE 查询没有参数化

不要写成：

```python
f"%{keyword}%"
```

然后直接拼进 SQL 字符串。  
正确方式是把 `f"%{keyword}%"` 放进 `values`，通过 `cursor.execute(sql, values)` 传入。

### 4. 分页参数没有上限

`page_size` 必须限制最大值，避免一次查询太多数据。

### 5. JOIN 后字段名冲突

`bloggers.name` 和 `funds.name` 都叫 `name`。  
SQL 中必须使用别名：

```sql
b.name AS blogger_name
f.name AS fund_name
```

### 6. 忘记关闭数据库连接

所有数据库操作都应该放在：

```python
try:
    ...
finally:
    conn.close()
```

### 7. 看到第四份重复的分页校验，想顺手抽成公共函数

到这里为止，博主、基金、初始持仓、操作记录四个模块里各有一份几乎一样的 `page` / `page_size` 校验代码。你会想把它们合并成一个工具函数——这个判断是对的。

但**不要在本任务里做**。抽公共函数要同时改四个模块，一旦改错，前面三个模块的测试会一起红，很难判断是新接口的问题还是重构的问题。

这件事已经排到第 6 天，记在：

```text
docs/backend/plans/backend-task-backlog.md
```

本任务照现有写法复制一份就行。

### 8. 把 `count_sql` 和 `list_sql` 的 WHERE 条件写得不一样

两条 SQL 必须用同一个 `where_sql` 和同一份 `values`。  
如果只给其中一条加了筛选条件，`total` 和 `items` 就会对不上——前端分页组件会显示「共 50 条」但翻到第 2 页是空的。

注意 `count_sql` 里不需要 JOIN `bloggers` 和 `funds`（外键保证了关联一定存在），但 `where_sql` 里的字段都带 `o.` 前缀，所以两边都能用。

## 完成标准

以下条件全部满足，任务 021 才算完成：

1. `GET /api/v1/operations` 可以分页查询，返回 `items`、`page`、`page_size`、`total`。
2. 支持按博主、基金、操作类型筛选，也支持多个条件同时生效。
3. 支持 `date_from` 和 `date_to` 日期区间筛选。
4. 支持备注关键字搜索，且 `keyword` 是参数化传入的。
5. 支持 `sort_by` 和 `order` 排序，排序字段走白名单。
6. 默认值与接口文档一致：`page=1`、`page_size=20`、`sort_by=created_at`、`order=desc`。
7. `page_size` 上限是 `100`。
8. 返回博主名称、基金名称、基金代码。
9. 非法参数返回 `VALIDATION_ERROR`，HTTP 状态码是 `400`。
10. 响应字段和 `docs/api/v1-operations.md` 第 3 节一致。
11. `total` 和实际筛选结果条数一致。

## 完成后请反馈

1. 修改的文件列表。
2. 上面 9 条验证的逐条结果（贴 curl 命令和响应）。
3. 响应字段是否和 `docs/api/v1-operations.md` 第 3 节完全一致。
4. 分页时 `total` 是否正确（可以用 `page_size=1` 翻几页确认）。
5. 遇到的问题和未完成项。
