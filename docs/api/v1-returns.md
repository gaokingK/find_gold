# 收益查询接口文档

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 版本 | v1.0 |
| 状态 | 已确认 |
| 日期 | 2026-09-30 |
| 对应计划 | 第 5–9 天功能闭环计划「简单收益计算」 |
| 后端框架 | Flask |
| 数据库 | MySQL |
| API 前缀 | `/api/v1/` |

本文档是简单收益模块前后端联调的唯一契约。  
字段发生任何变更，必须先改本文档，再改代码，并通知前端。

---

## 1. 全局约定

本模块沿用 `docs/api/v1-basic-management.md` 的全局约定：

1. 请求体和响应体都使用 `application/json`。
2. 日期字段格式为 `YYYY-MM-DD`。
3. 统一成功响应：`{"code": 0, "message": "ok", "data": {}}`。
4. 统一错误响应：`{"code": "错误码", "message": "提示", "details": []}`。
5. 第一版不做用户认证。
6. 所有收益接口的成功响应都返回 HTTP `200`。

### 1.1 本模块 HTTP 状态码

| HTTP 状态码 | 含义 |
| --- | --- |
| 200 | 成功 |
| 400 | 参数错误 |
| 404 | 博主、基金或持仓关系不存在 |
| 500 | 服务器内部错误 |

### 1.2 本模块错误码

| 错误码 | HTTP 状态码 | 说明 |
| --- | --- | --- |
| `VALIDATION_ERROR` | 400 | 路径参数或日期参数校验失败 |
| `BLOGGER_NOT_FOUND` | 404 | 博主不存在 |
| `FUND_NOT_FOUND` | 404 | 基金不存在，或该博主没有这只基金的持仓数据 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

---

## 2. 收益计算口径

第一版只计算简单累计收益：

| 指标 | 公式 |
| --- | --- |
| 成本 | 当前剩余成本 |
| 市值 | 当前份额 × 指定日期当天的净值 |
| 收益金额 | 市值 - 成本 |
| 收益率 | `(市值 - 成本) / 成本` |

### 2.1 空值规则

| 场景 | 返回结果 |
| --- | --- |
| 成本小于等于 `0` | `return_rate` 返回 `null`，不返回 `0` |
| 指定日期没有当天净值 | `nav`、`nav_date`、`market_value`、`profit_amount`、`return_rate` 都返回 `null` |
| 多个基金汇总时，任意一个基金缺当天净值 | 总市值、总收益金额、总收益率返回 `null` |
| 没有任何持仓数据 | 总成本、总市值、收益金额返回 `0`，收益率返回 `null` |

### 2.2 精度规则

1. 后端计算成本、市值、收益金额和收益率时使用 `Decimal`，不使用 `float`。
2. 返回 JSON 时，金额四舍五入到 2 位小数。
3. 份额四舍五入到 4 位小数。
4. 收益率四舍五入到 6 位小数，仍然使用小数表示，例如 `0.123456` 表示 `12.3456%`。

### 2.3 本阶段不做

- 最大回撤
- 年化收益
- 夏普比率
- 持仓分布
- 操作频率
- 净值复权
- 自动净值同步
- 最近一天净值兜底

### 2.4 null 真值表（收益类接口统一）

设：A = 无持仓数据；B = 有持仓、有当天净值；C = 有持仓、缺当天净值。

| 层级 | 场景 | cost_amount | nav | market_value | profit_amount | return_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 基金级 | B | 数值 | 数值 | 数值 | 数值 | 数值 |
| 基金级 | C | 数值 | `null` | `null` | `null` | `null` |
| 基金级 | B 但成本 ≤ 0 | 数值（可为 0 或负） | 数值 | 数值 | 市值 − 成本 | `null` |
| 博主级 | 名下所有基金都是 B | 数值 | — | 数值 | 数值 | 数值 |
| 博主级 | 名下**任意**基金是 C | 数值 | — | `null` | `null` | `null` |
| 博主级 | 总成本 ≤ 0 | 数值 | — | 数值 | 数值 | `null` |
| 博主级 | A（无持仓） | `0` | — | `0` | `0` | `null` |
| 全局级 | 全部基金都是 B | 数值 | — | 数值 | 数值 | 数值 |
| 全局级 | **任意**基金是 C | 数值 | — | `null` | `null` | `null` |
| 全局级 | A（无任何持仓） | `0` | — | `0` | `0` | `null` |

要点：

