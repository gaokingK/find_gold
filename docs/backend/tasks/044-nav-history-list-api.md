# 任务 044：实现净值列表查询接口

> **批次说明**：本任务属于 040 之后的补发批次。净值模块此前只有写入（`026` 单条 upsert、`028` CSV 导入），没有读取接口。040 的验收清单要求这个接口可用，但 001–040 里没有任务实现它，现在补上。

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：代码组织形式和任务 008（博主列表）完全一样——参数校验、条件构造、序列化、路由四段，可以照着 008 和 021 写；`nav_history.py` 里已有 `serialize_nav_history()`、`parse_positive_int()`、`error()`、`success()` 可复用，不需要新建文件、不需要注册新 Blueprint。真正的新东西只有两个：`Decimal.quantize()` 的定点化写法，和「`nav_date` 与 `date_from`/`date_to` 并存时以谁为准」的优先级判断。时间主要花在写 7 个测试函数（覆盖 14 组参数场景）和 7 条 curl 验证的逐值核对上；新增代码约 200 行，按实际产出折算 1.5 小时不够，定 2 小时。

## 任务目标

实现 `GET /api/v1/nav-history`，支持按基金、按单个净值日期、按日期区间筛选，支持分页。

完成后，导入 1000 行净值可以看到导入结果、按基金核对某天录了多少条、按区间查看历史净值。

## 范围说明

本任务只做净值**列表查询**。

不包含：净值新增 / 编辑 / 删除；净值单条详情接口；CSV 导入导出；按净值计算市值或收益；按博主筛选（净值不关联博主）；`sort_by` / `order` 排序参数。

**已知限制（不要自己补）**：第一版没有净值编辑和删除接口。用户发现某天净值录错时，只能用 `POST /api/v1/nav-history` 重新提交同一 `fund_id + nav_date` 来覆盖（`026` 已实现的 upsert 行为）。这是有意的设计，不要顺手加 `PUT` 或 `DELETE`。

**为什么没有 `sort_by` / `order`**：接口契约草稿（`docs/backend/review/api-contract-gaps.md` 第 5.3 节）里本接口只有 6 个参数，排序固定（`nav_date` 降序 + 同日 `fund_id` 升序）。所以 `ORDER BY` 里全是代码常量，没有用户输入拼进去，也不存在 SQL 注入；前端已按草稿实现页面，擅自加参数会造成两边不一致。前端若确实需要切换排序，请反馈协调人，不要在本任务里加。

## 前置条件

1. 任务 026 已完成，`POST /api/v1/nav-history` 可用，`backend/app/routes/nav_history.py` 已存在且 `nav_history_bp` 已注册。
2. 任务 028 已完成，`POST /api/v1/nav-history/import` 可用。
3. 任务 043 已完成，测试工厂函数统一为 `from factories import ...` 的写法。（043 之前 `tests/test_nav_history.py` 里有两个测试把 `create_fund` 当 fixture 传参，`pytest -q` 会报 `error`，本任务的测试没法在那种状态下验收。）
4. 数据库里至少存在一只基金，且 `nav_history` 表至少有 2 条净值数据（可用任务 028 的 curl 先导两条进来）。
5. `pytest -q` 当前全部通过。

## 接口定义

接口定义直接采用 `docs/backend/review/api-contract-gaps.md` 第 5.3 节，**写代码前先读那一节整节**；发现代码和它不一致时先停下来反馈，不要自己改契约。

**接口名称**：查询净值列表 / `list_nav_history`

**请求方法与路径**：

```http
GET /api/v1/nav-history
```

**功能说明**：分页查询已录入的净值记录，用于导入后核对和历史净值查看。

**请求头**：无需设置 `Content-Type`（GET 请求没有请求体）；第一版没有登录认证，不需要传 token。

### 请求参数

全部通过 query string 传递，**全部可选**。

| 字段 | 类型 | 是否必填 | 默认值 | 示例值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| fund_id | int | 否 | 无 | `1` | 按基金筛选，必须为正整数；传了不存在的 ID 返回空列表 |
| nav_date | string | 否 | 无 | `2026-09-30` | 按单个净值日期精确筛选，格式 `YYYY-MM-DD` |
| date_from | string | 否 | 无 | `2026-09-01` | 起始净值日期，含当天，格式 `YYYY-MM-DD` |
| date_to | string | 否 | 无 | `2026-09-30` | 结束净值日期，含当天，格式 `YYYY-MM-DD` |
| page | int | 否 | `1` | `1` | 页码，必须 ≥ 1 |
| page_size | int | 否 | `20` | `20` | 每页条数，范围 1–100 |

