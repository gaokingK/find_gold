# 操作记录接口文档

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 版本 | v1.0 |
| 状态 | 已确认 |
| 日期 | 2026-09-30 |
| 对应需求 | 第 5–9 天功能闭环计划「日常操作记录」 |
| 对应表设计 | `docs/backend/design/operations-table-design.md` |
| 后端框架 | Flask |
| 数据库 | MySQL |
| API 前缀 | `/api/v1/` |

本文档是操作记录模块前后端联调的唯一契约。  
字段发生任何变更，必须先改本文档，再改代码，并通知前端。

---

## 1. 全局约定

本模块沿用 `docs/api/v1-basic-management.md` 的全局约定：

1. 请求体和响应体都使用 `application/json`。
2. 日期字段格式为 `YYYY-MM-DD`，时间字段格式为 `YYYY-MM-DD HH:mm:ss`。
3. 金额和份额使用数字类型传输，后端落库时使用 `DECIMAL`。
4. 统一成功响应：`{"code": 0, "message": "ok", "data": {}}`。
5. 统一错误响应：`{"code": "错误码", "message": "提示", "details": []}`。
6. 第一版不做用户认证。

### 1.1 成功响应的 HTTP 状态码

本项目所有接口的成功响应统一使用 `200`，**新增类接口也返回 `200`，不使用 `201`**。  
前端判断成功与失败只依据响应体中的 `code` 字段。

### 1.2 本模块 HTTP 状态码

| HTTP 状态码 | 含义 |
| --- | --- |
| 200 | 成功 |
| 400 | 参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

本模块没有 `409`：同一博主、同一基金、同一天允许多笔操作，不做唯一约束。

### 1.3 本模块错误码

| 错误码 | HTTP 状态码 | 说明 |
| --- | --- | --- |
| `VALIDATION_ERROR` | 400 | 参数校验失败 |
| `BLOGGER_NOT_FOUND` | 404 | 博主不存在 |
| `FUND_NOT_FOUND` | 404 | 基金不存在 |
| `OPERATION_NOT_FOUND` | 404 | 操作记录不存在 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

### 1.4 操作类型

| operation_type | 中文含义 | 份额影响 | 说明 |
| --- | --- | --- | --- |
| `buy` | 买入 | 份额增加 | 记录买入份额和买入金额 |
| `sell` | 卖出 | 份额减少 | 记录卖出份额和卖出金额 |
| `dividend_cash` | 现金分红 | 不变 | 只记录分红金额 |

第一版不支持：手续费、税费、红利再投资、基金拆分合并、自动调仓、净值复权。

---

## 2. 接口总览

| 序号 | 接口 | 方法 | 路径 |
| --- | --- | --- | --- |
| 1 | 新增操作记录 | POST | `/api/v1/operations` |
| 2 | 查询操作记录列表 | GET | `/api/v1/operations` |
| 3 | 删除操作记录 | DELETE | `/api/v1/operations/{operation_id}` |

第一版**不提供**：

- 单条详情接口 `GET /api/v1/operations/{operation_id}`
- 编辑接口 `PUT /api/v1/operations/{operation_id}`

录错的记录先删除再重新录入。编辑接口的口径见 `docs/backend/plans/backend-task-backlog.md`。

---

## 3. 操作记录对象

所有接口返回的单条操作记录结构一致：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| operation_id | int | 操作记录 ID |
| blogger_id | int | 博主 ID |
| blogger_name | string | 博主名称，来自 `bloggers` 表 |
| fund_id | int | 基金 ID |
| fund_name | string | 基金名称，来自 `funds` 表 |
| fund_code | string | 基金代码，来自 `funds` 表 |
| operation_type | string | `buy` / `sell` / `dividend_cash` |
| operation_date | string | 操作日期，`YYYY-MM-DD` |
| shares | number | 份额，现金分红固定为 `0` |
| amount | number | 金额，单位元 |
| remark | string / null | 备注，最多 255 字符 |
| created_at | string | 创建时间 |
| updated_at | string | 更新时间 |

示例：

```json
{
  "operation_id": 1,
  "blogger_id": 1,
  "blogger_name": "验收博主A",
  "fund_id": 1,
  "fund_name": "华夏成长混合",
  "fund_code": "000001",
  "operation_type": "buy",
  "operation_date": "2026-09-30",
  "shares": 1000.0,
  "amount": 13000.0,
  "remark": "第一次买入",
  "created_at": "2026-09-30 10:00:00",
  "updated_at": "2026-09-30 10:00:00"
}
```

---

## 4. 新增操作记录

### 接口名称

新增操作记录 / `create_operation`

### 请求方法与路径

```http
POST /api/v1/operations
```

### 功能说明

