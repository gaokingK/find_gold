# 任务 038：基金分布看板接口

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务复用任务 037 的博主收益明细，但要把「按博主汇总」改为「按基金跨博主汇总」。主要工作是分组、占比计算和缺净值边界处理。

## 任务目标

修改：

```text
backend/app/routes/dashboards.py
```

完成后可以：

1. 访问 `GET /api/v1/dashboards/funds`。
2. 按可选参数 `return_date` 汇总基金分布，不传时默认今天。
3. 返回有持仓数据的基金数量。
4. 返回所有基金总成本和总市值。
5. 返回每只基金的份额、成本、净值、市值、成本占比、市值占比。
6. 缺当天净值的基金，自己的市值和市值占比返回 `null`；有净值的基金照实返回自己的市值。
7. 只要有一只基金缺当天净值，总市值和所有市值占比返回 `null`。
8. `pytest -q` 仍然全部通过。

## 范围说明

本任务只实现基金分布看板接口。

不包含：

- 分页
- 指定基金过滤
- 博主维度下钻
- 收益金额和收益率
- 图表专用格式
- 缓存
- 定时预计算

## 前置条件

1. 任务 037 已完成，`dashboards_bp` 和 `_load_blogger_return_items()` 可用。
2. `pytest -q` 当前全部通过。
3. 已阅读 `docs/api/v1-dashboards.md` 中「基金分布看板」部分。

## 新概念说明

### Grouping（分组）

Grouping 是把同一类数据合成一组。  
本任务把多个博主持有的同一只基金数据按 `fund_id` 分组合计。

### `set()`

`set()` 是不重复元素的集合。  
本任务用它记录持有某只基金的博主 ID，重复添加同一个博主 ID 也只会保留一个，从而计算 `blogger_count`。

### `sorted()`

`sorted()` 用于排序。  
本任务按每只基金的成本金额从高到低排序。

## 执行目录

```bash
cd /d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：补充 Decimal 工具

**必要性：**  
成本、份额、市值和占比要做合计和除法，必须使用 `Decimal`，不能使用 `float`。

打开：

```text
backend/app/routes/dashboards.py
```

在文件顶部导入区增加：

```python
from decimal import Decimal
```

在 `dashboards_bp = Blueprint("dashboards", __name__)` 后添加：

```python
ZERO = Decimal("0")


def _to_decimal(value):
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))
```

说明：

- `isinstance()` 用来判断一个值是不是指定类型。
- `_to_decimal()` 把数据库或 Service 层返回的数字统一转成 `Decimal`。

---

### 步骤 2：添加基金分布路由

**必要性：**  
基金分布需要跨博主聚合同一只基金的数据，这是看板前端展示持仓结构的核心接口。

在 `backend/app/routes/dashboards.py` 末尾添加：

```python
@dashboards_bp.get("/api/v1/dashboards/funds")
def get_fund_distribution_dashboard():
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
                "SELECT id, name FROM bloggers ORDER BY id"
            )
            bloggers = cursor.fetchall()
            fund_groups = {}

            for blogger in bloggers:
                return_items = _load_blogger_return_items(
                    cursor,
                    blogger,
                    return_date
                )

                for item in return_items:
                    fund_id = item["fund_id"]

                    if fund_id not in fund_groups:
                        fund_groups[fund_id] = {
                            "fund_id": fund_id,
                            "fund_name": item["fund_name"],
                            "fund_code": item["fund_code"],
                            "blogger_ids": set(),
                            "shares": ZERO,
                            "cost_amount": ZERO,
                            "nav": item["nav"],
                            "nav_date": item["nav_date"],
                            "market_value": ZERO,
                            "has_missing_nav": False,
                        }

                    group = fund_groups[fund_id]
                    group["blogger_ids"].add(blogger["id"])
                    group["shares"] += _to_decimal(item["shares"])
                    group["cost_amount"] += _to_decimal(item["cost_amount"])

                    if item["market_value"] is None:
                        group["has_missing_nav"] = True
                    else:
                        group["market_value"] += _to_decimal(
                            item["market_value"]
                        )

                        if group["nav"] is None:
                            group["nav"] = item["nav"]
                            group["nav_date"] = item["nav_date"]
    finally:
        conn.close()

    total_cost_amount = sum(
        (group["cost_amount"] for group in fund_groups.values()),
        ZERO
    )

    if any(group["has_missing_nav"] for group in fund_groups.values()):
        total_market_value = None
    else:
        total_market_value = sum(
            (group["market_value"] for group in fund_groups.values()),
            ZERO
        )

    fund_items = []

    for group in sorted(
        fund_groups.values(),
        key=lambda group: group["cost_amount"],
        reverse=True
    ):
        if total_cost_amount > ZERO:
            cost_ratio = group["cost_amount"] / total_cost_amount
        else:
            cost_ratio = None

        if group["has_missing_nav"]:
            market_value = None
        else:
            market_value = group["market_value"]

        if (
            market_value is None
            or total_market_value is None
            or total_market_value <= ZERO
        ):
            market_value_ratio = None
        else:
            market_value_ratio = market_value / total_market_value

        nav_date = group["nav_date"]

        fund_items.append(
            {
                "fund_id": group["fund_id"],
                "fund_name": group["fund_name"],
                "fund_code": group["fund_code"],
                "blogger_count": len(group["blogger_ids"]),
                "shares": _to_number(group["shares"], 4),
                "cost_amount": _to_number(group["cost_amount"], 2),
                "nav": _to_number(group["nav"], 4),
                "nav_date": (
                    nav_date.strftime("%Y-%m-%d")
                    if nav_date is not None
                    else None
                ),
                "market_value": _to_number(market_value, 2),
                "cost_ratio": _to_number(cost_ratio, 6),
                "market_value_ratio": _to_number(market_value_ratio, 6)
            }
        )

    return success(
        data={
            "return_date": return_date.strftime("%Y-%m-%d"),
            "fund_count": len(fund_items),
            "total_cost_amount": _to_number(total_cost_amount, 2),
            "total_market_value": _to_number(total_market_value, 2),
            "items": fund_items
        }
    )
