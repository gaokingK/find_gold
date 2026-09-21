# 第一版基础数据管理接口文档

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 版本 | v1.0 |
| 状态 | 已确认 |
| 日期 | 2026-09-21 |
| 对应需求文档 | `docs/requirements/v1-basic-management.md` |
| 后端框架 | Flask |
| 数据库 | MySQL |
| API 前缀 | `/api/v1/` |

---

## 1. 全局约定

### 1.1 请求格式

除非特别说明：

1. 请求体使用 `application/json`。
2. 响应体使用 `application/json`。
3. 日期字段格式为 `YYYY-MM-DD`。
4. 时间字段格式为 `YYYY-MM-DD HH:mm:ss`。
5. 金额和份额使用数字类型传输，后端落库时使用 `DECIMAL`。

---

### 1.2 认证方式

第一版不做用户认证。

所有接口暂不要求 `Authorization` 请求头。

---

### 1.3 统一成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data | object / array / null | 业务数据 |

---

### 1.4 统一错误响应

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "name",
      "message": "博主名称不能为空"
    }
  ]
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | string | 错误码 |
| message | string | 用户可读的错误提示 |
| details | array | 可选，详细校验错误 |

---

### 1.5 常用 HTTP 状态码

| HTTP 状态码 | 含义 |
| --- | --- |
| 200 | 成功 |
| 400 | 参数错误 |
| 404 | 资源不存在 |
| 409 | 业务冲突 |
| 500 | 服务器内部错误 |

---

### 1.6 常用错误码

| 错误码 | 说明 |
| --- | --- |
| `VALIDATION_ERROR` | 参数校验失败 |
| `BLOGGER_NOT_FOUND` | 博主不存在 |
| `FUND_NOT_FOUND` | 基金不存在 |
| `INITIAL_POSITION_NOT_FOUND` | 初始持仓不存在 |
| `BLOGGER_NAME_DUPLICATED` | 博主名称重复 |
| `FUND_CODE_DUPLICATED` | 基金代码重复 |
| `INITIAL_POSITION_DUPLICATED` | 同一博主、同一基金、同一记录日期的初始持仓已存在 |
| `INTERNAL_ERROR` | 服务器内部错误 |

---

## 2. 接口总览

| 序号 | 接口 | 方法 | 路径 |
| --- | --- | --- | --- |
| 1 | 查询博主列表 | GET | `/api/v1/bloggers` |
| 2 | 新增博主 | POST | `/api/v1/bloggers` |
| 3 | 查询博主详情 | GET | `/api/v1/bloggers/{blogger_id}` |
| 4 | 编辑博主 | PUT | `/api/v1/bloggers/{blogger_id}` |
| 5 | 删除博主 | DELETE | `/api/v1/bloggers/{blogger_id}` |
| 6 | 查询基金列表 | GET | `/api/v1/funds` |
| 7 | 新增基金 | POST | `/api/v1/funds` |
| 8 | 编辑基金 | PUT | `/api/v1/funds/{fund_id}` |
| 9 | 查询初始持仓列表 | GET | `/api/v1/initial-positions` |
| 10 | 新增初始持仓 | POST | `/api/v1/initial-positions` |
| 11 | 编辑初始持仓 | PUT | `/api/v1/initial-positions/{initial_position_id}` |

---

## 3. 博主管理接口

## 3.1 查询博主列表

### 接口名称

查询博主列表 / `list_bloggers`

### 请求方法与路径

```http
GET /api/v1/bloggers
```

### 功能说明

分页查询博主列表，支持关键字、板块、状态筛选和排序。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| keyword | string | 否 | `小星` | 按博主名称模糊搜索 |
| sector | string | 否 | `成长股` | 按板块精确筛选 |
| status | string | 否 | `observing` | 可选值：`observing`、`active` |
| page | int | 否 | `1` | 页码，默认 `1` |
| page_size | int | 否 | `20` | 每页数量，默认 `20`，最大 `100` |
| sort_by | string | 否 | `observe_days` | 支持值：`name`、`observe_start_date`、`observe_days`、`created_at` |
| order | string | 否 | `desc` | 支持值：`asc`、`desc` |

### 请求示例