### 请求示例

```bash
curl "http://127.0.0.1:5000/api/v1/nav-history?fund_id=1&date_from=2026-09-01&date_to=2026-09-30"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| data.items | array | 净值数组 |
| data.items[].nav_id | int | 净值记录 ID |
| data.items[].fund_id | int | 基金 ID |
| data.items[].fund_name | string | 基金名称（JOIN `funds` 表取得） |
| data.items[].fund_code | string | 基金代码（JOIN `funds` 表取得） |
| data.items[].nav_date | string | 净值日期，`YYYY-MM-DD` |
| data.items[].nav | number | 单位净值，4 位小数 |
| data.items[].created_at | string | 创建时间，`YYYY-MM-DD HH:MM:SS` |
| data.items[].updated_at | string | 更新时间，`YYYY-MM-DD HH:MM:SS` |
| data.page | int | 当前页码，回显请求值 |
| data.page_size | int | 每页条数，回显请求值 |
| data.total | int | 符合筛选条件的总条数 |

### 成功响应示例

HTTP 状态码 `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "nav_id": 1,
        "fund_id": 1,
        "fund_name": "华夏成长混合",
        "fund_code": "000001",
        "nav_date": "2026-09-30",
        "nav": 1.2345,
        "created_at": "2026-09-30 10:00:00",
        "updated_at": "2026-09-30 10:00:00"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

### 错误响应示例

多个参数同时出错时，`details` 里**一次性返回全部错误**，不短路到第一条。

**1. 日期区间颠倒**，HTTP `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {"field": "date_from", "message": "date_from 不能晚于 date_to"}
  ]
}
```

**2. `fund_id` 不是正整数**，HTTP `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {"field": "fund_id", "message": "基金 ID 必须为正整数"}
  ]
}
```

