# 任务 020：实现新增操作记录接口

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务需要新建操作记录模块、实现 POST 接口、完成三种操作类型的字段校验和日期范围校验、处理外键关联，并注册新的 Blueprint（蓝图）。是第 5 天最重的一个任务。

## 任务目标

实现：

```http
POST /api/v1/operations
```

使用者可以为某个博主、某只基金新增一条操作记录。

支持：

1. `buy` 买入
2. `sell` 卖出
3. `dividend_cash` 现金分红

## 范围说明

本任务只实现新增操作记录。

不包含：

- 查询操作记录（任务 021）
- 删除操作记录（任务 022）
- 编辑操作记录（第一版不做）
- 修改历史操作后的持仓重算
- 手续费、税费、红利再投资
- 超额卖出校验
- 权限校验

## 前置条件

1. 任务 018 已完成，`docs/backend/design/operations-table-design.md` 已产出。
2. 任务 019 已完成，`operations` 表已创建，测试夹具已同步。
3. 任务 009 已完成，项目里已经有 POST JSON 接口写法参考。
4. 数据库里至少存在一个博主和一个基金。

## 实现依据

接口契约在：

```text
docs/api/v1-operations.md
```

第 4 节写了完整的参数说明、成功响应、错误响应和 9 条业务规则。  
**写代码前先通读第 4 节**，本任务的步骤是它的实现指引，不是它的替代品。  
如果发现步骤里的代码和接口文档冲突，以接口文档为准，并把冲突反馈上来。

## 新概念：操作类型白名单

白名单是预先定义好的允许值列表。  
本任务中只允许：

```python
{"buy", "sell", "dividend_cash"}
```

如果请求传入其他类型，后端直接返回参数校验错误。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建操作记录路由文件

**必要性：**  
操作记录是一个新的业务模块，单独放一个文件可以避免路由文件越来越混乱。

新建文件：

```text
backend/app/routes/operations.py
```

先写入基础结构：

```python
from datetime import date, datetime

from flask import Blueprint, request

from app.db import get_connection
from app.utils.responses import error, success


operations_bp = Blueprint("operations", __name__)


ALLOWED_OPERATION_TYPES = {
    "buy",
    "sell",
    "dividend_cash",
}


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


def parse_operation_payload():
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
    operation_type = data.get("operation_type")
    operation_date = data.get("operation_date")
    shares = data.get("shares")
    amount = data.get("amount")
    remark = data.get("remark")

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

    if operation_type not in ALLOWED_OPERATION_TYPES:
        details.append(
            {
                "field": "operation_type",
                "message": "操作类型只允许 buy、sell、dividend_cash"
            }
        )

    parsed_operation_date = None

    if not isinstance(operation_date, str):
        details.append(
            {
                "field": "operation_date",
                "message": "操作日期不能为空"
            }
        )
    else:
        try:
            parsed_operation_date = datetime.strptime(
                operation_date,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            details.append(
                {
                    "field": "operation_date",
                    "message": "操作日期格式必须是 YYYY-MM-DD"
                }
            )

        if parsed_operation_date is not None:
            if parsed_operation_date > date.today():
                details.append(
                    {
                        "field": "operation_date",
                        "message": "操作日期不能晚于今天"
                    }
                )
                parsed_operation_date = None

    if shares is None and operation_type == "dividend_cash":
        parsed_shares = 0.0
    elif not isinstance(shares, (int, float)) or isinstance(shares, bool):
        details.append(
            {
                "field": "shares",
                "message": "份额必须是数字"
            }
        )
        parsed_shares = None
    else:
        parsed_shares = float(shares)

    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        details.append(
            {
                "field": "amount",
                "message": "金额必须是数字"
            }
        )
        parsed_amount = None
    else:
        parsed_amount = float(amount)

    if operation_type == "buy" or operation_type == "sell":
        if parsed_shares is not None and parsed_shares <= 0:
            details.append(
                {
                    "field": "shares",
                    "message": "买入和卖出份额必须大于 0"
                }
            )

        if parsed_amount is not None and parsed_amount <= 0:
            details.append(
                {
                    "field": "amount",
                    "message": "买入和卖出金额必须大于 0"
                }
            )

    if operation_type == "dividend_cash":
        if parsed_shares is not None and parsed_shares != 0:
            details.append(
                {
                    "field": "shares",
                    "message": "现金分红的份额必须等于 0"
                }
            )

        if parsed_amount is not None and parsed_amount <= 0:
            details.append(
                {
                    "field": "amount",
                    "message": "现金分红金额必须大于 0"
                }
            )

    parsed_remark = None

    if remark not in (None, ""):
        if not isinstance(remark, str):
            details.append(
                {
                    "field": "remark",
                    "message": "备注必须是字符串"
                }
            )
        elif len(remark.strip()) > 255:
            details.append(
                {
                    "field": "remark",
                    "message": "备注不能超过 255 个字符"
                }
            )
        else:
            parsed_remark = remark.strip()

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
        "operation_date": parsed_operation_date,
        "shares": parsed_shares,
        "amount": parsed_amount,
        "remark": parsed_remark
    }, None
```