```bash
curl "http://localhost:5000/api/v1/bloggers?page=1&page_size=20&status=observing"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data.items | array | 博主列表 |
| data.items[].blogger_id | int | 博主 ID |
| data.items[].name | string | 博主名称 |
| data.items[].sector | string | 所属板块 |
| data.items[].observe_start_date | string | 观察开始日 |
| data.items[].observe_days | int | 观察天数 |
| data.items[].status | string | 状态：`observing` 或 `active` |
| data.items[].created_at | string | 创建时间 |
| data.items[].updated_at | string | 更新时间 |
| data.page | int | 当前页码 |
| data.page_size | int | 每页数量 |
| data.total | int | 总记录数 |

### 成功响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "blogger_id": 1,
        "name": "基金小星",
        "sector": "成长股",
        "observe_start_date": "2026-03-22",
        "observe_days": 183,
        "status": "active",
        "created_at": "2026-09-21 10:00:00",
        "updated_at": "2026-09-21 10:00:00"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

### 错误响应示例

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "page",
      "message": "页码必须大于等于 1"
    }
  ]
}
```

```json
{
  "code": "INTERNAL_ERROR",
  "message": "服务器内部错误",
  "details": []
}
```

### 业务规则

1. `page` 默认为 `1`，最小值为 `1`。
2. `page_size` 默认为 `20`，最大值为 `100`。
3. `status` 只允许 `observing` 和 `active`。
4. `observe_days` 和 `status` 由后端根据 `observe_start_date` 计算。
5. 观察天数小于 30 天时，`status` 为 `observing`。
6. 观察天数大于等于 30 天时，`status` 为 `active`。

### 关联接口

- 新增博主：`POST /api/v1/bloggers`
- 查询博主详情：`GET /api/v1/bloggers/{blogger_id}`
- 编辑博主：`PUT /api/v1/bloggers/{blogger_id}`
- 删除博主：`DELETE /api/v1/bloggers/{blogger_id}`
- 查询初始持仓列表：`GET /api/v1/initial-positions`

---

## 3.2 新增博主

### 接口名称

新增博主 / `create_blogger`

### 请求方法与路径

```http
POST /api/v1/bloggers
```

### 功能说明

新增一个博主。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| name | string | 是 | `基金小星` | 博主名称，不能为空，不能重复 |
| sector | string | 是 | `成长股` | 所属板块，不能为空 |
| observe_start_date | string | 是 | `2026-09-21` | 观察开始日，格式 `YYYY-MM-DD` |

### 请求示例

```bash
curl -X POST "http://localhost:5000/api/v1/bloggers" \
  -H "Content-Type: application/json" \
  -d '{"name":"基金小星","sector":"成长股","observe_start_date":"2026-09-21"}'
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data.blogger_id | int | 博主 ID |
| data.name | string | 博主名称 |
| data.sector | string | 所属板块 |
| data.observe_start_date | string | 观察开始日 |
| data.observe_days | int | 观察天数 |
| data.status | string | 状态 |
| data.created_at | string | 创建时间 |
| data.updated_at | string | 更新时间 |

### 成功响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "blogger_id": 1,
    "name": "基金小星",
    "sector": "成长股",
    "observe_start_date": "2026-09-21",
    "observe_days": 0,
    "status": "observing",
    "created_at": "2026-09-21 10:00:00",
    "updated_at": "2026-09-21 10:00:00"
  }
}
```

### 错误响应示例

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "name",
      "message": "博主名称不能为空"
    }
  ]
}
```

```json
{
  "code": "BLOGGER_NAME_DUPLICATED",
  "message": "博主名称已存在",
  "details": []
}
```

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "observe_start_date",
      "message": "观察开始日格式必须为 YYYY-MM-DD"
    }
  ]
}
```

### 业务规则

1. `name` 必填且不能重复。
2. `sector` 必填。
3. `observe_start_date` 必填，且必须能解析为合法日期。
4. 新增成功后返回完整博主信息。
5. 观察开始日当天，`observe_days` 为 `0`。

### 关联接口

- 查询博主列表：`GET /api/v1/bloggers`
- 查询博主详情：`GET /api/v1/bloggers/{blogger_id}`
- 编辑博主：`PUT /api/v1/bloggers/{blogger_id}`
- 删除博主：`DELETE /api/v1/bloggers/{blogger_id}`
- 新增初始持仓：`POST /api/v1/initial-positions`

---

## 3.3 查询博主详情

### 接口名称

查询博主详情 / `get_blogger_detail`

### 请求方法与路径

```http
GET /api/v1/bloggers/{blogger_id}
```

### 功能说明