**3. 日期格式不对或分页参数越界**，HTTP `400`（`field` 分别是 `nav_date` / `page`）：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {"field": "nav_date", "message": "nav_date 格式必须是 YYYY-MM-DD"},
    {"field": "page", "message": "page 必须大于等于 1"}
  ]
}
```

### 业务规则

1. 默认排序：`nav_date` 降序，同一天内按 `fund_id` 升序。
2. `nav_date` 与 `date_from` / `date_to` 同时传时，**以 `nav_date` 为准**，`date_from` / `date_to` 忽略。
3. `date_from` 不能晚于 `date_to`。
4. 传入不存在的 `fund_id` 时返回空列表，HTTP `200`，**不返回 404**。
5. `page` 超过最大页码时返回 HTTP `200`，`items` 为空数组，`total` 为真实总数，`page` 和 `page_size` 回显请求值。不报错，不截断。
6. `nav` 返回 4 位小数。

补充两条实现口径（草稿没写，按全局约定执行）：

7. 查询参数**不校验「不能晚于今天」**。传未来日期只会查不到数据，返回空列表，HTTP `200`。
8. 排序在 SQL 里额外带第三级 `, n.id DESC`。因为表上有 `UNIQUE (fund_id, nav_date)`，前两级排序键已唯一，第三级是防御性的：万一以后唯一索引被改掉，翻页也不会重复或漏行。

**关联接口**：录入或更新净值 `POST /api/v1/nav-history`（026）；批量导入 `POST /api/v1/nav-history/import`（028）；基金列表 `GET /api/v1/funds`（011，前端拿 `fund_id` 的来源）。

---

## 新概念

### 1. `Decimal` 定点化与 `ROUND_HALF_UP`

`nav` 在 MySQL 里是 `DECIMAL`，PyMySQL 读出来是 `Decimal` 对象；`Decimal` 不能直接进 JSON——`jsonify()` 遇到它会抛 `TypeError: Object of type Decimal is not JSON serializable`。所以转 `float` 之前要先**定点化**，用到两个东西：`Decimal.quantize(exp)`（把小数调整到 `exp` 指定的位数，并按指定舍入模式处理多余位）和 `ROUND_HALF_UP`（舍入模式 Rounding Mode 常量，中文叫「四舍五入」，`0.5` 一律进位）。

为什么要显式指定：`Decimal` **默认**用 `ROUND_HALF_EVEN`（银行家舍入），把 `0.5` 舍入到**最近的偶数**——`0.12345` 保留 4 位会变成 `0.1234` 而不是 `0.1235`，前后端算出来的数会对不上。本项目全局约定一律 `ROUND_HALF_UP`。

一句话记住：**先 `quantize` 定精度，再 `float` 转类型，顺序不能反**。

### 2. 二级排序

业务规则 1 对应 `ORDER BY n.nav_date DESC, n.fund_id ASC`，这叫**多列排序**：先按第一列排，第一列相同的那些行再按第二列排。

为什么必须写第二列：只写 `ORDER BY n.nav_date DESC` 时，同一天的多条记录 `nav_date` 完全相同，MySQL **不保证它们之间的先后顺序**。第一次查可能是 A、B、C，第二次可能是 C、A、B，前端翻页时就会出现「第 1 页最后一条在第 2 页又出现，同时有另一条永远看不到」。这是分页接口最容易漏的 bug，只在数据量大到需要翻页时才暴露。本接口再加一级 `, n.id DESC`，理由见业务规则 8。

## 执行目录

所有命令都在下面目录执行（每次新开终端都要先激活虚拟环境）：

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：确认净值表结构和现有路由文件

**必要性：**  
本任务要 JOIN `funds` 表、要读 `created_at` 和 `updated_at`，而不同版本的建表脚本里 `nav_history` 的列可能不一样（早期设计稿里就没有 `created_at`）。先确认真实列名单，可以避免写出 `SELECT` 一个不存在的列、报 `Unknown column` 后再回头排查。

```bash
mysql -u root -p fund_db -e "DESC nav_history; DESC funds;"
grep -n "^def \|^@\|^from \|^import " app/routes/nav_history.py
```

第一条（把 `fund_db` 换成你的开发库名）预期至少看到 `id`、`fund_id`、`nav_date`、`nav`、`created_at`、`updated_at`；**如果实际列名和本文档不一致，以实际表为准**并反馈协调人。第二条预期看到 `parse_positive_int`、`serialize_nav_history`、`upsert_nav_history`、`import_nav_history_csv` 等，以及顶部已导入 `datetime`、`Decimal`、`InvalidOperation`、`Blueprint`、`request`、`get_connection`、`error`、`success`。本任务要用到 `datetime`（解析日期）、`Decimal`（定点化），还要额外导入 `ROUND_HALF_UP`。现有函数全部保留，本任务只做**追加**。

---

### 步骤 2：添加日期解析辅助函数

**必要性：**  
三个日期参数都要做「字符串 → 日期」的转换，失败时要给统一错误提示。抽成一个函数、三个参数各调一次，比复制三遍 `try/except` 更不容易写错（尤其是容易漏掉 `strip()`）。

在 `backend/app/routes/nav_history.py` 中添加（放在 `parse_positive_int` 之后）：

```python
NAV_DATE_FORMAT = "%Y-%m-%d"


def parse_date_arg(raw_value, field_name, details):
    if raw_value in (None, ""):
        return None

    try:
        return datetime.strptime(raw_value.strip(), NAV_DATE_FORMAT).date()
    except ValueError:
        details.append({"field": field_name, "message": f"{field_name} 格式必须是 YYYY-MM-DD"})
        return None
```

说明：`datetime.strptime(text, format)` 是标准库函数，把字符串按指定格式解析成 `datetime` 再 `.date()` 取日期部分，`%Y-%m-%d` 对应 `2026-09-30`。**解析失败会抛 `ValueError`**（常见：`2026/09/30`、`2026-13-01`、`abc`），所以必须 `try/except`。返回的是 **`date` 对象**不是字符串，后面传进 SQL 的就是它（见「常见坑 1」）。`details` 是调用方传进来的列表，三个参数的错误能累积到同一个列表最后一次性返回。参数没传时返回 `None` 表示「不筛选」，**空字符串也算没传**。

---

### 步骤 3：添加查询参数校验函数

**必要性：**  
所有进 SQL 的参数必须先校验。`fund_id` 不校验会出现 `fund_id=abc` 导致 MySQL 报错或隐式转换；`page` / `page_size` 不校验会出现一次查 10 万条把服务拖垮、或 `OFFSET` 为负数报错。日期区间颠倒不校验则返回空列表，用户以为是「没数据」而不是「条件写反了」。

在 `nav_history.py` 中继续添加：

```python
def parse_nav_history_list_params():
    details = []

    raw_fund_id = request.args.get("fund_id")
    fund_id = None

    if raw_fund_id not in (None, ""):
        fund_id = parse_positive_int(raw_fund_id)

        if fund_id is None:
            details.append({"field": "fund_id", "message": "基金 ID 必须为正整数"})

    nav_date = parse_date_arg(request.args.get("nav_date"), "nav_date", details)
    date_from = parse_date_arg(request.args.get("date_from"), "date_from", details)
    date_to = parse_date_arg(request.args.get("date_to"), "date_to", details)

    if date_from is not None and date_to is not None and date_from > date_to:
        details.append({"field": "date_from", "message": "date_from 不能晚于 date_to"})

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
    except (TypeError, ValueError):
        details.append({"field": "page", "message": "page 和 page_size 必须是整数"})
        page = 0
        page_size = 0

    if page < 1:
        details.append({"field": "page", "message": "page 必须大于等于 1"})

    if page_size < 1 or page_size > 100:
        details.append({"field": "page_size", "message": "page_size 必须在 1 到 100 之间"})

    if details:
        return None, error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=details,
            http_status=400
        )

    return {
        "fund_id": fund_id,
        "nav_date": nav_date,
        "date_from": date_from,
        "date_to": date_to,
        "page": page,
        "page_size": page_size,
    }, None
