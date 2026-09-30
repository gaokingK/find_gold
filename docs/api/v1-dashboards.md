# 看板接口文档

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 版本 | v1.0 |
| 状态 | 已确认 |
| 日期 | 2026-09-30 |
| 对应计划 | 第 5–9 天功能闭环计划「汇总看板与交付检查」 |
| 后端框架 | Flask |
| 数据库 | MySQL |
| API 前缀 | `/api/v1/` |

本文档是看板模块前后端联调的唯一契约。  
字段发生任何变更，必须先改本文档，再改代码，并通知前端。

---

## 1. 全局约定

本模块沿用 `docs/api/v1-basic-management.md` 的全局约定：

1. 请求体和响应体都使用 `application/json`。
2. 日期字段格式为 `YYYY-MM-DD`。
3. 统一成功响应：`{"code": 0, "message": "ok", "data": {}}`。
4. 统一错误响应：`{"code": "错误码", "message": "提示", "details": []}`。
5. 第一版不做用户认证。
6. 所有看板接口的成功响应都返回 HTTP `200`。

### 1.1 本模块 HTTP 状态码

| HTTP 状态码 | 含义 |
| --- | --- |
| 200 | 成功 |
| 400 | 参数错误 |
| 500 | 服务器内部错误 |

### 1.2 本模块错误码

| 错误码 | HTTP 状态码 | 说明 |
| --- | --- | --- |
| `VALIDATION_ERROR` | 400 | 日期、数量等参数校验失败 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

### 1.3 收益和空值口径

看板中的成本、市值、收益金额、收益率沿用 `docs/api/v1-returns.md`：

1. 只使用指定日期当天的净值，不使用最近一天净值兜底。
2. 成本小于等于 `0` 时，收益率返回 `null`。
3. 某只基金缺指定日期净值时，**只有它自己**的市值、收益金额、收益率返回 `null`；同一响应里其他有净值的基金照实返回。
4. 汇总值（某个博主的合计、全部博主的合计、总市值、各类占比）只要包含任何一个缺净值的基金，就整体返回 `null`——汇总的分母或加数不完整，算出来会误导前端。
5. 涉及金额和份额的计算在后端使用 `Decimal`。
6. 返回 JSON 时，金额四舍五入到 2 位小数，份额四舍五入到 4 位小数，收益率四舍五入到 6 位小数。

---

## 2. 接口总览

| 序号 | 接口 | 方法 | 路径 |
| --- | --- | --- | --- |
| 1 | 博主总览看板 | GET | `/api/v1/dashboards/bloggers` |
| 2 | 基金分布看板 | GET | `/api/v1/dashboards/funds` |
| 3 | 近期操作统计 | GET | `/api/v1/dashboards/recent-operations` |

第一版不提供：

- 自定义指标配置
- 图表专用数据格式
- 分页
- 缓存
- 定时预计算
- 用户维度的看板权限

---

## 3. 博主总览看板

### 接口名称

博主总览看板 / `get_blogger_overview_dashboard`

### 请求方法与路径

```http
GET /api/v1/dashboards/bloggers
```

### 功能说明

按博主维度汇总指定日期的持仓数量、成本、市值、收益金额和累计收益率。

这个接口和 `GET /api/v1/returns/summary`（见 `docs/api/v1-returns.md`）是同一份数据的两种视图：

| 项目 | `/returns/summary` | `/dashboards/bloggers` |
| --- | --- | --- |
| 用途 | 收益页面，需要下钻到每只基金 | 总览页面，只要博主级卡片 |
| 每个博主的明细 | 有 `funds` 数组 | **没有**，只有 `fund_count` |
| 额外字段 | — | `position_count` |

后端必须复用同一套计算逻辑（`calculate_position_snapshots()` + `calculate_position_returns()` + `calculate_total_returns()`），只是输出结构不同。  
**不要为这个接口另写一套收益算法**，否则两个接口会给出不一样的收益率，前端会先发现，然后没人说得清哪个对。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| return_date | string | 否 | `2026-09-30` | 收益计算日期，格式 `YYYY-MM-DD`，不能晚于今天；不传时默认今天 |

### 请求示例