查询单个博主的基础信息。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| blogger_id | int | 是 | `1` | 路径参数，博主 ID |

### 请求示例

```bash
curl "http://localhost:5000/api/v1/bloggers/1"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data.blogger_id | int | 博主 ID |
| data.name | string | 博主名称 |
| data.sector | string | 所属板块 |
| data.observe_start_date | string | 观察开始日 |
| data.observe_days | int | 观察天数 |
| data.status | string | 状态 |
| data.created_at | string | 创建时间 |
| data.updated_at | string | 更新时间 |

### 成功响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "blogger_id": 1,
    "name": "基金小星",
    "sector": "成长股",
    "observe_start_date": "2026-03-22",
    "observe_days": 183,
    "status": "active",
    "created_at": "2026-09-21 10:00:00",
    "updated_at": "2026-09-21 10:00:00"
  }
}
```

### 错误响应示例

```json
{
  "code": "BLOGGER_NOT_FOUND",
  "message": "博主不存在",
  "details": []
}
```

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

### 业务规则

1. `blogger_id` 必须是正整数。
2. 博主不存在时返回 `404`。
3. `observe_days` 和 `status` 实时计算。

### 关联接口

- 查询博主列表：`GET /api/v1/bloggers`
- 编辑博主：`PUT /api/v1/bloggers/{blogger_id}`
- 删除博主：`DELETE /api/v1/bloggers/{blogger_id}`
- 查询初始持仓列表：`GET /api/v1/initial-positions`

---

## 3.4 编辑博主

### 接口名称

编辑博主 / `update_blogger`

### 请求方法与路径

```http
PUT /api/v1/bloggers/{blogger_id}
```

### 功能说明

修改博主名称、所属板块和观察开始日。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| blogger_id | int | 是 | `1` | 路径参数，博主 ID |
| name | string | 是 | `基金小星` | 博主名称，不能为空，不能重复 |
| sector | string | 是 | `成长股` | 所属板块 |
| observe_start_date | string | 是 | `2026-09-21` | 观察开始日 |

### 请求示例

```bash
curl -X PUT "http://localhost:5000/api/v1/bloggers/1" \
  -H "Content-Type: application/json" \
  -d '{"name":"基金小星","sector":"成长股","observe_start_date":"2026-09-21"}'
```

### 响应字段

响应字段与查询博主详情接口一致。

### 成功响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "blogger_id": 1,
    "name": "基金小星",
    "sector": "成长股",
    "observe_start_date": "2026-09-21",
    "observe_days": 0,
    "status": "observing",
    "created_at": "2026-09-21 10:00:00",
    "updated_at": "2026-09-21 10:00:01"
  }
}
```

### 错误响应示例

```json
{
  "code": "BLOGGER_NOT_FOUND",
  "message": "博主不存在",
  "details": []
}
```

```json
{
  "code": "BLOGGER_NAME_DUPLICATED",
  "message": "博主名称已存在",
  "details": []
}
```

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "sector",
      "message": "所属板块不能为空"
    }
  ]
}
```

### 业务规则

1. 本接口使用完整更新，`name`、`sector`、`observe_start_date` 都必须传。
2. 博主名称不能与其他博主重复。
3. 修改观察开始日后，后端需要重新计算 `observe_days` 和 `status`。

### 关联接口

- 查询博主详情：`GET /api/v1/bloggers/{blogger_id}`
- 删除博主：`DELETE /api/v1/bloggers/{blogger_id}`
- 查询初始持仓列表：`GET /api/v1/initial-positions`

---

## 3.5 删除博主

### 接口名称

删除博主 / `delete_blogger`

### 请求方法与路径

```http
DELETE /api/v1/bloggers/{blogger_id}
```

### 功能说明

删除博主，并级联删除该博主名下的初始持仓。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| blogger_id | int | 是 | `1` | 路径参数，博主 ID |

### 请求示例