```

说明：`parse_positive_int()` 是任务 026 已写好的函数，直接复用，**不要重写一份**（它遇到 `0`、`-1`、`abc`、`True` 都返回 `None`）。`request.args.get(...)` 取 query string 参数，返回值永远是字符串或 `None`。`int(...)` 包在 `try` 里，因为 `page=abc`、`page=1.5` 都会抛 `ValueError`；出错时把 `page` / `page_size` 置 `0`，是为了让后面两个范围判断不会误判成合法值。**所有错误累积进 `details` 一起返回**，不短路。另外 `date_from > date_to` 必须放在两个日期**都解析成功**之后：其中一个格式错了它自己就是 `None`，这条判断要跳过——否则拿 `None` 和 `date` 比较会抛 `TypeError`。

---

### 步骤 4：添加查询条件构造函数

**必要性：**  
这是业务规则 2（`nav_date` 优先）的落地点。把优先级逻辑单独写一个函数，比塞进路由函数里更容易看清、也更容易测；同时所有筛选值都放进 `values` 列表走参数化查询，不拼进 SQL 字符串。

在 `nav_history.py` 中继续添加：

```python
def build_nav_history_conditions(params):
    conditions = []
    values = []

    if params["fund_id"] is not None:
        conditions.append("n.fund_id = %s")
        values.append(params["fund_id"])

    if params["nav_date"] is not None:
        conditions.append("n.nav_date = %s")
        values.append(params["nav_date"])
    else:
        if params["date_from"] is not None:
            conditions.append("n.nav_date >= %s")
            values.append(params["date_from"])

        if params["date_to"] is not None:
            conditions.append("n.nav_date <= %s")
            values.append(params["date_to"])

    where_sql = " AND ".join(conditions) if conditions else "1 = 1"

    return where_sql, values
```

说明：**那个 `if / else` 就是优先级规则本身**——`nav_date` 有值时走 `if` 分支只加等值条件，`date_from` / `date_to` 根本不会被读取；`nav_date` 为空时才走 `else` 分支加区间条件。写成两个平级的 `if` 会让两个条件同时生效，结果永远是空列表（见「常见坑 2」）。`fund_id` 的条件在优先级判断**之外**，所以它能和 `nav_date` 同时生效（`conditions` 为空时用 `WHERE 1 = 1`，这样 `AND` 拼接不需要特殊处理第一条）。

---

### 步骤 5：给 `nav` 加上定点化

**必要性：**  
`nav` 是 `DECIMAL`，不转 `float` 会直接 500；转 `float` 之前不定点化，则返回值的位数取决于数据库里存了什么，前端可能拿到 `1.23450001` 这种。全局约定要求净值 4 位小数、`ROUND_HALF_UP` 定点化。

先修改文件顶部的 import，把 `ROUND_HALF_UP` 加进去：

```python
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
```

然后在 `nav_history.py` 中添加（放在 `parse_positive_int` 附近即可）：

```python
NAV_QUANTIZE = Decimal("0.0001")


def round_nav(value):
    if not isinstance(value, Decimal):
        value = Decimal(str(value))

    return value.quantize(NAV_QUANTIZE, rounding=ROUND_HALF_UP)
```

再**修改**任务 026 已写好的 `serialize_nav_history()`，把 `nav` 那一行改成走 `round_nav()`：

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
        "nav": float(round_nav(row["nav"])),
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": updated_at.strftime("%Y-%m-%d %H:%M:%S"),
    }
```