```

说明：

- `dict.values()` 返回字典里的所有值，这里用于遍历所有基金分组。
- `any()` 表示只要有一个条件成立就返回 `True`。
- **缺净值不能直接把 `group["market_value"]` 改成 `None`。** 用一个单独的 `has_missing_nav` 标记记录「这只基金缺净值」，`market_value` 始终保持 `Decimal` 累加，最后输出时再根据标记决定返回累加值还是 `null`。原因见「常见坑」第 1 条。
- 缺净值的基金自己的 `market_value` 和 `market_value_ratio` 返回 `null`；有净值的基金照实返回自己的市值。
- 只要有任意一只基金缺净值，**总市值** `total_market_value` 和所有 `market_value_ratio` 返回 `null`——占比的分母不可信，算出来会误导前端。
- 成本不依赖净值，所以缺净值时仍然返回成本和成本占比。
- 初始化分组时 `nav` / `nav_date` 先取第一个贡献者的值；如果第一个贡献者缺净值（`nav` 是 `None`），后面遇到有净值的贡献者时补上。同一只基金同一天的净值只有一条，所以不会冲突。

---

### 步骤 3：语法检查

**必要性：**  
先确认修改后的看板路由没有语法错误，再启动服务。

执行：

```bash
python -m py_compile app/routes/dashboards.py
```

预期没有输出，并且退出码是 `0`。

---

### 步骤 4：启动服务并手动验证

**必要性：**  
基金分布跨多个博主和基金，必须实际请求一次，确认分组和占比正确。

启动服务：

```bash
python run.py
```

另开一个终端，在 `backend` 目录执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/funds?return_date=2026-09-30"
```

预期返回 HTTP `200`，响应结构符合 `docs/api/v1-dashboards.md`。

---

### 步骤 5：运行已有测试

**必要性：**  
确认新接口没有破坏已有看板和其他模块。

停止服务后，在 `backend` 目录执行：

```bash
pytest -q
```

预期全部通过。

## 验证方式

### 1. 语法检查

```bash
python -m py_compile app/routes/dashboards.py
```

预期没有输出。

### 2. 成功请求

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/funds?return_date=2026-09-30"
```

预期 HTTP `200`，字段和接口文档一致。

### 3. 不传日期

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/funds"
```

预期 HTTP `200`，`return_date` 是今天。

### 4. 缺净值场景

先准备一组数据：**同一只基金被两个博主持有，且该基金当天没有净值**，另一只基金当天有净值。  
特别要试一次「缺净值的那个博主在 `ORDER BY id` 里排在前面」的情况，这是「常见坑」第 1 条那个 `TypeError` 的触发条件。

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/funds?return_date=2026-09-29"
```

预期 HTTP `200`，**不是** `500`。并且：

- 缺净值的基金：`nav`、`nav_date`、`market_value`、`market_value_ratio` 都是 `null`。
- 有净值的基金：`market_value` 照实返回，`market_value_ratio` 是 `null`。
- 所有基金的 `cost_amount` 和 `cost_ratio` 都照实返回。
- `total_market_value` 是 `null`。

### 5. 空数据场景

**不要清空开发库 `fund_db`。** 换一个没有任何持仓的早期日期请求即可：

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/funds?return_date=2020-01-01"
```