```bash
curl "http://127.0.0.1:5000/api/v1/dashboards/bloggers?return_date=2026-09-30"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data.return_date | string | 收益计算日期 |
| data.blogger_count | int | 有持仓收益数据的博主数量 |
| data.position_count | int | 博主和基金组合的持仓数量 |
| data.total_cost_amount | number | 所有博主总成本 |
| data.total_market_value | number / null | 所有博主总市值；任意基金缺当天净值时为 `null` |
| data.profit_amount | number / null | 所有博主总收益金额 |
| data.return_rate | number / null | 所有博主总累计收益率 |
| data.items | array | 按博主拆分的汇总列表 |
| data.items[].blogger_id | int | 博主 ID |
| data.items[].blogger_name | string | 博主名称 |
| data.items[].fund_count | int | 该博主持有的基金数量 |
| data.items[].total_cost_amount | number | 该博主总成本 |
| data.items[].total_market_value | number / null | 该博主总市值 |
| data.items[].profit_amount | number / null | 该博主总收益金额 |
| data.items[].return_rate | number / null | 该博主总累计收益率 |

### 成功响应示例

HTTP 状态码 `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "return_date": "2026-09-30",
    "blogger_count": 1,
    "position_count": 2,
    "total_cost_amount": 43540.00,
    "total_market_value": 48080.00,
    "profit_amount": 4540.00,
    "return_rate": 0.104272,
    "items": [
      {
        "blogger_id": 1,
        "blogger_name": "基金小星",
        "fund_count": 2,
        "total_cost_amount": 43540.00,
        "total_market_value": 48080.00,
        "profit_amount": 4540.00,
        "return_rate": 0.104272
      }
    ]
  }
}
```

### 空数据响应示例

没有可计算的持仓数据，HTTP `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "return_date": "2026-09-30",
    "blogger_count": 0,
    "position_count": 0,
    "total_cost_amount": 0.00,
    "total_market_value": 0.00,
    "profit_amount": 0.00,
    "return_rate": null,
    "items": []
  }
}
```

### 错误响应示例

日期格式错误，HTTP `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "return_date",
      "message": "收益日期格式必须是 YYYY-MM-DD"
    }
  ]
}
```

日期晚于今天，HTTP `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "return_date",
      "message": "收益日期不能晚于今天"
    }
  ]
}
```

服务器内部错误，HTTP `500`：

```json
{
  "code": "INTERNAL_ERROR",
  "message": "服务器内部错误",
  "details": []
}
```

### 业务规则

1. 遍历所有博主，逐个计算持仓收益后汇总。
2. `blogger_count` 只统计有持仓收益数据的博主，不统计没有持仓的博主。
3. `position_count` 等于所有博主收益明细的数量，即「博主 + 基金」组合数量。
4. 没有持仓数据的博主不进入 `items`。
5. 只使用 `return_date` 当天的净值。
6. 任意基金缺当天净值时，受影响博主和总体汇总的市值、收益金额、收益率返回 `null`。

### 关联接口

- 简单收益查询：`docs/api/v1-returns.md`（`GET /api/v1/returns/summary` 是本接口的明细版，必须复用同一套计算逻辑）
- 持仓快照：`docs/api/v1-position-snapshots.md`
- 博主管理：`docs/api/v1-basic-management.md`

---

## 4. 基金分布看板

### 接口名称

基金分布看板 / `get_fund_distribution_dashboard`

### 请求方法与路径

```http
GET /api/v1/dashboards/funds
```

### 功能说明

按基金维度汇总所有博主的份额、成本、市值，并返回成本占比和市值占比。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| return_date | string | 否 | `2026-09-30` | 收益计算日期，格式 `YYYY-MM-DD`，不能晚于今天；不传时默认今天 |

### 请求示例

```bash
curl "http://127.0.0.1:5000/api/v1/dashboards/funds?return_date=2026-09-30"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data.return_date | string | 收益计算日期 |
| data.fund_count | int | 有持仓数据的基金数量 |
| data.total_cost_amount | number | 所有基金总成本 |
| data.total_market_value | number / null | 所有基金总市值；任意基金缺当天净值时为 `null` |
| data.items | array | 按基金拆分的分布列表，按成本金额从高到低排序 |
| data.items[].fund_id | int | 基金 ID |
| data.items[].fund_name | string | 基金名称 |
| data.items[].fund_code | string | 基金代码 |
| data.items[].blogger_count | int | 持有该基金的博主数量 |
| data.items[].shares | number | 所有博主持有该基金的份额合计 |
| data.items[].cost_amount | number | 所有博主持有该基金的成本合计 |
| data.items[].nav | number / null | 该基金指定日期当天的净值 |
| data.items[].nav_date | string / null | 净值日期 |
| data.items[].market_value | number / null | 该基金市值合计 |
| data.items[].cost_ratio | number / null | 成本占比 |
| data.items[].market_value_ratio | number / null | 市值占比 |

### 成功响应示例