说明：`float(round_nav(...))` 的顺序是**先定点化、再转 `float`**，不能反过来。这个改动会同时影响 `POST /api/v1/nav-history` 的返回，符合全局约定；026、028 的测试里用的净值本身就是 4 位小数，值不会变，测试不会红。用 `git diff app/routes/nav_history.py` 确认改动**只有** import 一行、`round_nav` 一段、`serialize_nav_history` 里的一行。

---

### 步骤 6：添加 GET 路由并重启服务

**必要性：**  
这是本任务的核心接口，负责校验参数、查总数、查当页数据、组装响应。改完必须重启进程，否则验证的是旧代码；重启还能顺便暴露语法错误和 import 错误。

在 `backend/app/routes/nav_history.py` **末尾**添加：

```python
@nav_history_bp.get("/api/v1/nav-history")
def list_nav_history():
    params, error_response = parse_nav_history_list_params()

    if error_response is not None:
        return error_response

    where_sql, values = build_nav_history_conditions(params)
    offset = (params["page"] - 1) * params["page_size"]

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            count_sql = f"""
                SELECT COUNT(*) AS total
                FROM nav_history n
                WHERE {where_sql}
            """
            cursor.execute(count_sql, values)
            total = cursor.fetchone()["total"]

            list_sql = f"""
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
                WHERE {where_sql}
                ORDER BY n.nav_date DESC, n.fund_id ASC, n.id DESC
                LIMIT %s OFFSET %s
            """
            query_values = values + [params["page_size"], offset]
            cursor.execute(list_sql, query_values)
            rows = cursor.fetchall()
    finally:
        conn.close()

    return success(
        data={
            "items": [serialize_nav_history(row) for row in rows],
            "page": params["page"],
            "page_size": params["page_size"],
            "total": total
        }
    )
```

说明：`count_sql` 里**没有 JOIN `funds`**——`where_sql` 里的字段都带 `n.` 前缀，不需要 JOIN 也能执行，外键也保证每净值行一定有一只基金，JOIN 不会改变行数。但两条 SQL **必须用同一个 `where_sql` 和同一份 `values`**，只给其中一条加筛选条件就会出现「显示共 50 条，翻到第 2 页是空的」。`query_values = values + [...]` 不要写成 `values.append(...)`（那会改掉 `values` 本身）。`page` 越界时 `OFFSET` 算出来是 80，MySQL 返回空结果集不报错，`total` 走 `count_sql` 是真实总数，这就是业务规则 5，不需要额外写判断。`success()` 是任务 003 写的统一成功响应函数，HTTP 状态码固定 `200`，**不要传 `http_status=201`**。

重启：先在运行服务的终端按 `Ctrl + C`，然后执行 `python run.py`。预期输出 `* Running on http://127.0.0.1:5000`；注意看启动日志有没有 `NameError: name 'ROUND_HALF_UP' is not defined`——如果有，说明步骤 5 的 import 没改。

---

### 步骤 7：添加自动化测试

**必要性：**  
净值列表是导入功能的唯一核对手段，必须被测试守住，尤其是「`nav_date` 优先于日期区间」和「`page` 越界」这两条——前者写错了表现为「查不到数据」，后者写错了表现为「前端翻页崩」，都不容易在手工验收时发现。

先在 `backend/tests/factories.py` 末尾追加净值工厂函数：

```python
def create_nav_history(client, fund_id, nav_date, nav="1.2345"):
    response = client.post(
        "/api/v1/nav-history",
        json={"fund_id": fund_id, "nav_date": nav_date, "nav": nav}
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    return body["data"]
```

说明：`nav_date` 必须是不晚于今天的日期（026 的规则），否则工厂函数自己就会断言失败。用 `2026-09-29`、`2026-09-30` 这类固定日期，不要用「今天」这种动态值。

然后修改已存在的文件（任务 028 建的）`backend/tests/test_nav_history.py`：顶部导入区加 `from factories import create_fund, create_nav_history`，文件末尾追加以下测试：