为某个博主、某只基金新增一条买入、卖出或现金分红记录。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| blogger_id | int | 是 | `1` | 博主 ID，必须为正整数且博主必须存在 |
| fund_id | int | 是 | `1` | 基金 ID，必须为正整数且基金必须存在 |
| operation_type | string | 是 | `buy` | 只允许 `buy`、`sell`、`dividend_cash` |
| operation_date | string | 是 | `2026-09-30` | 格式 `YYYY-MM-DD`，不能晚于今天，不能早于该博主该基金的初始持仓记录日期 |
| shares | number | 条件必填 | `1000` | `buy`、`sell` 必填且大于 0；`dividend_cash` 可不传，传了必须等于 0 |
| amount | number | 是 | `13000` | 必须大于 0 |
| remark | string | 否 | `第一次买入` | 最多 255 字符 |

### 请求示例

买入：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"operation_type":"buy","operation_date":"2026-09-30","shares":1000,"amount":13000,"remark":"第一次买入"}'
```

卖出：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"operation_type":"sell","operation_date":"2026-09-30","shares":300,"amount":4200,"remark":"部分卖出"}'
```

现金分红（不传 `shares`）：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"operation_type":"dividend_cash","operation_date":"2026-09-30","amount":120,"remark":"现金分红"}'
```

### 响应字段

`data` 是一个操作记录对象，字段见第 3 节。

### 成功响应示例

HTTP 状态码 `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "operation_id": 1,
    "blogger_id": 1,
    "blogger_name": "验收博主A",
    "fund_id": 1,
    "fund_name": "华夏成长混合",
    "fund_code": "000001",
    "operation_type": "buy",
    "operation_date": "2026-09-30",
    "shares": 1000.0,
    "amount": 13000.0,
    "remark": "第一次买入",
    "created_at": "2026-09-30 10:00:00",
    "updated_at": "2026-09-30 10:00:00"
  }
}
```

### 错误响应示例

非法操作类型，HTTP 状态码 `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "operation_type",
      "message": "操作类型只允许 buy、sell、dividend_cash"
    }
  ]
}
```

操作日期晚于今天，HTTP 状态码 `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "operation_date",
      "message": "操作日期不能晚于今天"
    }
  ]
}
```

操作日期早于初始持仓记录日期，HTTP 状态码 `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "operation_date",
      "message": "操作日期不能早于该博主该基金的初始持仓记录日期 2026-09-01"
    }
  ]
}
```

博主不存在，HTTP 状态码 `404`：

```json
{
  "code": "BLOGGER_NOT_FOUND",
  "message": "博主不存在",
  "details": []
}
```

基金不存在，HTTP 状态码 `404`：

```json
{
  "code": "FUND_NOT_FOUND",
  "message": "基金不存在",
  "details": []
}
```

### 业务规则

1. `blogger_id` 和 `fund_id` 必须在数据库中存在，否则返回 404。
2. `buy` 和 `sell`：`shares` 和 `amount` 都必须大于 0。
3. `dividend_cash`：`shares` 可不传，等价于 `0`；传了必须等于 0；`amount` 必须大于 0。
4. `operation_date` 不能晚于今天，避免录入未来操作污染持仓快照。
5. 如果该博主该基金已有初始持仓记录，`operation_date` 不能早于初始持仓的 `record_date`。持仓快照以初始持仓为起点，早于起点的操作会被重复计入。
6. 如果该博主该基金没有初始持仓记录，不限制 `operation_date` 的下界。
7. 同一博主、同一基金、同一天允许多笔操作，不做唯一约束。
8. **第一版不校验卖出份额是否超过当前持有份额。** 超额卖出会让持仓快照出现负份额、成本出现 0 或负数。此时收益率接口返回 `null`，详见「持仓快照」和「收益计算」接口文档。
9. 本接口只记录操作，不改写 `initial_positions`，也不落库持仓快照。

### 关联接口

- 查询操作记录列表：`GET /api/v1/operations`
- 删除操作记录：`DELETE /api/v1/operations/{operation_id}`
- 查询博主列表：`GET /api/v1/bloggers`
- 查询基金列表：`GET /api/v1/funds`
- 查询初始持仓列表：`GET /api/v1/initial-positions`

---

## 5. 查询操作记录列表

### 接口名称

查询操作记录列表 / `list_operations`

### 请求方法与路径

```http
GET /api/v1/operations
```

### 功能说明

分页查询操作记录，支持按博主、基金、操作类型、日期区间和备注关键字筛选。

### 请求头

无特殊要求。

### 请求参数

全部通过 query string 传递，全部可选。

| 字段 | 类型 | 是否必填 | 默认值 | 示例值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| blogger_id | int | 否 | 无 | `1` | 按博主筛选，必须为正整数 |
| fund_id | int | 否 | 无 | `1` | 按基金筛选，必须为正整数 |
| operation_type | string | 否 | 无 | `buy` | 只允许 `buy`、`sell`、`dividend_cash` |
| date_from | string | 否 | 无 | `2026-09-01` | 起始操作日期，格式 `YYYY-MM-DD`，含当天 |
| date_to | string | 否 | 无 | `2026-09-30` | 结束操作日期，格式 `YYYY-MM-DD`，含当天 |
| keyword | string | 否 | 空 | `第一次` | 备注模糊搜索 |
| page | int | 否 | `1` | `1` | 页码，必须大于 0 |
| page_size | int | 否 | `20` | `20` | 每页条数，范围 1–100 |
| sort_by | string | 否 | `created_at` | `operation_date` | 只允许 `operation_date`、`amount`、`created_at` |
| order | string | 否 | `desc` | `desc` | 只允许 `asc`、`desc` |

### 请求示例

```bash
curl "http://127.0.0.1:5000/api/v1/operations?blogger_id=1&operation_type=buy&date_from=2026-09-01&date_to=2026-09-30&page=1&page_size=20&sort_by=operation_date&order=desc"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| data.items | array | 操作记录数组，元素结构见第 3 节 |
| data.page | int | 当前页码 |
| data.page_size | int | 每页条数 |
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
        "operation_id": 1,
        "blogger_id": 1,
        "blogger_name": "验收博主A",
        "fund_id": 1,
        "fund_name": "华夏成长混合",
        "fund_code": "000001",
        "operation_type": "buy",
        "operation_date": "2026-09-30",
        "shares": 1000.0,
        "amount": 13000.0,
        "remark": "第一次买入",
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