HTTP 状态码 `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "return_date": "2026-09-30",
    "fund_count": 2,
    "total_cost_amount": 43540.00,
    "total_market_value": 48080.00,
    "items": [
      {
        "fund_id": 101,
        "fund_name": "华夏成长混合",
        "fund_code": "000001",
        "blogger_count": 2,
        "shares": 18700.0000,
        "cost_amount": 27940.00,
        "nav": 2.4000,
        "nav_date": "2026-09-30",
        "market_value": 44880.00,
        "cost_ratio": 0.641709,
        "market_value_ratio": 0.933444
      },
      {
        "fund_id": 102,
        "fund_name": "稳健增利债券",
        "fund_code": "000002",
        "blogger_count": 1,
        "shares": 4000.0000,
        "cost_amount": 15600.00,
        "nav": 0.8000,
        "nav_date": "2026-09-30",
        "market_value": 3200.00,
        "cost_ratio": 0.358291,
        "market_value_ratio": 0.066556
      }
    ]
  }
}
```

### 缺净值响应示例

任意基金缺当天净值时，HTTP 仍然是 `200`。

口径是：

- **缺净值的基金**：自己的 `nav`、`nav_date`、`market_value`、`market_value_ratio` 是 `null`。
- **有净值的基金**：`market_value` 照实返回；但 `market_value_ratio` 是 `null`，因为占比的分母（总市值）不可信。
- **所有基金**：`cost_amount` 和 `cost_ratio` 都照实返回，成本不依赖净值。
- **总市值** `total_market_value` 是 `null`。

下面的例子里，基金 101 缺当天净值，基金 102 有净值：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "return_date": "2026-09-30",
    "fund_count": 2,
    "total_cost_amount": 43540.00,
    "total_market_value": null,
    "items": [
      {
        "fund_id": 101,
        "fund_name": "华夏成长混合",
        "fund_code": "000001",
        "blogger_count": 2,
        "shares": 18700.0000,
        "cost_amount": 27940.00,
        "nav": null,
        "nav_date": null,
        "market_value": null,
        "cost_ratio": 0.641709,
        "market_value_ratio": null
      },
      {
        "fund_id": 102,
        "fund_name": "稳健增利债券",
        "fund_code": "000002",
        "blogger_count": 1,
        "shares": 4000.0000,
        "cost_amount": 15600.00,
        "nav": 0.8000,
        "nav_date": "2026-09-30",
        "market_value": 3200.00,
        "cost_ratio": 0.358291,
        "market_value_ratio": null
      }
    ]
  }
}
```

注意 `items` 的条数必须和 `fund_count` 一致——缺净值不会让基金从列表里消失。

### 错误响应示例

日期格式错误，HTTP `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "return_date",
      "message": "收益日期格式必须是 YYYY-MM-DD"
    }
  ]
}
```

日期晚于今天，HTTP `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "return_date",
      "message": "收益日期不能晚于今天"
    }
  ]
}
```

服务器内部错误，HTTP `500`：

```json
{
  "code": "INTERNAL_ERROR",
  "message": "服务器内部错误",
  "details": []
}
```

### 业务规则

1. 同一只基金被多个博主持有时，份额、成本、市值跨博主累加。
2. `blogger_count` 表示持有该基金的去重博主数量。
3. `items` 按 `cost_amount` 从高到低排序。
4. 成本不依赖净值，缺净值时仍然可以计算成本占比。
5. 某只基金缺当天净值时，**只有它自己**的 `nav`、`nav_date`、`market_value` 返回 `null`；其他有净值的基金照实返回自己的市值。这和 `docs/api/v1-returns.md` 的逐基金口径一致。
6. 只要任意一只基金缺当天净值，`total_market_value` 和**所有**基金的 `market_value_ratio` 都返回 `null`——占比的分母不完整，算出来会误导前端。
7. `items` 的条数始终等于 `fund_count`，缺净值不会让基金从列表里消失。
8. 总成本为 `0` 时，所有 `cost_ratio` 返回 `null`。
9. 总市值为 `0` 或 `null` 时，所有 `market_value_ratio` 返回 `null`。

### 关联接口

- 博主总览看板：`GET /api/v1/dashboards/bloggers`
- 简单收益查询：`docs/api/v1-returns.md`
- 基金管理：`docs/api/v1-basic-management.md`

---

## 5. 近期操作统计

### 接口名称

近期操作统计 / `get_recent_operation_statistics`

### 请求方法与路径

```http
GET /api/v1/dashboards/recent-operations
```

### 功能说明

统计指定日期范围内的买入、卖出、现金分红数量和金额，并返回范围内最近的操作记录列表。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| start_date | string | 否 | `2026-09-24` | 开始日期，格式 `YYYY-MM-DD`；不传时默认 `end_date - 6`，也就是最近 7 天 |
| end_date | string | 否 | `2026-09-30` | 结束日期，格式 `YYYY-MM-DD`，不能晚于今天；不传时默认今天 |
| limit | int | 否 | `20` | 返回的操作记录条数，范围 `1–100`，不传时默认 `20` |

### 请求示例

```bash
curl "http://127.0.0.1:5000/api/v1/dashboards/recent-operations?start_date=2026-09-24&end_date=2026-09-30&limit=20"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data.start_date | string | 统计开始日期 |
| data.end_date | string | 统计结束日期 |
| data.limit | int | 当前返回的操作记录条数上限 |
| data.summary.operation_count | int | 范围内操作记录总数 |
| data.summary.buy_count | int | 买入记录数量 |
| data.summary.buy_shares | number | 买入份额合计 |
| data.summary.buy_amount | number | 买入金额合计 |
| data.summary.sell_count | int | 卖出记录数量 |
| data.summary.sell_shares | number | 卖出份额合计 |
| data.summary.sell_amount | number | 卖出金额合计 |
| data.summary.dividend_cash_count | int | 现金分红记录数量 |
| data.summary.dividend_cash_amount | number | 现金分红金额合计 |
| data.items | array | 最近操作记录列表，按操作日期倒序、ID 倒序排列 |
| data.items[].operation_id | int | 操作记录 ID |
| data.items[].blogger_id | int | 博主 ID |
| data.items[].blogger_name | string | 博主名称 |
| data.items[].fund_id | int | 基金 ID |
| data.items[].fund_name | string | 基金名称 |
| data.items[].fund_code | string | 基金代码 |
| data.items[].operation_type | string | 操作类型：`buy`、`sell`、`dividend_cash` |
| data.items[].operation_date | string | 操作日期 |
| data.items[].shares | number | 操作份额 |
| data.items[].amount | number | 操作金额 |