```python
def test_list_nav_history_returns_empty_when_no_match(client):
    # 空表
    response = client.get("/api/v1/nav-history")
    body = response.get_json()

    assert response.status_code == 200
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0

    # 不存在的 fund_id：同样返回空列表 + 200，不是 404（业务规则 4）
    response = client.get("/api/v1/nav-history?fund_id=999999")
    body = response.get_json()

    assert response.status_code == 200
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


def test_list_nav_history_returns_created_records(client):
    fund = create_fund(client, name="净值列表基金", fund_code="NAVLIST01")
    create_nav_history(client, fund["fund_id"], "2026-09-29", "1.2000")
    create_nav_history(client, fund["fund_id"], "2026-09-30", "1.2345")

    response = client.get("/api/v1/nav-history")
    body = response.get_json()

    assert response.status_code == 200
    assert body["data"]["total"] == 2
    assert body["data"]["items"][0]["nav_date"] == "2026-09-30"
    assert body["data"]["items"][0]["fund_name"] == "净值列表基金"
    assert body["data"]["items"][0]["fund_code"] == "NAVLIST01"
    # 同时验证 nav 是 4 位小数（业务规则 6）
    assert body["data"]["items"][0]["nav"] == 1.2345

    # 按 fund_id 筛选能取到这只基金的净值
    response = client.get(f"/api/v1/nav-history?fund_id={fund['fund_id']}")
    body = response.get_json()

    assert response.status_code == 200
    assert body["data"]["total"] == 2
    assert body["data"]["items"][0]["fund_code"] == "NAVLIST01"


def test_list_nav_history_filter_by_date_range(client):
    fund = create_fund(client, name="区间筛选基金", fund_code="NAVLIST06")
    create_nav_history(client, fund["fund_id"], "2026-08-31", "1.1000")
    create_nav_history(client, fund["fund_id"], "2026-09-15", "1.2000")
    create_nav_history(client, fund["fund_id"], "2026-09-30", "1.3000")

    response = client.get("/api/v1/nav-history?date_from=2026-09-01&date_to=2026-09-30")
    body = response.get_json()

    assert response.status_code == 200
    assert body["data"]["total"] == 2
    assert [item["nav_date"] for item in body["data"]["items"]] == ["2026-09-30", "2026-09-15"]


def test_list_nav_history_nav_date_wins_over_date_range(client):
    fund = create_fund(client, name="优先级基金", fund_code="NAVLIST07")
    create_nav_history(client, fund["fund_id"], "2026-09-15", "1.2000")
    create_nav_history(client, fund["fund_id"], "2026-09-30", "1.3000")

    url = "/api/v1/nav-history?nav_date=2026-09-15&date_from=2026-09-20&date_to=2026-09-30"
    response = client.get(url)
    body = response.get_json()

    assert response.status_code == 200
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["nav_date"] == "2026-09-15"


def test_list_nav_history_rejects_reversed_date_range(client):
    response = client.get("/api/v1/nav-history?date_from=2026-09-30&date_to=2026-09-01")
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"][0]["field"] == "date_from"


def test_list_nav_history_returns_empty_when_page_out_of_range(client):
    fund = create_fund(client, name="翻页基金", fund_code="NAVLIST08")
    create_nav_history(client, fund["fund_id"], "2026-09-29", "1.1000")
    create_nav_history(client, fund["fund_id"], "2026-09-30", "1.2000")

    response = client.get("/api/v1/nav-history?page=99&page_size=20")
    body = response.get_json()

    assert response.status_code == 200
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 2
    assert body["data"]["page"] == 99
    assert body["data"]["page_size"] == 20


def test_list_nav_history_rejects_invalid_params(client):
    queries = [
        "page=0",
        "page_size=0",
        "page_size=101",
        "page=abc",
        "fund_id=abc",
        "fund_id=0",
        "nav_date=2026/09/30",
        "date_from=bad-date",
    ]

    for query in queries:
        response = client.get(f"/api/v1/nav-history?{query}")
        body = response.get_json()

        assert response.status_code == 400, f"参数 {query} 应该被拒绝"
        assert body["code"] == "VALIDATION_ERROR", f"参数 {query} 错误码不对"
```

说明：循环里 `assert ..., f"参数 {query} 应该被拒绝"` 叫**断言消息**，8 个参数里任何一个漏了校验，报错会直接告诉你是哪一个（不写的话只能看到「400 != 200」，得一个个试）。`test_list_nav_history_filter_by_date_range` 断言了**完整的日期顺序列表**而不只是 `total`，这同时验证了默认排序。`test_list_nav_history_nav_date_wins_over_date_range` 是本任务最重要的一条：如果步骤 4 写成了两个平级的 `if`，这个测试会拿到 `total == 0` 而不是 `1`，立刻红。`fund_code` 用 `NAVLIST01`–`NAVLIST08`，和 028 里的 `NAV000001`、`NAV000002` 不冲突。

---

### 步骤 8：跑测试

**必要性：**  
步骤 5 修改了 `serialize_nav_history()`，它同时被 `POST /api/v1/nav-history` 使用，只跑 `test_nav_history.py` 只能看到新接口没问题，必须跑全量确认 026 的单条录入测试没有被这次改动带崩。