几个容易看漏的点：

- `from datetime import date, datetime`：`date.today()` 用来判断操作日期有没有填到未来。填未来日期的操作在业务上不成立，而且会让后面算持仓快照时出现「今天的持仓包含了明天的买入」这种怪事。
- 日期检查不通过时把 `parsed_operation_date` 重新设回 `None`，是为了防止校验失败的值被后面的代码误用。
- `shares` 那一段：`dividend_cash` 允许**不传** `shares`，此时后端自己补 `0.0`。如果传了，仍然必须等于 `0`（这条规则在下面 `if operation_type == "dividend_cash"` 那段里）。`buy` 和 `sell` 必须传。
- 注意 `isinstance(x, bool)` 的判断：Python 里 `True` 也是 `int`，`isinstance(True, int)` 返回 `True`。如果不排除，`{"shares": true}` 会被当成 `1.0` 收下。
- 所有校验错误都收集到 `details` 列表里一次返回，不要发现第一个错就 `return`。前端需要一次性看到所有问题。

---

### 步骤 2：新增序列化函数

**必要性：**  
数据库返回的日期、小数不能直接给 JSON。需要一个统一函数把数据库行转换成前端可用的字典。

在 `operations.py` 中继续添加：

```python
def serialize_operation(row):
    operation_date = row["operation_date"]
    created_at = row["created_at"]
    updated_at = row["updated_at"]

    return {
        "operation_id": row["id"],
        "blogger_id": row["blogger_id"],
        "blogger_name": row["blogger_name"],
        "fund_id": row["fund_id"],
        "fund_name": row["fund_name"],
        "fund_code": row["fund_code"],
        "operation_type": row["operation_type"],
        "operation_date": operation_date.strftime("%Y-%m-%d"),
        "shares": float(row["shares"]),
        "amount": float(row["amount"]),
        "remark": row["remark"],
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": updated_at.strftime("%Y-%m-%d %H:%M:%S"),
    }
```

---

### 步骤 3：新增数据库查询辅助函数

**必要性：**  
新增操作记录前必须确认博主和基金存在，否则数据库外键会报原始错误，前端无法理解。

在 `operations.py` 中继续添加：

```python
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


def fetch_operation_by_id(cursor, operation_id):
    cursor.execute(
        """
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
        WHERE o.id = %s
        """,
        (operation_id,)
    )
    row = cursor.fetchone()

    if row is None:
        return None

    return serialize_operation(row)


def fetch_initial_position_date(cursor, blogger_id, fund_id):
    cursor.execute(
        """
        SELECT MIN(record_date) AS first_record_date
        FROM initial_positions
        WHERE blogger_id = %s AND fund_id = %s
        """,
        (blogger_id, fund_id)
    )
    row = cursor.fetchone()

    if row is None:
        return None

    return row["first_record_date"]
```

说明 `fetch_initial_position_date()`：

初始持仓记录的是「开始观察时这个博主持有多少」。在它之前发生的操作不该录进来——那些操作的结果已经包含在初始持仓的份额和成本里了，再录一遍会重复计算。  
所以这个函数用来查出该博主该基金最早的初始持仓日期，作为操作日期的下界。

`MIN()` 是 SQL 聚合函数，取最小值。用它是因为同一个博主同一只基金可能有多条不同日期的初始持仓记录（`initial_positions` 的唯一约束是博主 + 基金 + 记录日期三个字段）。

注意：`SELECT MIN(...)` 在没有任何匹配行时**不会**返回空结果，而是返回一行、值为 `NULL`。所以这个函数可能返回 `None`，调用方要判空——没有初始持仓就不限制下界。

---

### 步骤 4：新增 POST 路由

**必要性：**  
这是本任务的核心接口。先校验参数，再检查关联数据，最后插入数据库。

在 `operations.py` 末尾添加：

