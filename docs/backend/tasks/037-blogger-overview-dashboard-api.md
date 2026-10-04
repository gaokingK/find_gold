# 任务 037：博主总览看板接口

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务要新建看板路由文件、复用第 8 天的持仓快照和收益计算逻辑，并按博主维度输出汇总。没有新表、新依赖和复杂 SQL，但需要处理空数据和缺净值的返回口径。

## 任务目标

创建：

```text
backend/app/routes/dashboards.py
```

修改：

```text
backend/app/__init__.py
```

完成后可以：

1. 访问 `GET /api/v1/dashboards/bloggers`。
2. 按可选参数 `return_date` 汇总博主收益，不传时默认今天。
3. 返回有持仓收益数据的博主数量。
4. 返回「博主 + 基金」组合的持仓数量。
5. 返回总成本、总市值、总收益金额、总收益率。
6. 返回按博主拆分的看板明细。
7. `pytest -q` 仍然全部通过。

## 范围说明

本任务只实现博主总览看板接口。

不包含：

- 基金分布看板
- 近期操作统计
- 分页
- 图表专用格式
- 缓存
- 定时预计算
- 登录和权限

## 前置条件

1. 任务 033–036 已完成，收益计算和收益接口可用。
2. `pytest -q` 当前全部通过。
3. 已阅读 `docs/api/v1-dashboards.md` 中「博主总览看板」部分。

## 新概念说明

### Dashboard（看板）

Dashboard 是给前端总览页面一次性使用的汇总数据接口。  
它通常不直接展示所有原始记录，而是先在后端按业务维度汇总。

### Helper（辅助函数）

Helper 是把一段会重复使用的逻辑封装成函数。  
本任务把「读取某个博主持仓、查净值、算收益」封装成 `_load_blogger_return_items()`，后面基金分布看板也能复用。

### 和 `/returns/summary` 的关系

本接口和任务 036 的 `GET /api/v1/returns/summary` 是**同一份数据的两种视图**：

| 项目 | `/returns/summary` | `/dashboards/bloggers` |
| --- | --- | --- |
| 用途 | 收益页面，需要下钻到每只基金 | 总览页面，只要博主级卡片 |
| 每个博主的明细 | 有 `funds` 数组 | **没有**，只有 `fund_count` |
| 额外字段 | — | `position_count` |

所以本任务必须复用同一套计算函数（`calculate_position_snapshots()` + `calculate_position_returns()` + `calculate_total_returns()`），只是输出结构不同。  
**不要为看板另写一套收益算法。** 否则两个接口会给出不一样的收益率，前端会先发现，然后没人说得清哪个对。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建看板路由文件

**必要性：**  
看板是新模块。单独建文件可以避免 `returns.py` 继续变大。

新建文件：

```text
backend/app/routes/dashboards.py
```

先写入基础结构：

```python
from datetime import date

from flask import Blueprint, request

from app.db import get_connection
from app.services.position_snapshot import calculate_position_snapshots
from app.services.return_calculation import (
    calculate_position_returns,
    calculate_total_returns,
)
from app.utils.responses import error, success
from app.utils.snapshot_data import (
    get_initial_positions,
    get_nav_on_date_map,
    get_operations,
    parse_snapshot_date,
)


dashboards_bp = Blueprint("dashboards", __name__)


def _to_number(value, places):
    if value is None:
        return None

    return round(float(value), places)
```

说明：

- `Blueprint（蓝图）` 用来组织看板相关路由。
- `_to_number()` 把 `Decimal` 转成 JSON 友好的数字，并控制小数位。

---

### 步骤 2：添加博主收益数据加载函数

**必要性：**  
博主总览和后面的基金分布都需要「某个博主持仓快照 + 当天净值 + 收益明细」。提前封装，避免复制相同逻辑。

继续添加：

```python
def _load_blogger_return_items(cursor, blogger, return_date):
    initial_positions = get_initial_positions(
        cursor,
        blogger["id"],
        return_date
    )
    operations = get_operations(
        cursor,
        blogger["id"],
        return_date
    )
    position_items = calculate_position_snapshots(
        initial_positions,
        operations
    )

    if not position_items:
        return []

    fund_ids = [item["fund_id"] for item in position_items]
    nav_map = get_nav_on_date_map(
        cursor,
        fund_ids,
        return_date
    )

    return calculate_position_returns(
        position_items,
        nav_map
    )
```

说明：

- 这个函数返回的是某博主按基金拆分的收益明细。
- 如果没有持仓快照，直接返回空列表。
- `get_nav_on_date_map()` 只查指定日期当天的净值，不做最近日期兜底。

---

### 步骤 3：实现博主总览看板路由

**必要性：**  
这一步把所有博主的收益明细逐个算出，再汇总成前端总览页面需要的结构。

继续添加：

