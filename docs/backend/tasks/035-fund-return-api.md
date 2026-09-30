# 任务 035：单基金收益汇总接口

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务复用任务 034 的路由结构、持仓快照、精确净值查询和收益计算，只增加基金 ID 校验、基金存在性检查和单基金结果定位。不新增表、不新增依赖。

## 任务目标

修改：

```text
backend/app/routes/returns.py
```

完成后可以：

1. 访问 `GET /api/v1/bloggers/{blogger_id}/funds/{fund_id}/return`。
2. 按可选参数 `return_date` 计算某个博主持有某只基金的收益。
3. 返回份额、成本、当天净值、市值、收益金额、收益率。
4. 基金不存在或该博主没有该基金持仓数据时，返回 `404 FUND_NOT_FOUND`。
5. `pytest -q` 仍然全部通过。

## 范围说明

本任务只实现单基金收益查询接口。

不包含：

- 总体收益汇总接口
- 多只基金批量收益查询
- 修改基金管理接口
- 修改净值录入接口
- 最近一天净值兜底
- 最大回撤、年化收益、夏普比率

## 前置条件

1. 任务 034 已完成，单博主收益接口可用。
2. `returns_bp` 已在 `backend/app/__init__.py` 注册。
3. `pytest -q` 当前全部通过。
4. 已阅读 `docs/api/v1-returns.md` 中「查询单基金收益」部分。

## 新概念说明

### Path Parameter（路径参数）

路径参数写在 URL 路径里，用来定位资源。  
本接口用 `blogger_id` 定位博主，用 `fund_id` 定位基金。

### `next()`

`next()` 用于从可迭代对象里找到第一个满足条件的元素。  
本任务用它从多只基金的收益明细里找出指定 `fund_id` 的那一条；找不到时返回 `None`。

## 执行目录

```bash
cd /d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：确认已有路由文件

**必要性：**  
本任务在任务 034 的文件上继续扩展，先确认文件和蓝图都存在，避免改错位置。

打开：

```text
backend/app/routes/returns.py
```

确认里面已经有：

1. `returns_bp = Blueprint("returns", __name__)`
2. `parse_positive_int()`
3. `_to_number()`
4. `_serialize_return_item()`
5. 任务 034 的单博主收益路由

如果缺少这些内容，先完成任务 034，不要继续。

---

### 步骤 2：添加单基金收益路由

**必要性：**  
单基金收益是前端查看某个博主某只基金表现时需要的最小接口。放在同一个 `returns.py` 文件里，可以复用已有的辅助函数。

在 `backend/app/routes/returns.py` 末尾添加：

```python
@returns_bp.get("/api/v1/bloggers/<blogger_id>/funds/<fund_id>/return")
def get_blogger_fund_return(blogger_id, fund_id):
    parsed_blogger_id = parse_positive_int(blogger_id)

    if parsed_blogger_id is None:
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

    parsed_fund_id = parse_positive_int(fund_id)

    if parsed_fund_id is None:
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
                "SELECT id, name FROM bloggers WHERE id = %s",
                (parsed_blogger_id,)
            )
            blogger = cursor.fetchone()

            if blogger is None:
                return error(
                    code="BLOGGER_NOT_FOUND",
                    message="博主不存在",
                    details=[],
                    http_status=404
                )

            cursor.execute(
                "SELECT id, name, fund_code FROM funds WHERE id = %s",
                (parsed_fund_id,)
            )
            fund = cursor.fetchone()

            if fund is None:
                return error(
                    code="FUND_NOT_FOUND",
                    message="基金不存在，或该博主未持有该基金",
                    details=[],
                    http_status=404
                )

            initial_positions = get_initial_positions(
                cursor,
                parsed_blogger_id,
                return_date
            )
            operations = get_operations(
                cursor,
                parsed_blogger_id,
                return_date
            )
            position_items = calculate_position_snapshots(
                initial_positions,
                operations
            )
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
            matched_item = next(
                (
                    item
                    for item in return_items
                    if item["fund_id"] == parsed_fund_id
                ),
                None
            )

            if matched_item is None:
                return error(
                    code="FUND_NOT_FOUND",
                    message="基金不存在，或该博主未持有该基金",
                    details=[],
                    http_status=404
                )
    finally:
        conn.close()

    serialized_fund = _serialize_return_item(matched_item)
    serialized_fund.update(
        {
            "blogger_id": parsed_blogger_id,
            "blogger_name": blogger["name"],
            "return_date": return_date.strftime("%Y-%m-%d"),
        }
    )

    return success(data=serialized_fund)