预期 HTTP `200`，`fund_count` 是 `0`，`items` 是 `[]`，总成本和总市值是 `0`，占比字段不出现（`items` 为空）。

如果确实需要一个完全空的数据库来验证，只能连测试库 `fund_test_db`，不能动 `fund_db`。

### 6. 错误场景

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/funds?return_date=bad-date"
curl -i "http://127.0.0.1:5000/api/v1/dashboards/funds?return_date=2999-12-31"
```

预期都返回 HTTP `400 VALIDATION_ERROR`。

### 7. 已有测试

```bash
pytest -q
```

预期全部通过。

## 常见坑

### 1. 把 `group["market_value"]` 直接赋成 `None`

这是本任务最容易写出的崩溃代码：

```python
                    if item["market_value"] is None:
                        group["has_missing_nav"] = True
                        group["market_value"] = None          # 错误
                    else:
                        group["market_value"] += _to_decimal(
                            item["market_value"]
                        )
```

同一只基金可能被多个博主持有。假设博主 A 缺净值、博主 B 有净值，而循环先处理 A：

1. 处理 A 时把 `group["market_value"]` 置成 `None`。
2. 处理 B 时执行 `None += Decimal(...)`，直接抛：

```text
TypeError: unsupported operand type(s) for +=: 'NoneType' and 'decimal.Decimal'
```

接口返回 `500`。而且这个 bug 只在「缺净值的博主排在前面」时才触发，换个博主顺序就复现不了，非常难查。

正确做法：`market_value` 只做 `Decimal` 累加，缺净值单独用 `has_missing_nav` 标记，输出时再决定返回累加值还是 `null`。

同理，`any()` 判断总市值时要看 `group["has_missing_nav"]`，不要看 `group["market_value"] is None`。

### 2. 缺净值的基金把有净值的基金也拖成 null

口径要分清楚，和 `docs/api/v1-returns.md` 保持一致：

| 字段 | 基金 A 缺净值 | 基金 B 有净值 |
| --- | --- | --- |
| `market_value` | `null` | 照实返回 |
| `market_value_ratio` | `null` | `null`（分母不可信） |
| `cost_amount` | 照实返回 | 照实返回 |
| `cost_ratio` | 照实返回 | 照实返回 |
| `total_market_value` | `null` | — |

也就是说：**每只基金的市值只看自己有没有净值；总市值和所有占比只要有一只缺就是 `null`。**

不要因为基金 A 缺净值，就把基金 B 的 `market_value` 也抹成 `null`——前端会以为 B 也没数据。

### 3. 用 float 计算占比

成本、市值、占比都要使用 `Decimal`。  
使用 `float` 会出现精度误差，多个基金占比加起来可能不是 `1`。

### 4. 重复统计同一只基金

同一只基金可能被多个博主持有。  
必须按 `fund_id` 分组后再汇总，不能简单把所有收益明细顺序相加后当作单基金结果。

### 5. 忽略成本为 0 的场景

总成本为 `0` 时，成本占比要返回 `null`。  
不能执行除法，否则会抛除零错误。

## 完成标准

以下条件全部满足，任务 038 才算完成：

1. `GET /api/v1/dashboards/funds` 可访问。
2. `return_date` 可选，默认今天。
3. 响应字段和 `docs/api/v1-dashboards.md` 一致。
4. 基金按成本金额从高到低排序。
5. 空数据时返回 `200`，不抛异常。
6. 缺净值的基金自己的 `market_value` 和 `market_value_ratio` 是 `null`；有净值的基金 `market_value` 照实返回。
7. 只要有一只基金缺净值，`total_market_value` 和所有 `market_value_ratio` 都是 `null`。
8. 「同一只基金、缺净值的博主排在前面、另一个博主有净值」这个场景不会返回 `500`。
9. `pytest -q` 全部通过。

## 完成后请反馈

1. 修改的文件列表。
2. 语法检查输出。
3. 成功请求的完整响应 JSON。
4. 缺净值、空数据和错误场景的响应 JSON。
5. `pytest -q` 的完整输出。
6. 遇到的问题和未完成项。