```bash
curl -X DELETE "http://localhost:5000/api/v1/bloggers/1"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data | object | 固定为空对象 |

### 成功响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

### 错误响应示例

```json
{
  "code": "BLOGGER_NOT_FOUND",
  "message": "博主不存在",
  "details": []
}
```

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

### 业务规则

1. 删除博主时，级联删除该博主名下的初始持仓。
2. 本接口不做二次确认，二次确认由前端负责。
3. 第一版没有博主归档功能。

### 关联接口

- 查询博主列表：`GET /api/v1/bloggers`
- 查询博主详情：`GET /api/v1/bloggers/{blogger_id}`
- 查询初始持仓列表：`GET /api/v1/initial-positions`

---

## 4. 基金管理接口

## 4.1 查询基金列表

### 接口名称

查询基金列表 / `list_funds`

### 请求方法与路径

```http
GET /api/v1/funds
```

### 功能说明

分页查询基金列表，支持关键字搜索。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| keyword | string | 否 | `华夏` | 按基金名称或基金代码模糊搜索 |
| page | int | 否 | `1` | 页码，默认 `1` |
| page_size | int | 否 | `20` | 每页数量，默认 `20`，最大 `100` |

### 请求示例

```bash
curl "http://localhost:5000/api/v1/funds?page=1&page_size=20&keyword=华夏"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data.items | array | 基金列表 |
| data.items[].fund_id | int | 基金 ID |
| data.items[].name | string | 基金名称 |
| data.items[].fund_code | string | 基金代码 |
| data.items[].created_at | string | 创建时间 |
| data.items[].updated_at | string | 更新时间 |
| data.page | int | 当前页码 |
| data.page_size | int | 每页数量 |
| data.total | int | 总记录数 |

### 成功响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "fund_id": 101,
        "name": "华夏成长混合",
        "fund_code": "000001",
        "created_at": "2026-09-21 10:00:00",
        "updated_at": "2026-09-21 10:00:00"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

### 错误响应示例

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "page_size",
      "message": "每页数量不能超过 100"
    }
  ]
}
```

```json
{
  "code": "INTERNAL_ERROR",
  "message": "服务器内部错误",
  "details": []
}
```

### 业务规则

1. `keyword` 同时匹配基金名称和基金代码。
2. 第一版不做基金删除。
3. 返回结果默认按 `fund_id` 升序排序。

### 关联接口

- 新增基金：`POST /api/v1/funds`
- 编辑基金：`PUT /api/v1/funds/{fund_id}`
- 新增初始持仓：`POST /api/v1/initial-positions`
- 查询初始持仓列表：`GET /api/v1/initial-positions`

---

## 4.2 新增基金

### 接口名称

新增基金 / `create_fund`

### 请求方法与路径

```http
POST /api/v1/funds
```

### 功能说明

新增一个基金。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| name | string | 是 | `华夏成长混合` | 基金名称，不能为空 |
| fund_code | string | 是 | `000001` | 基金代码，不能为空，不能重复 |

### 请求示例

```bash
curl -X POST "http://localhost:5000/api/v1/funds" \
  -H "Content-Type: application/json" \
  -d '{"name":"华夏成长混合","fund_code":"000001"}'
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data.fund_id | int | 基金 ID |
| data.name | string | 基金名称 |
| data.fund_code | string | 基金代码 |
| data.created_at | string | 创建时间 |
| data.updated_at | string | 更新时间 |

### 成功响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "fund_id": 101,
    "name": "华夏成长混合",
    "fund_code": "000001",
    "created_at": "2026-09-21 10:00:00",
    "updated_at": "2026-09-21 10:00:00"
  }
}
```

### 错误响应示例

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "fund_code",
      "message": "基金代码不能为空"
    }
  ]
}
```

```json
{
  "code": "FUND_CODE_DUPLICATED",
  "message": "基金代码已存在",
  "details": []
}
```

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "name",
      "message": "基金名称不能为空"
    }
  ]
}
```

### 业务规则

1. `name` 必填。
2. `fund_code` 必填且不能重复。
3. 第一版不限制基金代码格式，但建议使用数字或数字与字母组合。

### 关联接口

- 查询基金列表：`GET /api/v1/funds`
- 编辑基金：`PUT /api/v1/funds/{fund_id}`
- 新增初始持仓：`POST /api/v1/initial-positions`
- 查询初始持仓列表：`GET /api/v1/initial-positions`

---

## 4.3 编辑基金

### 接口名称

编辑基金 / `update_fund`

### 请求方法与路径

```http
PUT /api/v1/funds/{fund_id}
```

### 功能说明

修改基金名称和基金代码。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| fund_id | int | 是 | `101` | 路径参数，基金 ID |
| name | string | 是 | `华夏成长混合` | 基金名称 |
| fund_code | string | 是 | `000001` | 基金代码，不能重复 |

### 请求示例

```bash
curl -X PUT "http://localhost:5000/api/v1/funds/101" \
  -H "Content-Type: application/json" \
  -d '{"name":"华夏成长混合","fund_code":"000001"}'