```

说明：

- `matched_item` 是从该博主全部基金收益明细里找到的指定基金那条记录。
- 即使 `fund` 表里存在这只基金，只要该博主没有对应的初始持仓或操作记录，也返回 `FUND_NOT_FOUND`。
- 返回时先复用 `_serialize_return_item()`，再补充博主和日期字段。

---

### 步骤 3：语法检查

**必要性：**  
先确认修改后的路由文件没有语法错误，再启动服务。

执行：

```bash
python -m py_compile app/routes/returns.py
```

预期没有输出，并且退出码是 `0`。

---

### 步骤 4：启动服务并手动验证

**必要性：**  
新增路由后必须实际请求，才能确认 URL、SQL 和响应字段都正确。

启动服务：

```bash
python run.py
```

另开一个终端，在 `backend` 目录执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/funds/101/return?return_date=2026-09-30"
```

把 `1` 和 `101` 换成数据库里实际存在且有持仓关系的博主 ID 和基金 ID。

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
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/funds/101/return?return_date=2026-09-30"
```

预期 HTTP `200`，字段与接口文档一致。

### 3. 缺净值场景

使用一个指定日期没有净值但博主有持仓的请求：

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/funds/101/return?return_date=2026-09-29"
```

预期 HTTP `200`，`nav`、`nav_date`、`market_value`、`profit_amount`、`return_rate` 都是 `null`。

### 4. 错误场景

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/abc/funds/101/return"
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/funds/abc/return"
curl -i "http://127.0.0.1:5000/api/v1/bloggers/999999/funds/101/return"
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/funds/999999/return"
```

预期结果：前两个返回 HTTP `400 VALIDATION_ERROR`；第三个返回 HTTP `404 BLOGGER_NOT_FOUND`；第四个返回 HTTP `404 FUND_NOT_FOUND`。

### 5. 已有测试

```bash
pytest -q
```

预期全部通过。

## 常见坑

### 1. 只判断基金表存在，不判断持仓关系

接口的语义是「某个博主持有某只基金的收益」。  
即使基金存在，如果该博主没有这只基金的持仓数据，也应该返回 `FUND_NOT_FOUND`。

### 2. 先找基金明细，再查净值

一定要先用 `calculate_position_snapshots()` 得到持仓明细，再用 `get_nav_on_date_map()` 查净值。  
顺序反了会导致不知道应该查哪些 `fund_id`。

### 3. 直接从基金表查名称拼结果

单基金收益的份额和成本来自初始持仓和操作记录，不能只根据基金表里的数据凭空返回。  
必须走持仓快照和收益计算。

### 4. 误用最近一天净值

这里必须使用 `get_nav_on_date_map()`。  
不要使用 `get_latest_nav_map()`。

## 完成标准

以下条件全部满足，任务 035 才算完成：

1. `GET /api/v1/bloggers/{blogger_id}/funds/{fund_id}/return` 可访问。
2. `return_date` 可选，默认今天。
3. 响应字段和 `docs/api/v1-returns.md` 一致。
4. 缺净值时相关字段返回 `null`。
5. 基金不存在或博主没有该基金持仓时返回 `404 FUND_NOT_FOUND`。
6. `pytest -q` 全部通过。

## 完成后请反馈

1. 修改的文件列表。
2. 语法检查输出。
3. 成功请求的完整响应 JSON。
4. 缺净值和错误场景的响应 JSON。
5. `pytest -q` 的完整输出。
6. 遇到的问题和未完成项。
