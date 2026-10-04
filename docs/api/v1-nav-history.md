# 净值数据接口文档

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 版本 | v1.0 |
| 状态 | 已确认 |
| 日期 | 2026-09-30 |
| API 前缀 | `/api/v1/` |
| 模块范围 | 基金净值手动录入、CSV 导入 |
| 数据表 | `nav_history` |

## 1. 全局约定

### 1.1 成功响应的 HTTP 状态码

所有成功响应统一返回 HTTP `200`。

### 1.2 成功响应结构

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

### 1.3 错误响应结构

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": []
}
```

### 1.4 本模块错误码

| 错误码 | HTTP 状态码 | 说明 |
| --- | --- | --- |
| `VALIDATION_ERROR` | 400 | 参数校验失败 |
| `FUND_NOT_FOUND` | 404 | 基金不存在 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

## 2. 接口总览

| 序号 | 接口名称 | 请求方法 | 路径 |
| --- | --- | --- | --- |
| 1 | 录入或更新净值 | POST | `/api/v1/nav-history` |
| 2 | 批量导入净值 | POST | `/api/v1/nav-history/import` |

## 3. 净值对象

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| nav_id | int | 净值记录 ID |
| fund_id | int | 基金 ID |
| fund_name | string | 基金名称 |
| fund_code | string | 基金代码 |
| nav_date | string | 净值日期，格式 `YYYY-MM-DD` |
| nav | number | 单位净值 |
| created_at | string | 创建时间 |
| updated_at | string | 更新时间 |

## 4. 录入或更新净值

### 接口名称

录入或更新净值 / `upsert_nav_history`

### 请求方法与路径

```http
POST /api/v1/nav-history
```

### 功能说明

录入某只基金某一天的净值。  
如果同一 `fund_id + nav_date` 已有净值，则更新旧值。

### 请求头

```http
Content-Type: application/json
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| fund_id | int | 是 | `1` | 基金 ID，必须为正整数且基金必须存在 |
| nav_date | string | 是 | `2026-09-30` | 净值日期，格式 `YYYY-MM-DD`，不能晚于今天 |
| nav | number | 是 | `1.2345` | 单位净值，必须大于 0 |

### 请求示例

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/nav-history" \
  -H "Content-Type: application/json" \
  -d '{"fund_id":1,"nav_date":"2026-09-30","nav":1.2345}'
```

### 响应字段

`data` 是一个净值对象，字段见第 3 节。

### 成功响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "nav_id": 1,
    "fund_id": 1,
    "fund_name": "华夏成长混合",
    "fund_code": "000001",
    "nav_date": "2026-09-30",
    "nav": 1.2345,
    "created_at": "2026-09-30 10:00:00",
    "updated_at": "2026-09-30 10:00:00"
  }
}
```

### 错误响应示例

净值不合法：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "nav",
      "message": "净值必须大于 0"
    }
  ]
}
```

日期格式错误：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "nav_date",
      "message": "净值日期格式必须是 YYYY-MM-DD"
    }
  ]
}
```

基金不存在：

```json
{
  "code": "FUND_NOT_FOUND",
  "message": "基金不存在",
  "details": []
}
```

### 业务规则

1. `fund_id` 必须存在于 `funds` 表。
2. `nav_date` 不能晚于今天。
3. `nav` 必须大于 0。
4. 同一 `fund_id + nav_date` 只允许一条净值。
5. 同一 `fund_id + nav_date` 重复提交时，更新旧值。
6. 第一版不处理分红净值、累计净值、复权净值。
7. 第一版没有净值删除接口和净值编辑接口。

### 关联接口

- 批量导入净值：`POST /api/v1/nav-history/import`
- 查询基金列表：`GET /api/v1/funds`

## 5. 批量导入净值

### 接口名称

批量导入净值 / `import_nav_history_csv`

### 请求方法与路径

```http
POST /api/v1/nav-history/import
```

### 功能说明

上传 CSV 文件，批量导入或更新净值。

### 请求头

请求体使用文件上传，不需要手动设置 `Content-Type`。

```http
Content-Type: multipart/form-data
```

### 请求参数

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| file | file | 是 | `nav_history.csv` | CSV 文件，最多 1000 行 |

CSV 列名必须包含：

| 列名 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- |
| fund_code | 是 | `000001` | 基金代码，必须存在 |
| nav_date | 是 | `2026-09-30` | 净值日期，格式 `YYYY-MM-DD` |
| nav | 是 | `1.2345` | 单位净值，必须大于 0 |

CSV 示例：

```csv
fund_code,nav_date,nav
000001,2026-09-29,1.2000
000001,2026-09-30,1.2345
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| total_rows | int | CSV 中解析成功的行数 |
| processed_rows | int | 实际处理成功的行数 |

### 成功响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "total_rows": 2,
    "processed_rows": 2
  }
}
```

### 错误响应示例

CSV 内部校验失败：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "CSV 解析或校验失败",
  "details": [
    {
      "row": 3,
      "field": "nav",
      "message": "净值必须大于 0"
    }
  ]
}
```

基金代码不存在：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "CSV 中存在不存在的基金代码",
  "details": [
    {
      "field": "fund_code",
      "message": "基金代码 NOT_EXIST 不存在"
    }
  ]
}
```

CSV 为空：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "CSV 解析或校验失败",
  "details": [
    {
      "field": "file",
      "message": "CSV 文件不能为空"
    }
  ]
}
```

### 业务规则

1. CSV 必须包含 `fund_code`、`nav_date`、`nav` 三列。
2. 后端根据 `fund_code` 查找 `fund_id`。
3. `fund_code` 不存在时，整批导入失败。
4. CSV 内部不允许重复的 `fund_code + nav_date`。
5. 只要有一行错误，整批导入失败。
6. 同一 `fund_id + nav_date` 已有净值时，更新旧值。
7. CSV 最多 1000 行。
8. 支持 UTF-8 BOM 和 GBK 编码。

### 关联接口

- 录入或更新净值：`POST /api/v1/nav-history`
- 查询基金列表：`GET /api/v1/funds`

## 6. 变更记录

| 日期 | 变更 | 说明 |
| --- | --- | --- |
| 2026-09-30 | v1.0 | 初始化净值接口文档，确认手动录入和 CSV 导入口径 |