```python
@operations_bp.post("/api/v1/operations")
def create_operation():
    payload, error_response = parse_operation_payload()

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

            first_record_date = fetch_initial_position_date(
                cursor,
                payload["blogger_id"],
                payload["fund_id"]
            )

            if first_record_date is not None:
                if payload["operation_date"] < first_record_date:
                    return error(
                        code="VALIDATION_ERROR",
                        message="参数校验失败",
                        details=[
                            {
                                "field": "operation_date",
                                "message": (
                                    "操作日期不能早于初始持仓记录日期 "
                                    f"{first_record_date.strftime('%Y-%m-%d')}"
                                )
                            }
                        ],
                        http_status=400
                    )

            cursor.execute(
                """
                INSERT INTO operations (
                    blogger_id,
                    fund_id,
                    operation_type,
                    operation_date,
                    shares,
                    amount,
                    remark
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    payload["blogger_id"],
                    payload["fund_id"],
                    payload["operation_type"],
                    payload["operation_date"],
                    payload["shares"],
                    payload["amount"],
                    payload["remark"]
                )
            )
            operation_id = cursor.lastrowid
            conn.commit()

            data = fetch_operation_by_id(cursor, operation_id)
    finally:
        conn.close()

    return success(data=data)
```

说明这个路由的检查顺序，顺序不能随便调：

1. 先做**不需要数据库**的参数校验（`parse_operation_payload`）。格式都不对就没必要连库。
2. 再查博主和基金是否存在。这两个不存在，日期校验也没有意义。
3. 最后查初始持仓日期，做日期下界校验。这一步依赖前两步的结果。
4. 都通过了才 `INSERT`。

注意 `success(data=data)` 没有 `http_status` 参数。本项目所有成功响应统一返回 `200`，新增接口也一样，不要写 `success(data=data, http_status=201)`——`success()` 函数没有这个参数，会直接报 `TypeError`。

---

### 步骤 5：注册操作记录 Blueprint

**必要性：**  
Flask 只有注册 Blueprint 后，才能访问这个模块里的路由。

修改文件：

```text
backend/app/__init__.py
```

增加导入：

```python
from app.routes.operations import operations_bp
```

在 `create_app()` 中注册：

```python
app.register_blueprint(operations_bp)
```

完整示例：

```python
from flask import Flask

from app.routes.health import health_bp
from app.routes.bloggers import bloggers_bp
from app.routes.funds import funds_bp
from app.routes.initial_positions import initial_positions_bp
from app.routes.operations import operations_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(health_bp)
    app.register_blueprint(bloggers_bp)
    app.register_blueprint(funds_bp)
    app.register_blueprint(initial_positions_bp)
    app.register_blueprint(operations_bp)

    return app
```

---

### 步骤 6：重启 Flask 服务

**必要性：**  
新增文件和注册路由后必须重启，确认没有语法错误。

```bash
python run.py
```

## 验证方式

### 1. 新增买入记录

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"operation_type":"buy","operation_date":"2026-09-30","shares":1000,"amount":13000,"remark":"第一次买入"}'
```

预期返回 `code: 0`，并包含 `operation_id`、`blogger_name`、`fund_name`、`fund_code`。

### 2. 新增卖出记录

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"operation_type":"sell","operation_date":"2026-09-30","shares":300,"amount":4200,"remark":"部分卖出"}'
```

预期返回 `code: 0`。

### 3. 新增现金分红记录

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"operation_type":"dividend_cash","operation_date":"2026-09-30","shares":0,"amount":120,"remark":"现金分红"}'
```

预期返回 `code: 0`。

### 4. 新增现金分红记录，不传 shares

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"operation_type":"dividend_cash","operation_date":"2026-09-30","amount":88,"remark":"不传份额的分红"}'
```

预期返回 `code: 0`，并且响应里 `shares` 是 `0.0`。  
这一条必须测，它是现金分红和买卖在参数上唯一的区别。

### 5. 验证非法操作类型

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"operation_type":"transfer","operation_date":"2026-09-30","shares":100,"amount":1300}'
```

预期返回 `VALIDATION_ERROR`，HTTP 状态码是 `400`。

### 6. 验证现金分红 shares 不为 0

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"operation_type":"dividend_cash","operation_date":"2026-09-30","shares":100,"amount":120}'
```

预期返回 `VALIDATION_ERROR`。

### 7. 验证买入不传 shares

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"operation_type":"buy","operation_date":"2026-09-30","amount":1300}'
```

预期返回 `VALIDATION_ERROR`。  
「可以不传」只对 `dividend_cash` 成立，不要放宽到买卖。

### 8. 验证未来日期

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"operation_type":"buy","operation_date":"2099-01-01","shares":100,"amount":1300}'
```

预期返回 `VALIDATION_ERROR`，`details` 里能看到「操作日期不能晚于今天」。

### 9. 验证早于初始持仓日期

先确认博主 1、基金 1 有初始持仓，并记下它的 `record_date`。然后用一个更早的日期：

```bash
curl "http://127.0.0.1:5000/api/v1/initial-positions?blogger_id=1&fund_id=1"

curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"operation_type":"buy","operation_date":"2000-01-01","shares":100,"amount":1300}'
```

预期返回 `VALIDATION_ERROR`，`details` 的 message 里包含那个初始持仓日期。