### 成功响应示例

HTTP 状态码 `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "start_date": "2026-09-24",
    "end_date": "2026-09-30",
    "limit": 20,
    "summary": {
      "operation_count": 3,
      "buy_count": 1,
      "buy_shares": 1000.0000,
      "buy_amount": 13000.00,
      "sell_count": 1,
      "sell_shares": 300.0000,
      "sell_amount": 4200.00,
      "dividend_cash_count": 1,
      "dividend_cash_amount": 120.00
    },
    "items": [
      {
        "operation_id": 12,
        "blogger_id": 1,
        "blogger_name": "基金小星",
        "fund_id": 101,
        "fund_name": "华夏成长混合",
        "fund_code": "000001",
        "operation_type": "buy",
        "operation_date": "2026-09-30",
        "shares": 1000.0000,
        "amount": 13000.00
      }
    ]
  }
}
```

### 空数据响应示例

范围内没有操作记录时，HTTP `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "start_date": "2026-09-24",
    "end_date": "2026-09-30",
    "limit": 20,
    "summary": {
      "operation_count": 0,
      "buy_count": 0,
      "buy_shares": 0.0000,
      "buy_amount": 0.00,
      "sell_count": 0,
      "sell_shares": 0.0000,
      "sell_amount": 0.00,
      "dividend_cash_count": 0,
      "dividend_cash_amount": 0.00
    },
    "items": []
  }
}
```

### 错误响应示例

开始日期格式错误，HTTP `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "start_date",
      "message": "开始日期格式必须是 YYYY-MM-DD"
    }
  ]
}
```

结束日期晚于今天，HTTP `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "end_date",
      "message": "结束日期不能晚于今天"
    }
  ]
}
```

开始日期晚于结束日期，HTTP `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "start_date",
      "message": "开始日期不能晚于结束日期"
    }
  ]
}
```

### 业务规则

1. 日期范围包含开始日期和结束日期。
2. `summary` 统计整个日期范围内的所有操作记录。
3. `items` 只返回按 `limit` 截断后的最近记录，所以 `items` 的数量可能小于 `summary.operation_count`。
4. 不传 `start_date` 和 `end_date` 时，默认查询最近 7 天，包含今天。
5. 只支持 `buy`、`sell`、`dividend_cash`。
6. `summary` 里的所有字段**始终出现**，范围内没有某个类型的记录时补 `0`，不要省略字段，也不要返回 `null`。
7. `*_count` 是整数；`*_shares` 和 `*_amount` 是金额类数字，即使是 `0` 也按小数位返回（份额 4 位、金额 2 位）。
8. `dividend_cash` 不统计份额，因为现金分红不改变份额。
9. 第一版不区分操作记录编辑后的影响，因为操作记录当前没有编辑接口。

### 关联接口

- 操作记录列表：`docs/api/v1-operations.md`
- 博主管理：`docs/api/v1-basic-management.md`
- 基金管理：`docs/api/v1-basic-management.md`

---

## 6. 变更记录

| 日期 | 版本 | 说明 |
| --- | --- | --- |
| 2026-09-30 | v1.0 | 初始化看板接口文档 |