```

### 响应字段

响应字段与新增基金接口一致。

### 成功响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "fund_id": 101,
    "name": "华夏成长混合",
    "fund_code": "000001",
    "created_at": "2026-09-21 10:00:00",
    "updated_at": "2026-09-21 10:00:01"
  }
}
```

### 错误响应示例

```json
{
  "code": "FUND_NOT_FOUND",
  "message": "基金不存在",
  "details": []
}
```

```json
{
  "code": "FUND_CODE_DUPLICATED",
  "message": "基金代码已存在",
  "details": []
}
```

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "fund_code",
      "message": "基金代码不能为空"
    }
  ]
}
```

### 业务规则

1. 本接口使用完整更新，`name` 和 `fund_code` 都必须传。
2. `fund_code` 不能与其他基金重复。
3. 基金编辑后，初始持仓列表应通过关联查询返回最新基金名称和基金代码。

### 关联接口

- 查询基金列表：`GET /api/v1/funds`
- 新增基金：`POST /api/v1/funds`
- 查询初始持仓列表：`GET /api/v1/initial-positions`

---

## 5. 初始持仓接口

## 5.1 查询初始持仓列表

### 接口名称

查询初始持仓列表 / `list_initial_positions`

### 请求方法与路径

```http
GET /api/v1/initial-positions
```

### 功能说明

分页查询初始持仓列表，支持按博主或基金筛选。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| blogger_id | int | 否 | `1` | 按博主筛选 |
| fund_id | int | 否 | `101` | 按基金筛选 |
| page | int | 否 | `1` | 页码，默认 `1` |
| page_size | int | 否 | `20` | 每页数量，默认 `20`，最大 `100` |

### 请求示例

```bash
curl "http://localhost:5000/api/v1/initial-positions?blogger_id=1&page=1&page_size=20"
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data.items | array | 初始持仓列表 |
| data.items[].initial_position_id | int | 初始持仓 ID |
| data.items[].blogger_id | int | 博主 ID |
| data.items[].blogger_name | string | 博主名称 |
| data.items[].fund_id | int | 基金 ID |
| data.items[].fund_name | string | 基金名称 |
| data.items[].fund_code | string | 基金代码 |
| data.items[].shares | number | 持有份额 |
| data.items[].cost_amount | number | 成本金额 |
| data.items[].record_date | string | 记录日期 |
| data.page | int | 当前页码 |
| data.page_size | int | 每页数量 |
| data.total | int | 总记录数 |

### 成功响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "initial_position_id": 1,
        "blogger_id": 1,
        "blogger_name": "基金小星",
        "fund_id": 101,
        "fund_name": "华夏成长混合",
        "fund_code": "000001",
        "shares": 12000,
        "cost_amount": 15600,
        "record_date": "2026-03-22"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

### 错误响应示例

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

```json
{
  "code": "INTERNAL_ERROR",
  "message": "服务器内部错误",
  "details": []
}
```

### 业务规则

1. 博主名称、基金名称、基金代码由后端关联查询返回。
2. 支持同时按博主和基金筛选。
3. 第一版不计算当前净值、市值、收益和占比。

### 关联接口

- 新增初始持仓：`POST /api/v1/initial-positions`
- 编辑初始持仓：`PUT /api/v1/initial-positions/{initial_position_id}`
- 查询博主列表：`GET /api/v1/bloggers`
- 查询基金列表：`GET /api/v1/funds`

---

## 5.2 新增初始持仓

### 接口名称

新增初始持仓 / `create_initial_position`

### 请求方法与路径

```http
POST /api/v1/initial-positions
```

### 功能说明

为指定博主和指定基金新增初始持仓。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| blogger_id | int | 是 | `1` | 博主 ID |
| fund_id | int | 是 | `101` | 基金 ID |
| shares | number | 是 | `12000` | 持有份额，必须大于等于 0 |
| cost_amount | number | 是 | `15600` | 成本金额，必须大于等于 0 |
| record_date | string | 是 | `2026-03-22` | 记录日期，格式 `YYYY-MM-DD` |

### 请求示例