没有数据时返回空数组，不返回 404：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [],
    "page": 1,
    "page_size": 20,
    "total": 0
  }
}
```

### 错误响应示例

非法排序字段，HTTP 状态码 `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "sort_by",
      "message": "排序字段只允许 operation_date、amount、created_at"
    }
  ]
}
```

分页参数越界，HTTP 状态码 `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "page_size",
      "message": "page_size 必须在 1 到 100 之间"
    }
  ]
}
```

日期区间颠倒，HTTP 状态码 `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "date_from",
      "message": "date_from 不能晚于 date_to"
    }
  ]
}
```

### 业务规则

1. 多个筛选条件之间是「同时满足」关系。
2. `date_from` 和 `date_to` 都包含当天。
3. `date_from` 不能晚于 `date_to`。
4. `sort_by` 和 `order` 都使用白名单校验，非白名单值返回 400，不允许拼接进 SQL。
5. `page_size` 上限为 100。
6. 排序结果在同一排序值内按 `operation_id` 倒序，保证分页稳定。
7. 筛选条件指向不存在的博主或基金时，返回空列表，不返回 404。

### 关联接口

- 新增操作记录：`POST /api/v1/operations`
- 删除操作记录：`DELETE /api/v1/operations/{operation_id}`

---

## 6. 删除操作记录

### 接口名称

删除操作记录 / `delete_operation`

### 请求方法与路径

```http
DELETE /api/v1/operations/{operation_id}
```

### 功能说明

删除一条录错的操作记录。第一版没有编辑接口，修正数据的方式是「删除 + 重新新增」。

### 请求头

无特殊要求。

### 请求参数

| 字段 | 位置 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| operation_id | 路径 | int | 是 | `1` | 操作记录 ID，必须为正整数 |

### 请求示例

```bash
curl -X DELETE "http://127.0.0.1:5000/api/v1/operations/1"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| data.operation_id | int | 被删除的操作记录 ID |

### 成功响应示例

HTTP 状态码 `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "operation_id": 1
  }
}
```

### 错误响应示例

ID 非法，HTTP 状态码 `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "operation_id",
      "message": "操作记录 ID 必须为正整数"
    }
  ]
}
```

记录不存在，HTTP 状态码 `404`：

```json
{
  "code": "OPERATION_NOT_FOUND",
  "message": "操作记录不存在",
  "details": []
}
```

### 业务规则

1. 删除是物理删除，不做软删除，不保留删除痕迹。
2. 删除操作记录不影响 `bloggers`、`funds`、`initial_positions` 的数据。
3. 因为第一版持仓快照是实时计算、不落库，删除后下一次查询快照就会反映新结果，不需要重算。
4. 重复删除同一个 ID，第二次返回 `OPERATION_NOT_FOUND`。
5. 删除博主时会级联删除该博主的操作记录，详见博主删除接口。

### 关联接口

- 新增操作记录：`POST /api/v1/operations`
- 查询操作记录列表：`GET /api/v1/operations`
- 删除博主：`DELETE /api/v1/bloggers/{blogger_id}`

---

## 7. 变更记录

| 日期 | 版本 | 变更内容 |
| --- | --- | --- |
| 2026-09-30 | v1.0 | 首版：新增、查询、删除三个接口 |