```bash
pytest tests/test_nav_history.py -q
pytest -q
```

预期：**没有 failed，也没有 error**。

---

## 验证方式

用 curl 手工验证（自动化测试见步骤 8）。下面每条命令都要补全成 `curl "http://127.0.0.1:5000/api/v1/nav-history` + 表中「补全为」列的内容：

| # | 场景 | 补全为 | 预期 |
| --- | --- | --- | --- |
| 1 | 无匹配 | `?fund_id=999999"` | HTTP `200`，`items` 为 `[]`，`total` 为 `0`。**不是 404** |
| 2 | 正常查询 | `"` | HTTP `200`，`total` 等于实际条数，`items` 按 `nav_date` 降序，`nav` 是 4 位小数（`1.2345` 而不是 `1.23450000`） |
| 3 | 按区间筛选 | `?date_from=2026-09-01&date_to=2026-09-30"` | 只返回区间内记录，含边界两天 |
| 4 | 区间颠倒 | `-i "?date_from=2026-09-30&date_to=2026-09-01"` | HTTP `400`，`code` 是 `VALIDATION_ERROR`，`details[0].field` 是 `date_from` |
| 5 | `nav_date` 优先 | `?nav_date=2026-09-15&date_from=2026-09-20&date_to=2026-09-30"` | 返回 `2026-09-15` 的净值（区间被忽略），**不是空列表**。规则 2 的直接验证，不能省 |
| 6 | `page` 越界 | `?page=99&page_size=20"` | HTTP `200`，`items` 为 `[]`，`total` 为真实总数，`page` 回显 `99`，`page_size` 回显 `20` |
| 7 | 非法参数 | `-i "?page=0"`，再依次试 `page_size=101`、`fund_id=abc`、`nav_date=2026/09/30` | 四条全部 HTTP `400`，响应体是 JSON 不是 HTML |

## 常见坑

### 1. 把日期字符串直接拼进 SQL，或不做合法性校验

不是所有字符串都能被 MySQL 当日期用。`2026/09/30`、`bad-date`、`2026-02-31` 都会出问题，表现可能是 MySQL 报 `Incorrect DATE value`，也可能是**静默返回空结果**（某些宽松模式下）——后者最难查，用户会以为「这一天没净值」。

正确做法就是步骤 2：用 `datetime.strptime(value, "%Y-%m-%d")` 解析，失败就返回 400；成功后把得到的 **`date` 对象**（不是字符串）放进 `values` 交给 `cursor.execute()` 参数化传入。一定要先 `strip()`（前端传 `?nav_date=%202026-09-30%20` 带空格时，不 strip 会解析失败）。

### 2. `nav_date` 与 `date_from` / `date_to` 的优先级写反

典型错误写法：把 `nav_date` 和 `date_from` 写成两个**平级**的 `if`（`if params["nav_date"] is not None: ...` 然后 `if params["date_from"] is not None: ...`）。

这样写，当 `nav_date=2026-09-15` 且 `date_from=2026-09-20` 时两个条件用 `AND` 拼在一起，得到 `WHERE n.nav_date = '2026-09-15' AND n.nav_date >= '2026-09-20'`，结果恒为空。用户看到的是「查不到数据」，没人会想到是后端两个条件打架了。正确写法是步骤 4 的 `if / else`：`nav_date` 有值时，区间条件根本不生成。

### 3. `Decimal` 直接 `jsonify` 报错

报错原文：`TypeError: Object of type Decimal is not JSON serializable`。`nav` 在 MySQL 里是 `DECIMAL`，PyMySQL 读出来是 `Decimal` 对象，`jsonify()` 不认识它。

**两个要点都要做到**：① 先 `quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)` 定精度——直接 `float(row["nav"])` 也能跑，但返回值的位数取决于库里存了什么，而且绕过了全局的四舍五入约定；② 再用 `float()` 转类型——不转就 500。

不要用 `str()` 转成字符串返回：前端拿到的是 `"1.2345"` 而不是 `1.2345`，做数值比较和图表渲染都要先转换。本项目约定转 `float`。

### 4. JOIN `funds` 表时的列名冲突

`nav_history` 和 `funds` **都有 `id`、`created_at`、`updated_at`**。如果图省事写 `SELECT * FROM nav_history n JOIN funds f ON f.id = n.fund_id`：PyMySQL 用的是 DictCursor（字典游标），字典的键不能重复，**同名列后面的会覆盖前面的**。结果 `row["id"]` 拿到的是 `funds.id`（基金 ID）而不是净值 ID，`row["created_at"]` 拿到的是基金的创建时间。`nav_id` 全错了，而且不报错，只是数字不对——非常难发现。