1. **`0` 只出现在"根本没有任何持仓"这一格。** 只要有持仓且缺净值，一律 `null`，绝不返回 `0`。前端需要能区分"亏到 0"和"没数据"。
2. 成本 ≤ 0 时，`market_value` 和 `profit_amount` **照实返回数值**（`profit_amount = market_value − cost_amount`），只有 `return_rate` 是 `null`。
3. 成本可以是负数（超额卖出导致），照实返回，不截断到 0。
4. `return_rate` 为 `null` 有三种互不覆盖的原因：无持仓、缺净值、成本 ≤ 0。后端不额外返回原因字段，前端按上表判断。
5. `docs/api/v1-dashboards.md` 的 null 规则是对本表在博主级和全局级的展开，冲突时以本表为准。

### 2.5 现金分红的收益归属

**第一版：现金分红不计入收益金额。** `profit_amount = market_value − cost_amount`；`dividend_cash_amount` 只在持仓快照和近期操作统计中体现，不参与收益率计算。

理由：现金分红拿到的是现金，已脱离持仓；要计入必须引入"已实现收益 + 未实现浮动收益"双口径，第一版不做。前端如需展示分红，单独取 `dividend_cash_amount`。

### 2.6 多初始持仓的计算口径（与持仓快照对齐）

同一 `blogger_id + fund_id` 存在多条初始持仓时，**只取 `record_date` 最早的一条作为计算起点，其余初始持仓完全不参与计算（不累加份额、不累加成本）**。

本条**覆盖**本文档第 4 节业务规则 1「只统计 `return_date` 当天或之前的初始持仓和操作记录」中的"初始持仓"部分；操作记录仍按 `operation_date <= return_date` 全量统计。

本条与 `docs/api/v1-position-snapshots.md` 业务规则 3 完全一致，两个接口对同一博主同一日期必须给出**相同**的 `shares` 和 `cost_amount`。

### 2.7 其他

1. `return_date` 不设下界；传历史日期时返回空 `items` 和零值汇总，HTTP 200。
2. `return_date` 不传时默认今天。**周末和节假日没有净值，默认查询会返回 `null` 市值**，这是预期行为，不是故障。前端在 `market_value` 为 `null` 时应提示"该日期无净值数据"并引导用户选择其他日期。
3. 所有金额单位为**元**。
4. 单基金接口 `GET /bloggers/{blogger_id}/funds/{fund_id}/return` 中，"基金不存在"与"该博主未持有该基金"共用 `FUND_NOT_FOUND`，HTTP 404，靠 `message` 区分。
5. 成本小于等于 `0` 时返回 `null` 收益率，不返回 `0`，不抛异常。

---

## 3. 接口总览

| 序号 | 接口 | 方法 | 路径 |
| --- | --- | --- | --- |
| 1 | 查询单博主累计收益 | GET | `/api/v1/bloggers/{blogger_id}/returns` |
| 2 | 查询单基金收益 | GET | `/api/v1/bloggers/{blogger_id}/funds/{fund_id}/return` |
| 3 | 查询总体收益汇总 | GET | `/api/v1/returns/summary` |

---

## 4. 查询单博主累计收益

### 接口名称

查询单博主累计收益 / `get_blogger_returns`

### 请求方法与路径

```http
GET /api/v1/bloggers/{blogger_id}/returns
```

### 功能说明

根据初始持仓、截至指定日期的操作记录和指定日期当天的净值，计算一个博主的整体成本、市值、收益金额和累计收益率，并返回按基金拆分的明细。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| blogger_id | int | 是 | `1` | 路径参数，博主 ID，必须为正整数 |
| return_date | string | 否 | `2026-09-30` | 收益计算日期，格式 `YYYY-MM-DD`，不能晚于今天；不传时默认今天 |

### 请求示例

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers/1/returns?return_date=2026-09-30"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data.blogger_id | int | 博主 ID |
| data.blogger_name | string | 博主名称 |
| data.return_date | string | 收益计算日期 |
| data.total_cost_amount | number | 总成本 |
| data.total_market_value | number / null | 总市值；任意基金缺当天净值时为 `null` |
| data.profit_amount | number / null | 总收益金额 |
| data.return_rate | number / null | 总累计收益率 |
| data.items | array | 按基金拆分的收益明细 |
| data.items[].fund_id | int | 基金 ID |
| data.items[].fund_name | string | 基金名称 |
| data.items[].fund_code | string | 基金代码 |
| data.items[].shares | number | 当前份额 |
| data.items[].cost_amount | number | 当前成本 |
| data.items[].nav | number / null | 指定日期当天的净值 |
| data.items[].nav_date | string / null | 净值日期 |
| data.items[].market_value | number / null | 市值 |
| data.items[].profit_amount | number / null | 收益金额 |
| data.items[].return_rate | number / null | 累计收益率 |

### 成功响应示例