如果博主 1、基金 1 **没有**初始持仓记录，这条会返回 `code: 0`——这是正确行为，没有初始持仓就不限制下界。这种情况下请换一组有初始持仓的博主和基金再测一次。

### 10. 验证博主不存在

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":999999,"fund_id":1,"operation_type":"buy","operation_date":"2026-09-30","shares":1000,"amount":13000}'
```

预期返回 `BLOGGER_NOT_FOUND`，HTTP 状态码是 `404`。

### 11. 验证基金不存在

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":999999,"operation_type":"buy","operation_date":"2026-09-30","shares":1000,"amount":13000}'
```

预期返回 `FUND_NOT_FOUND`，HTTP 状态码是 `404`。

## 常见坑

### 1. 忘记注册 Blueprint

如果访问 `/api/v1/operations` 返回 HTML `404`，通常是 `operations_bp` 没有注册。

检查命令：

```bash
grep -n "operations_bp" app/__init__.py
```

### 2. 忘记校验 operation_type

不要允许任意字符串进入数据库。  
必须使用 `ALLOWED_OPERATION_TYPES` 白名单。

### 3. 现金分红允许 shares 大于 0

现金分红不改变份额。  
如果 `operation_type` 是 `dividend_cash`，`shares` 要么不传（后端补 0），要么必须等于 `0`。

### 4. 把「dividend_cash 可以不传 shares」放宽到所有类型

只有 `dividend_cash` 能省略 `shares`。  
如果写成「`shares` 缺失就统一补 0」，那么买入不传份额也会被收下，库里会出现「花了 13000 买到 0 份」的记录，后面算持仓和收益全是错的。

判断条件里必须同时看 `shares is None` 和 `operation_type == "dividend_cash"`。

### 5. 忘记检查博主和基金是否存在

虽然数据库外键会拦截，但业务接口应该返回：

```text
BLOGGER_NOT_FOUND
FUND_NOT_FOUND
```

不要把数据库原始错误直接抛给前端。

### 6. 忘记 `conn.commit()`

如果没有提交，`cursor.lastrowid` 可能返回了 ID，但数据库里没有这条记录。

### 7. 日期格式不统一

后端数据库保存 `DATE`，前端展示使用 `YYYY-MM-DD` 字符串。  
必须在序列化时格式化。

### 8. 用字符串比较日期

日期下界校验里，`payload["operation_date"]` 和 `first_record_date` 都是 Python 的 `date` 对象，可以直接用 `<` 比较。

不要写成：

```python
if str(payload["operation_date"]) < str(first_record_date):
```

`YYYY-MM-DD` 这种格式按字符串比大小碰巧是对的，但一旦有人改成别的格式就会悄悄出错。有 `date` 对象就用 `date` 对象比。

### 9. 用 `float` 处理金额

本任务的 `parse_operation_payload()` 用 `float()` 转换，这是当前项目的简化做法，够用。  
但不要在这基础上做金额累加运算——累加会有精度误差。以后做收益汇总时要改用 `Decimal`，这一项已记在 `docs/backend/plans/backend-task-backlog.md` 里。

### 10. 给 `success()` 传 `http_status`

```python
return success(data=data, http_status=201)
```

会直接报：

```text
TypeError: success() got an unexpected keyword argument 'http_status'
```

本项目成功响应统一 `200`。正确写法是 `return success(data=data)`。

## 完成标准

以下条件全部满足，任务 020 才算完成：

1. `backend/app/routes/operations.py` 存在。
2. `operations_bp` 已在 `app/__init__.py` 注册。
3. `POST /api/v1/operations` 可以新增 `buy`、`sell`、`dividend_cash`。
4. `dividend_cash` 不传 `shares` 时能成功，且入库值是 `0`。
5. `buy` 和 `sell` 不传 `shares` 时返回 `400`。
6. `dividend_cash` 传了非 `0` 的 `shares` 时返回 `400`。
7. 非法操作类型返回 `400`。
8. 操作日期晚于今天返回 `400`。
9. 操作日期早于该博主该基金的初始持仓日期返回 `400`；没有初始持仓时不限制。
10. 博主或基金不存在时返回对应 `404`。
11. 所有响应都是统一 JSON 结构，成功时 HTTP 状态码是 `200`。
12. 响应字段和 `docs/api/v1-operations.md` 第 3 节一致。
13. 重启服务后功能仍然正常。

## 完成后请反馈

1. 新增和修改的文件列表。
2. 上面 11 条验证的逐条结果（贴 curl 命令和响应）。
3. 响应字段是否和 `docs/api/v1-operations.md` 第 3 节完全一致。
4. 有没有发现接口文档里说不通或没写清的地方。
5. 遇到的问题和未完成项。