正确做法：显式列出每一列，并给需要的列起别名（步骤 6 已经这样写了）。注意 `f.name` 必须起别名 `fund_name`——虽然 `nav_history` 表没有 `name` 列不会冲突，但序列化函数里读的是 `row["fund_name"]`，不起别名就是 `KeyError`。

### 5. 另外四条（对照检查即可）

- **`count_sql` 和 `list_sql` 的筛选条件不一致**：只给 `list_sql` 加条件就会出现「`total` 是 10，但翻到第 2 页空了」，两条 SQL 必须共用同一个 `where_sql` 和同一份 `values`。
- **只有一级 `ORDER BY`**：必须写成 `ORDER BY n.nav_date DESC, n.fund_id ASC, n.id DESC`，否则同日多只基金时顺序不稳定，翻页会重复和漏行。
- **忘记关闭数据库连接**：所有数据库操作都要放在 `conn = get_connection()` + `try / finally: conn.close()` 里；不关的话压测几轮就把连接池耗尽。
- **查询接口返回 201，或空数据返回 404**：成功响应统一 HTTP `200`，**包括列表为空的情况**，不要给 `success()` 传 `http_status=201`；`fund_id` 指向不存在的基金时返回空列表 + HTTP `200`，**不返回 404**（筛选类参数查不到就当「没有符合条件的数据」）。

---

## 完成标准

以下条件全部满足，任务 044 才算完成：

- [ ] `GET /api/v1/nav-history` 可用，返回统一 JSON 结构，HTTP 状态码 `200`。
- [ ] 支持 `fund_id`、`nav_date`、`date_from`、`date_to`、`page`、`page_size` 六个参数，全部可选，默认值分别是无、`1`、`20`。
- [ ] 默认排序是 `nav_date` 降序 + 同日 `fund_id` 升序，且 `ORDER BY` 带第三级 `n.id DESC`；`items` 里包含 `nav_id`、`fund_id`、`fund_name`、`fund_code`、`nav_date`、`nav`、`created_at`、`updated_at` 八个字段。
- [ ] `nav_date` 与 `date_from` / `date_to` 同时传时以 `nav_date` 为准，区间条件不生效。
- [ ] `date_from` 晚于 `date_to` 返回 HTTP `400` / `VALIDATION_ERROR`，`details[0].field` 是 `date_from`。
- [ ] 不存在的 `fund_id` 返回空 `items` + `total` 为 `0`、HTTP `200`（不是 404）；`page` 越界返回空 `items` + 真实 `total`，并回显 `page` / `page_size`、HTTP `200`。
- [ ] `nav` 返回 4 位小数，且用了 `ROUND_HALF_UP` 定点化，不是直接 `float()`。
- [ ] 六个参数的非法输入全部返回 `400`，且 `details` 一次性返回全部错误。
- [ ] `pytest tests/test_nav_history.py -q` 全部通过，新增测试不少于 7 个。
- [ ] `pytest -q` 全部通过，没有 failed 也没有 error。
- [ ] 没有新增 `PUT` 或 `DELETE /api/v1/nav-history` 相关路由（第一版不做编辑和删除）。

---

## 完成后请反馈

请把下面命令的输出发给后端协调人：

```bash
sed -n '1,60p' app/routes/nav_history.py
git diff --stat
curl "http://127.0.0.1:5000/api/v1/nav-history?page=1&page_size=5"
curl -i "http://127.0.0.1:5000/api/v1/nav-history?date_from=2026-09-30&date_to=2026-09-01"
curl "http://127.0.0.1:5000/api/v1/nav-history?nav_date=2026-09-15&date_from=2026-09-20&date_to=2026-09-30"
curl "http://127.0.0.1:5000/api/v1/nav-history?page=99&page_size=20"
pytest -q
```

另外请说明：① `nav_history` 表的实际列名（步骤 1 查到的）是否和本文档一致；② 步骤 5 修改 `serialize_nav_history()` 后 `POST /api/v1/nav-history` 的返回有没有变化、026 的测试有没有红；③ 导入 1000 行净值后这个接口的响应时间大概多少秒（`time curl ...` 粗测即可，超过 1 秒请记下来，后续可能要加索引）；④ 有没有发现接口契约草稿（5.3 节）里说不通或没写到的地方。
