# 任务 036：总体收益汇总接口

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务复用单博主持仓快照和收益计算逻辑，但要循环处理多个博主、逐层汇总并序列化。数据量不大，第一版可以接受简单循环查询；主要复杂点是空数据和缺净值时的汇总口径。

## 任务目标

修改：

```text
backend/app/routes/returns.py
```

完成后可以：

1. 访问 `GET /api/v1/returns/summary`。
2. 按可选参数 `return_date` 计算全部博主持仓收益，不传时默认今天。
3. 返回总成本、总市值、总收益金额、总收益率。
4. 返回有持仓收益数据的博主数量。
5. 返回按博主拆分的汇总和按基金拆分的明细。
6. `pytest -q` 仍然全部通过。

## 范围说明

本任务只实现总体收益汇总接口。

不包含：

- 分页
- 指定博主列表过滤
- 基金维度汇总
- 图表数据结构
- 缓存
- 定时计算
- 最近一天净值兜底
- 最大回撤、年化收益、夏普比率

## 前置条件

1. 任务 034 已完成，`returns.py` 里有单博主收益查询和序列化函数。
2. 任务 035 已完成，单基金收益查询可用。
3. `pytest -q` 当前全部通过。
4. 已阅读 `docs/api/v1-returns.md` 中「查询总体收益汇总」部分。

## 新概念说明

### Aggregation（聚合）

Aggregation 是把多条明细数据汇总成一个总数或平均数。  
本任务把多个基金的收益汇总成博主收益，再把多个博主的收益汇总成总体收益。

### N+1 Query（N+1 查询）

N+1 Query 指先查一批主数据，再循环为主数据逐条查询关联数据。  
本任务第一版使用这种方式，因为简单易懂；当前数据量小，先不做复杂优化。

## 执行目录

```bash
cd /d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：确认已有收益路由

**必要性：**  
本任务复用任务 034 和 035 已经建好的路由文件，先确认基础内容存在。

打开：

```text
backend/app/routes/returns.py
```

确认里面已经有：

1. `returns_bp`
2. `parse_positive_int()`
3. `_to_number()`
4. `_serialize_return_item()`
5. 单博主收益接口
6. 单基金收益接口

如果缺少这些内容，先完成前置任务，不要继续。

---

### 步骤 2：添加总体收益汇总路由

**必要性：**  
前端总览看板需要一个能直接展示整体收益情况的接口。这一步把所有博主持仓收益逐个算出后汇总。

在 `backend/app/routes/returns.py` 末尾添加：

```python
@returns_bp.get("/api/v1/returns/summary")
def get_total_returns_summary():
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
            blogger_summaries = []

            for blogger in bloggers:
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
                    continue

                fund_ids = [item["fund_id"] for item in position_items]
                nav_map = get_nav_on_date_map(
                    cursor,
                    fund_ids,
                    return_date
                )
                return_items = calculate_position_returns(
                    position_items,
                    nav_map
                )
                blogger_summary = calculate_total_returns(return_items)

                all_return_items.extend(return_items)
                blogger_summaries.append(
                    {
                        "blogger_id": blogger["id"],
                        "blogger_name": blogger["name"],
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
                        ),
                        "funds": [
                            _serialize_return_item(item)
                            for item in return_items
                        ]
                    }
                )

            total_summary = calculate_total_returns(all_return_items)
    finally:
        conn.close()

    return success(
        data={
            "return_date": return_date.strftime("%Y-%m-%d"),
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
            "blogger_count": len(blogger_summaries),
            "items": blogger_summaries
        }
    )
```

说明：

- `list.extend()` 会把另一个列表里的元素逐个加入当前列表；这里用于把每个博主的基金收益明细累积到总体明细里。
- 没有持仓数据的博主不进入 `items`，也不计入 `blogger_count`。
- 只要任意基金缺当天净值，总体市值、总收益金额和总收益率都会是 `null`。

---

### 步骤 3：语法检查

**必要性：**  
先确认新路由没有语法错误，再进行接口验证。

执行：

```bash
python -m py_compile app/routes/returns.py
```

预期没有输出，并且退出码是 `0`。

---

### 步骤 4：启动服务并手动验证

**必要性：**  
总体汇总会跨越多个博主和基金，必须实际请求一次，确认空数据、有数据、缺净值时响应都正确。

启动服务：

```bash
python run.py
```

另开一个终端，在 `backend` 目录执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/returns/summary?return_date=2026-09-30"
```

预期返回 HTTP `200`，响应结构符合 `docs/api/v1-returns.md`。

---

### 步骤 5：运行已有测试

**必要性：**  
确认新接口没有破坏已有模块。

停止服务后，在 `backend` 目录执行：

```bash
pytest -q
```

预期全部通过。

## 验证方式

### 1. 语法检查

```bash
python -m py_compile app/routes/returns.py
```

预期没有输出。

### 2. 成功请求

```bash
curl -i "http://127.0.0.1:5000/api/v1/returns/summary?return_date=2026-09-30"
```

预期 HTTP `200`，字段与接口文档一致。

### 3. 不传日期

```bash
curl -i "http://127.0.0.1:5000/api/v1/returns/summary"
```

预期 HTTP `200`，`return_date` 是今天。

### 4. 空数据场景

在测试环境清空基础数据后请求：

```bash
curl -i "http://127.0.0.1:5000/api/v1/returns/summary?return_date=2026-09-30"
```

预期 HTTP `200`，`blogger_count` 是 `0`，`items` 是 `[]`，总成本、总市值、总收益金额是 `0`，总收益率是 `null`。

### 5. 错误场景

```bash
curl -i "http://127.0.0.1:5000/api/v1/returns/summary?return_date=bad-date"
curl -i "http://127.0.0.1:5000/api/v1/returns/summary?return_date=2999-12-31"
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
没有持仓数据的博主不要进入 `items`，也不要计入数量。

### 2. 只汇总有净值的基金

如果任意基金缺当天净值，总体市值必须返回 `null`。  
不要只把有净值的基金加起来，否则会误判收益。

### 3. 在路由里重复实现收益率公式

单基金、单博主、总体收益都应该使用任务 033 的 `calculate_total_returns()`。  
不要在路由里再次手写 `(市值 - 成本) / 成本`。

### 4. 忘记空列表场景

没有任何博主或持仓时，接口应该返回 `200` 和空汇总，而不是返回 `500`。  
`calculate_total_returns([])` 可以处理空列表。

## 完成标准

以下条件全部满足，任务 036 才算完成：

1. `GET /api/v1/returns/summary` 可访问。
2. `return_date` 可选，默认今天。
3. 响应字段和 `docs/api/v1-returns.md` 一致。
4. 空数据时返回 `200`，不抛异常。
5. 缺净值时相关汇总字段返回 `null`。
6. `pytest -q` 全部通过。

## 完成后请反馈

1. 修改的文件列表。
2. 语法检查输出。
3. 成功请求的完整响应 JSON。
4. 空数据、缺净值和错误场景的响应 JSON。
5. `pytest -q` 的完整输出。
6. 遇到的问题和未完成项。