```python
@dashboards_bp.get("/api/v1/dashboards/bloggers")
def get_blogger_overview_dashboard():
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

            all_return_items = []
            blogger_items = []

            for blogger in bloggers:
                return_items = _load_blogger_return_items(
                    cursor,
                    blogger,
                    return_date
                )

                if not return_items:
                    continue

                blogger_summary = calculate_total_returns(return_items)

                all_return_items.extend(return_items)
                blogger_items.append(
                    {
                        "blogger_id": blogger["id"],
                        "blogger_name": blogger["name"],
                        "fund_count": len(return_items),
                        "total_cost_amount": _to_number(
                            blogger_summary["total_cost_amount"],
                            2
                        ),
                        "total_market_value": _to_number(
                            blogger_summary["total_market_value"],
                            2
                        ),
                        "profit_amount": _to_number(
                            blogger_summary["profit_amount"],
                            2
                        ),
                        "return_rate": _to_number(
                            blogger_summary["return_rate"],
                            6
                        )
                    }
                )

            total_summary = calculate_total_returns(all_return_items)
            position_count = len(all_return_items)
    finally:
        conn.close()

    return success(
        data={
            "return_date": return_date.strftime("%Y-%m-%d"),
            "blogger_count": len(blogger_items),
            "position_count": position_count,
            "total_cost_amount": _to_number(
                total_summary["total_cost_amount"],
                2
            ),
            "total_market_value": _to_number(
                total_summary["total_market_value"],
                2
            ),
            "profit_amount": _to_number(
                total_summary["profit_amount"],
                2
            ),
            "return_rate": _to_number(
                total_summary["return_rate"],
                6
            ),
            "items": blogger_items
        }
    )
```

说明：

- `list.extend()` 会把另一个列表里的元素逐个加入当前列表。
- `all_return_items` 里每个元素就是一条「博主 + 基金」明细，所以 `position_count` 直接取 `len(all_return_items)`，不需要再额外维护一个列表来统计。
- 没有持仓数据的博主不进入 `items`，也不计入 `blogger_count`。
- `calculate_total_returns(all_return_items)` 在列表为空时也能正常返回（总成本 `0`、总市值 `0`、收益率 `None`），不需要额外判空。

---

### 步骤 4：注册看板 Blueprint

**必要性：**  
Flask 只有注册 Blueprint 后，才能访问新路由。

修改文件：

```text
backend/app/__init__.py
```

增加导入：

```python
from app.routes.dashboards import dashboards_bp
```

在 `create_app()` 中注册：

```python
app.register_blueprint(dashboards_bp)
```

---

### 步骤 5：语法检查

**必要性：**  
先确认新文件没有语法错误，再启动服务。

执行：

```bash
python -m py_compile app/routes/dashboards.py
python -m py_compile app/__init__.py
```

预期没有输出，并且退出码是 `0`。

---

### 步骤 6：启动服务并手动验证

**必要性：**  
看板接口涉及多表读取和多博主循环，必须实际请求一次。

启动服务：

```bash
python run.py
```

另开一个终端，在 `backend` 目录执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/bloggers?return_date=2026-09-30"
```

预期返回 HTTP `200`，响应结构符合 `docs/api/v1-dashboards.md`。

---

### 步骤 7：运行已有测试

**必要性：**  
确认新看板模块没有破坏已有功能。

停止服务后，在 `backend` 目录执行：

```bash
pytest -q
```

预期全部通过。

## 验证方式

### 1. 语法检查

```bash
python -m py_compile app/routes/dashboards.py
python -m py_compile app/__init__.py
```

预期没有输出。

### 2. 成功请求

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/bloggers?return_date=2026-09-30"
```

预期 HTTP `200`，字段和接口文档一致。

### 3. 不传日期

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/bloggers"
```

预期 HTTP `200`，`return_date` 是今天。

### 4. 空数据场景

在测试环境清空基础数据后请求：

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/bloggers?return_date=2026-09-30"
```

预期 HTTP `200`，`blogger_count` 是 `0`，`position_count` 是 `0`，`items` 是 `[]`，总收益率是 `null`。

### 5. 错误场景

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/bloggers?return_date=bad-date"
curl -i "http://127.0.0.1:5000/api/v1/dashboards/bloggers?return_date=2999-12-31"
```

预期都返回 HTTP `400 VALIDATION_ERROR`。

### 6. 已有测试

```bash
pytest -q
```

预期全部通过。

## 常见坑

### 1. 把没有持仓的博主也计入数量

`blogger_count` 表示有持仓收益数据的博主数量。  
没有持仓数据的博主不要进入 `items`。

### 2. 用博主数量当作持仓数量

`position_count` 是「博主 + 基金」组合数量。  
一个博主持有 2 只基金，即使只算 1 个博主，`position_count` 也应该是 2。

### 3. 使用最近一天净值兜底

看板收益必须使用指定日期当天的净值。  
不要使用 `get_latest_nav_map()`。

### 4. 忘记注册 Blueprint

只在 `dashboards.py` 里定义路由还不够。  
必须在 `app/__init__.py` 中注册 `dashboards_bp`。

## 完成标准

以下条件全部满足，任务 037 才算完成：

1. `GET /api/v1/dashboards/bloggers` 可访问。
2. `return_date` 可选，默认今天。
3. 响应字段和 `docs/api/v1-dashboards.md` 一致。
4. 空数据时返回 `200`，不抛异常。
5. 缺净值时相关汇总字段返回 `null`。
6. `pytest -q` 全部通过。

## 完成后请反馈

1. 新增和修改的文件列表。
2. 语法检查输出。
3. 成功请求的完整响应 JSON。
4. 空数据、缺净值和错误场景的响应 JSON。
5. `pytest -q` 的完整输出。
6. 遇到的问题和未完成项。