```bash
curl -X POST "http://localhost:5000/api/v1/initial-positions" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":101,"shares":12000,"cost_amount":15600,"record_date":"2026-03-22"}'
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | `0` 表示成功 |
| message | string | 提示信息 |
| data.initial_position_id | int | 初始持仓 ID |
| data.blogger_id | int | 博主 ID |
| data.blogger_name | string | 博主名称 |
| data.fund_id | int | 基金 ID |
| data.fund_name | string | 基金名称 |
| data.fund_code | string | 基金代码 |
| data.shares | number | 持有份额 |
| data.cost_amount | number | 成本金额 |
| data.record_date | string | 记录日期 |

### 成功响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "initial_position_id": 1,
    "blogger_id": 1,
    "blogger_name": "基金小星",
    "fund_id": 101,
    "fund_name": "华夏成长混合",
    "fund_code": "000001",
    "shares": 12000,
    "cost_amount": 15600,
    "record_date": "2026-03-22"
  }
}
```

### 错误响应示例

```json
{
  "code": "BLOGGER_NOT_FOUND",
  "message": "博主不存在",
  "details": []
}
```

```json
{
  "code": "FUND_NOT_FOUND",
  "message": "基金不存在",
  "details": []
}
```

```json
{
  "code": "INITIAL_POSITION_DUPLICATED",
  "message": "同一博主、同一基金、同一记录日期的初始持仓已存在",
  "details": []
}
```

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "shares",
      "message": "份额必须大于等于 0"
    }
  ]
}
```

### 业务规则

1. `blogger_id` 对应的博主必须存在。
2. `fund_id` 对应的基金必须存在。
3. `shares` 必须大于等于 0。
4. `cost_amount` 必须大于等于 0。
5. `record_date` 必须是合法日期。
6. 同一 `blogger_id`、`fund_id`、`record_date` 只允许存在一条初始持仓。

### 关联接口

- 查询博主列表：`GET /api/v1/bloggers`
- 查询基金列表：`GET /api/v1/funds`
- 查询初始持仓列表：`GET /api/v1/initial-positions`
- 编辑初始持仓：`PUT /api/v1/initial-positions/{initial_position_id}`

---

## 5.3 编辑初始持仓

### 接口名称

编辑初始持仓 / `update_initial_position`

### 请求方法与路径

```http
PUT /api/v1/initial-positions/{initial_position_id}
```

### 功能说明

修改指定初始持仓。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| initial_position_id | int | 是 | `1` | 路径参数，初始持仓 ID |
| blogger_id | int | 是 | `1` | 博主 ID |
| fund_id | int | 是 | `101` | 基金 ID |
| shares | number | 是 | `12000` | 持有份额，必须大于等于 0 |
| cost_amount | number | 是 | `15600` | 成本金额，必须大于等于 0 |
| record_date | string | 是 | `2026-03-22` | 记录日期 |

### 请求示例

```bash
curl -X PUT "http://localhost:5000/api/v1/initial-positions/1" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":101,"shares":12000,"cost_amount":15600,"record_date":"2026-03-22"}'
```

### 响应字段

响应字段与新增初始持仓接口一致。

### 成功响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "initial_position_id": 1,
    "blogger_id": 1,
    "blogger_name": "基金小星",
    "fund_id": 101,
    "fund_name": "华夏成长混合",
    "fund_code": "000001",
    "shares": 12000,
    "cost_amount": 15600,
    "record_date": "2026-03-22"
  }
}
```

### 错误响应示例

```json
{
  "code": "INITIAL_POSITION_NOT_FOUND",
  "message": "初始持仓不存在",
  "details": []
}
```

```json
{
  "code": "BLOGGER_NOT_FOUND",
  "message": "博主不存在",
  "details": []
}
```

```json
{
  "code": "INITIAL_POSITION_DUPLICATED",
  "message": "同一博主、同一基金、同一记录日期的初始持仓已存在",
  "details": []
}
```

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "cost_amount",
      "message": "成本金额必须大于等于 0"
    }
  ]
}
```

### 业务规则

1. 本接口使用完整更新，所有字段都必须传。
2. 修改后的博主和基金必须存在。
3. 修改后的份额和成本金额必须大于等于 0。
4. 修改后仍需要满足同一博主、同一基金、同一记录日期唯一。
5. 如果未修改任何业务字段，接口可以返回原数据。

### 关联接口

- 查询初始持仓列表：`GET /api/v1/initial-positions`
- 新增初始持仓：`POST /api/v1/initial-positions`
- 查询博主列表：`GET /api/v1/bloggers`
- 查询基金列表：`GET /api/v1/funds`
