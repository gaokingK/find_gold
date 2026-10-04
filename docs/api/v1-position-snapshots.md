# 持仓快照接口文档

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 版本 | v1.0 |
| 状态 | 已确认 |
| 日期 | 2026-09-30 |
| 对应计划 | 第 5–9 天功能闭环计划「持仓快照」 |
| 后端框架 | Flask |
| 数据库 | MySQL |
| API 前缀 | `/api/v1/` |

本文档是持仓快照模块前后端联调的唯一契约。  
字段发生任何变更，必须先改本文档，再改代码，并通知前端。

---

## 1. 全局约定

本模块沿用 `docs/api/v1-basic-management.md` 的全局约定：

1. 请求体和响应体都使用 `application/json`。
2. 日期字段格式为 `YYYY-MM-DD`。
3. 统一成功响应：`{"code": 0, "message": "ok", "data": {}}`。
4. 统一错误响应：`{"code": "错误码", "message": "提示", "details": []}`。
5. 第一版不做用户认证。

### 1.1 成功响应的 HTTP 状态码

本项目所有接口的成功响应统一使用 `200`。  
前端判断成功与失败只依据响应体中的 `code` 字段。

### 1.2 本模块 HTTP 状态码

| HTTP 状态码 | 含义 |
| --- | --- |
| 200 | 成功 |
| 400 | 参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 1.3 本模块错误码

| 错误码 | HTTP 状态码 | 说明 |
| --- | --- | --- |
| `VALIDATION_ERROR` | 400 | 路径参数或日期参数校验失败 |
| `BLOGGER_NOT_FOUND` | 404 | 博主不存在 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

---

## 2. 接口总览

| 序号 | 接口 | 方法 | 路径 |
| --- | --- | --- | --- |
| 1 | 查询博主持仓快照 | GET | `/api/v1/bloggers/{blogger_id}/position-snapshots` |

第一版不提供：

- 创建快照接口
- 编辑快照接口
- 删除快照接口
- 持仓快照历史持久化

---

## 3. 查询博主持仓快照

### 接口名称

查询博主持仓快照 / `get_position_snapshots`

### 请求方法与路径

```http
GET /api/v1/bloggers/{blogger_id}/position-snapshots
```

### 功能说明

根据初始持仓和截至指定日期的操作记录，实时计算某个博主持有的每只基金的份额和成本。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| blogger_id | int | 是 | `1` | 路径参数，博主 ID，必须为正整数 |
| snapshot_date | string | 否 | `2026-09-30` | 快照日期，格式 `YYYY-MM-DD`，不能晚于今天；不传时默认今天 |

### 请求示例

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers/1/position-snapshots?snapshot_date=2026-09-30"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data.blogger_id | int | 博主 ID |
| data.blogger_name | string | 博主名称 |
| data.snapshot_date | string | 快照日期 |
| data.items | array | 按基金分组的持仓快照列表 |
| data.items[].fund_id | int | 基金 ID |
| data.items[].fund_name | string | 基金名称 |
| data.items[].fund_code | string | 基金代码 |
| data.items[].initial_record_date | string / null | 初始持仓记录日期；没有初始持仓时为 `null` |
| data.items[].initial_shares | number | 初始份额 |
| data.items[].initial_cost_amount | number | 初始成本金额 |
| data.items[].buy_shares | number | 累计买入份额 |
| data.items[].buy_amount | number | 累计买入金额 |
| data.items[].sell_shares | number | 累计卖出份额 |
| data.items[].sell_amount | number | 累计卖出金额 |
| data.items[].dividend_cash_amount | number | 累计现金分红金额 |
| data.items[].shares | number | 当前份额 |
| data.items[].cost_amount | number | 当前成本金额 |

### 成功响应示例

HTTP 状态码 `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "blogger_id": 1,
    "blogger_name": "基金小星",
    "snapshot_date": "2026-09-30",
    "items": [
      {
        "fund_id": 101,
        "fund_name": "华夏成长混合",
        "fund_code": "000001",
        "initial_record_date": "2026-01-01",
        "initial_shares": 12000,
        "initial_cost_amount": 15600,
        "buy_shares": 1000,
        "buy_amount": 13000,
        "sell_shares": 300,
        "sell_amount": 4200,
        "dividend_cash_amount": 120,
        "shares": 12700,
        "cost_amount": 27940
      }
    ]
  }
}
```

### 空数据响应示例

博主存在，但没有持仓和操作时返回空列表：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "blogger_id": 1,
    "blogger_name": "基金小星",
    "snapshot_date": "2026-09-30",
    "items": []
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

快照日期格式错误，HTTP `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "snapshot_date",
      "message": "快照日期格式必须是 YYYY-MM-DD"
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

---

## 4. 业务规则

1. 持仓快照实时计算，不落库。
2. 只统计初始持仓和截至快照日期的操作记录。
3. 同一 `blogger_id + fund_id` 有多条初始持仓时，第一版取最早一条作为起点。
4. 卖出使用平均成本法。
5. 现金分红不改变份额和成本。
6. 第一版不校验超额卖出。份额可以为负，成本也可以为 0 或负数。
7. 第一版不返回市值、收益金额和收益率，这些属于第 8 天的收益计算模块。

---

## 5. 关联接口

- 博主管理：`docs/api/v1-basic-management.md`
- 操作记录：`docs/api/v1-operations.md`
- 净值数据：`docs/api/v1-nav-history.md`

---

## 6. 变更记录

| 日期 | 版本 | 说明 |
| --- | --- | --- |
| 2026-09-30 | v1.0 | 初始化持仓快照接口文档 |