HTTP 状态码 `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "blogger_id": 1,
    "blogger_name": "基金小星",
    "return_date": "2026-09-30",
    "total_cost_amount": 27940.00,
    "total_market_value": 30480.00,
    "profit_amount": 2540.00,
    "return_rate": 0.090909,
    "items": [
      {
        "fund_id": 101,
        "fund_name": "华夏成长混合",
        "fund_code": "000001",
        "shares": 12700.0000,
        "cost_amount": 27940.00,
        "nav": 2.4000,
        "nav_date": "2026-09-30",
        "market_value": 30480.00,
        "profit_amount": 2540.00,
        "return_rate": 0.090909
      }
    ]
  }
}
```

### 缺净值响应示例

HTTP 状态码仍为 `200`。缺净值不是请求失败，而是数据缺失：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "blogger_id": 1,
    "blogger_name": "基金小星",
    "return_date": "2026-09-30",
    "total_cost_amount": 27940.00,
    "total_market_value": null,
    "profit_amount": null,
    "return_rate": null,
    "items": [
      {
        "fund_id": 101,
        "fund_name": "华夏成长混合",
        "fund_code": "000001",
        "shares": 12700.0000,
        "cost_amount": 27940.00,
        "nav": null,
        "nav_date": null,
        "market_value": null,
        "profit_amount": null,
        "return_rate": null
      }
    ]
  }
}
```

### 错误响应示例

博主 ID 非法，HTTP `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "blogger_id",
      "message": "博主 ID 必须为正整数"
    }
  ]
}
```

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

博主不存在，HTTP `404`：

```json
{
  "code": "BLOGGER_NOT_FOUND",
  "message": "博主不存在",
  "details": []
}
```

### 业务规则

1. 只统计 `return_date` 当天或之前的初始持仓和操作记录。**关于"初始持仓"的部分，按 2.6 节覆盖：同一博主同一基金有多条初始持仓时，只取 `record_date` 最早的一条参与计算，其余完全不累加。**
2. 只使用 `return_date` 当天的净值，不使用最近一天净值兜底。
3. 博主存在但没有持仓和操作时，返回空明细和零值汇总。
4. 成本小于等于 `0` 时，收益率返回 `null`。同一场景下 `market_value` 和 `profit_amount` **照实返回数值**，见 2.4 节真值表。
5. 任意基金缺当天净值时，博主总市值、总收益金额和总收益率返回 `null`。
6. 空值判定一律以 2.4 节 null 真值表为准。

### 关联接口

- 持仓快照：`docs/api/v1-position-snapshots.md`
- 操作记录：`docs/api/v1-operations.md`
- 净值数据：`docs/api/v1-nav-history.md`

---

## 5. 查询单基金收益

### 接口名称

查询单基金收益 / `get_blogger_fund_return`

### 请求方法与路径

```http
GET /api/v1/bloggers/{blogger_id}/funds/{fund_id}/return
```

### 功能说明

计算某个博主持有某只基金的成本、市值、收益金额和累计收益率。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| blogger_id | int | 是 | `1` | 路径参数，博主 ID，必须为正整数 |
| fund_id | int | 是 | `101` | 路径参数，基金 ID，必须为正整数 |
| return_date | string | 否 | `2026-09-30` | 收益计算日期，格式 `YYYY-MM-DD`，不能晚于今天；不传时默认今天 |

### 请求示例

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers/1/funds/101/return?return_date=2026-09-30"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data.blogger_id | int | 博主 ID |
| data.blogger_name | string | 博主名称 |
| data.fund_id | int | 基金 ID |
| data.fund_name | string | 基金名称 |
| data.fund_code | string | 基金代码 |
| data.return_date | string | 收益计算日期 |
| data.shares | number | 当前份额 |
| data.cost_amount | number | 当前成本 |
| data.nav | number / null | 指定日期当天的净值 |
| data.nav_date | string / null | 净值日期 |
| data.market_value | number / null | 市值 |
| data.profit_amount | number / null | 收益金额 |
| data.return_rate | number / null | 累计收益率 |

### 成功响应示例

HTTP 状态码 `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "blogger_id": 1,
    "blogger_name": "基金小星",
    "fund_id": 101,
    "fund_name": "华夏成长混合",
    "fund_code": "000001",
    "return_date": "2026-09-30",
    "shares": 12700.0000,
    "cost_amount": 27940.00,
    "nav": 2.4000,
    "nav_date": "2026-09-30",
    "market_value": 30480.00,
    "profit_amount": 2540.00,
    "return_rate": 0.090909
  }
}
```

### 缺净值响应示例

HTTP 状态码 `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "blogger_id": 1,
    "blogger_name": "基金小星",
    "fund_id": 101,
    "fund_name": "华夏成长混合",
    "fund_code": "000001",
    "return_date": "2026-09-30",
    "shares": 12700.0000,
    "cost_amount": 27940.00,
    "nav": null,
    "nav_date": null,
    "market_value": null,
    "profit_amount": null,
    "return_rate": null
  }
}
```

### 错误响应示例

基金 ID 非法，HTTP `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "fund_id",
      "message": "基金 ID 必须为正整数"
    }
  ]
}
```

博主不存在，HTTP `404`：

```json
{
  "code": "BLOGGER_NOT_FOUND",
  "message": "博主不存在",
  "details": []
}
```

基金不存在，或该博主没有这只基金的持仓数据，HTTP `404`：

```json
{
  "code": "FUND_NOT_FOUND",
  "message": "基金不存在，或该博主未持有该基金",
  "details": []
}
```

### 业务规则

1. 先确认博主存在，再确认基金存在。
2. 即使基金存在，如果该博主没有这只基金的初始持仓或操作记录，也返回 `FUND_NOT_FOUND`。
3. 只统计 `return_date` 当天或之前的初始持仓和操作记录。
4. 只使用 `return_date` 当天的净值，不使用最近一天净值兜底。
5. 成本小于等于 `0` 时，收益率返回 `null`。

### 关联接口

- 单博主累计收益：`GET /api/v1/bloggers/{blogger_id}/returns`
- 基金管理：`docs/api/v1-basic-management.md`
- 持仓快照：`docs/api/v1-position-snapshots.md`

---

## 6. 查询总体收益汇总

### 接口名称

查询总体收益汇总 / `get_total_returns_summary`

### 请求方法与路径

```http
GET /api/v1/returns/summary
```

### 功能说明

计算全部博主持仓的总成本、总市值、总收益金额和总累计收益率，并返回按博主拆分的汇总数据。

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
curl "http://127.0.0.1:5000/api/v1/returns/summary?return_date=2026-09-30"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data.return_date | string | 收益计算日期 |
| data.total_cost_amount | number | 所有博主的总成本 |
| data.total_market_value | number / null | 所有博主的总市值；任意基金缺当天净值时为 `null` |
| data.profit_amount | number / null | 所有博主的总收益金额 |
| data.return_rate | number / null | 所有博主的总累计收益率 |
| data.blogger_count | int | 有持仓收益数据的博主数量 |
| data.items | array | 按博主拆分的汇总列表 |
| data.items[].blogger_id | int | 博主 ID |
| data.items[].blogger_name | string | 博主名称 |
| data.items[].total_cost_amount | number | 该博主总成本 |
| data.items[].total_market_value | number / null | 该博主总市值 |
| data.items[].profit_amount | number / null | 该博主总收益金额 |
| data.items[].return_rate | number / null | 该博主总收益率 |
| data.items[].funds | array | 该博主按基金拆分的收益明细，字段同单博主接口的 `items` |

### 成功响应示例

HTTP 状态码 `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "return_date": "2026-09-30",
    "total_cost_amount": 27940.00,
    "total_market_value": 30480.00,
    "profit_amount": 2540.00,
    "return_rate": 0.090909,
    "blogger_count": 1,
    "items": [
      {
        "blogger_id": 1,
        "blogger_name": "基金小星",
        "total_cost_amount": 27940.00,
        "total_market_value": 30480.00,
        "profit_amount": 2540.00,
        "return_rate": 0.090909,
        "funds": [
          {
            "fund_id": 101,
            "fund_name": "华夏成长混合",
            "fund_code": "000001",
            "shares": 12700.0000,
            "cost_amount": 27940.00,
            "nav": 2.4000,
            "nav_date": "2026-09-30",
            "market_value": 30480.00,
            "profit_amount": 2540.00,
            "return_rate": 0.090909
          }
        ]
      }
    ]
  }
}
```

### 空数据响应示例

系统里没有任何博主，或没有任何可计算的持仓数据时，HTTP `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "return_date": "2026-09-30",
    "total_cost_amount": 0.00,
    "total_market_value": 0.00,
    "profit_amount": 0.00,
    "return_rate": null,
    "blogger_count": 0,
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
2. 没有持仓数据的博主不进入 `items`，也不计入 `blogger_count`。
3. `blogger_count` 表示有持仓收益数据的博主数量，不是博主表里的全部博主数量。
4. 只使用 `return_date` 当天的净值，不使用最近一天净值兜底。
5. 任意基金缺当天净值时，对应博主和总体汇总的市值、收益金额、收益率都返回 `null`。
6. 总成本不依赖净值，缺净值时仍然可以返回。

### 关联接口

- 单博主累计收益：`GET /api/v1/bloggers/{blogger_id}/returns`
- 博主管理：`docs/api/v1-basic-management.md`
- 持仓快照：`docs/api/v1-position-snapshots.md`

---

## 7. 变更记录

| 日期 | 版本 | 说明 |
| --- | --- | --- |
| 2026-09-30 | v1.0 | 初始化简单收益查询接口文档 |
