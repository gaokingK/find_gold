# 任务 013：手工联调与验收检查

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务不写新功能，但要按接口文档逐项验证博主、基金、初始持仓模块；需要准备测试数据、执行一组 curl 请求、核对响应字段和错误码，并整理验收结果。

## 任务目标

对第一版基础数据管理接口做一次完整手工验收。

完成后可以确认：

1. 博主管理接口可用。
2. 基金管理接口可用。
3. 初始持仓接口可用。
4. 博主、基金、初始持仓之间的关联关系正确。
5. 所有接口响应结构统一。
6. 第一版基础数据模块可以交付给前端联调。

## 范围说明

本任务只做联调和验收。

不包含：

- 新增功能
- 重构代码
- 引入自动化测试框架
- 部署上线
- 权限和认证

如果验收时发现严重问题，先停止新增验收项，记录问题并反馈；问题修复后再继续验收。

## 前置条件

1. 任务 010 已完成。
2. 任务 011 已完成。
3. 任务 012 已完成。
4. MySQL 服务正常。
5. Flask 服务可以启动。
6. `docs/api/v1-basic-management.md` 可以访问。

## 新概念：联调与验收

### 联调

联调的英文是 Integration Testing。  
这里是前后端联调前的接口级验证，使用 curl 模拟前端请求，确认后端接口符合接口文档。

### 验收

验收的英文是 Acceptance Check。  
验收是按照需求文档和接口文档逐条确认功能是否完成，不凭感觉判断。

## 执行目录

所有命令都在下面目录执行：

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：确认数据库表存在

**必要性：**  
表结构是所有接口的基础。先确认三张表都存在，避免后面因为缺表误判接口代码有问题。

执行：

```bash
python -m scripts.check_db
```

如果该脚本只检查连接，不检查表，可以继续用数据库客户端确认：

```sql
SHOW TABLES;
```

预期至少能看到：

```text
bloggers
funds
initial_positions
```

---

### 步骤 2：启动 Flask 服务

**必要性：**  
所有接口验收都必须在服务运行状态下进行。

执行：

```bash
python run.py
```

另开一个终端执行下面的 curl 命令。

---

### 步骤 3：验证健康检查

**必要性：**  
先确认服务本身可用，再测试业务接口。

执行：

```bash
curl -i "http://127.0.0.1:5000/health"
```

预期：

- HTTP 状态码是 `200`。
- 返回统一 JSON 结构。
- `code` 是 `0`。

---

### 步骤 4：准备第一组博主数据

**必要性：**  
初始持仓依赖博主。先创建两个博主，才能测试列表、详情、编辑、删除和重复名称。

执行：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/bloggers" \
  -H "Content-Type: application/json" \
  -d '{"name":"验收博主A","sector":"成长股","observe_start_date":"2026-09-30"}'

curl -X POST "http://127.0.0.1:5000/api/v1/bloggers" \
  -H "Content-Type: application/json" \
  -d '{"name":"验收博主B","sector":"价值股","observe_start_date":"2026-09-01"}'
```

记录返回的 `blogger_id`。下面假设：

- `验收博主A` 的 ID 是 `1`
- `验收博主B` 的 ID 是 `2`

如果本地已有同名数据，请换成新的测试名称。

---

### 步骤 5：验证博主模块

**必要性：**  
博主是初始持仓的关联主体，必须先确认基础能力正常。

执行：

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers?keyword=验收博主"
curl "http://127.0.0.1:5000/api/v1/bloggers/1"
```

验证编辑：

```bash
curl -X PUT "http://127.0.0.1:5000/api/v1/bloggers/1" \
  -H "Content-Type: application/json" \
  -d '{"name":"验收博主A修改","sector":"成长股","observe_start_date":"2026-09-30"}'
```

验证重复名称：

```bash
curl -X PUT "http://127.0.0.1:5000/api/v1/bloggers/1" \
  -H "Content-Type: application/json" \
  -d '{"name":"验收博主B","sector":"成长股","observe_start_date":"2026-09-30"}'
```

预期：

1. 列表接口返回分页字段。
2. 详情接口返回完整字段。
3. 编辑接口返回 `code: 0`。
4. 重复名称返回 `BLOGGER_NAME_DUPLICATED`，HTTP 状态码是 `409`。

---

### 步骤 6：准备基金数据

**必要性：**  
初始持仓还依赖基金。需要至少两个基金，才能验证列表和编辑。

执行：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/funds" \
  -H "Content-Type: application/json" \
  -d '{"name":"验收基金A","fund_code":"ACCT001"}'

curl -X POST "http://127.0.0.1:5000/api/v1/funds" \
  -H "Content-Type: application/json" \
  -d '{"name":"验收基金B","fund_code":"ACCT002"}'
```

记录返回的 `fund_id`。下面假设：

- `验收基金A` 的 ID 是 `1`
- `验收基金B` 的 ID 是 `2`

如果基金代码已存在，请换成新的测试代码。

---

### 步骤 7：验证基金模块

**必要性：**  
基金代码有唯一约束，编辑基金可能影响初始持仓列表展示，必须提前确认。

执行：

```bash
curl "http://127.0.0.1:5000/api/v1/funds?keyword=验收基金"
```

第一版**没有基金详情接口** `GET /api/v1/funds/{fund_id}`，不要验证这个路径。  
需要看单只基金时，用 `keyword` 或 `fund_code` 从列表接口筛选。

验证编辑：

```bash
curl -X PUT "http://127.0.0.1:5000/api/v1/funds/1" \
  -H "Content-Type: application/json" \
  -d '{"name":"验收基金A修改","fund_code":"ACCT001"}'
```

验证重复代码：

```bash
curl -X PUT "http://127.0.0.1:5000/api/v1/funds/1" \
  -H "Content-Type: application/json" \
  -d '{"name":"验收基金A修改","fund_code":"ACCT002"}'
```

预期：

1. 列表接口返回分页字段。
2. 编辑接口返回 `code: 0`。
3. 重复代码返回 `FUND_CODE_DUPLICATED`，HTTP 状态码是 `409`。

---

### 步骤 8：新增初始持仓

**必要性：**  
初始持仓是第一版核心业务数据，必须确认博主和基金都能正确关联。

执行：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/initial-positions" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"shares":12000,"cost_amount":15600,"record_date":"2026-09-30"}'

curl -X POST "http://127.0.0.1:5000/api/v1/initial-positions" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":2,"shares":8000,"cost_amount":10400,"record_date":"2026-09-30"}'

curl -X POST "http://127.0.0.1:5000/api/v1/initial-positions" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":2,"fund_id":1,"shares":5000,"cost_amount":6500,"record_date":"2026-09-30"}'
```

预期每个请求都返回：

- `code: 0`
- `blogger_name`
- `fund_name`
- `fund_code`
- `shares`
- `cost_amount`
- `record_date`

---

### 步骤 9：验证初始持仓列表和筛选

**必要性：**  
前端列表页需要分页和筛选能力，也需要显示博主名称和基金信息。

执行：

```bash
curl "http://127.0.0.1:5000/api/v1/initial-positions"
curl "http://127.0.0.1:5000/api/v1/initial-positions?blogger_id=1"
curl "http://127.0.0.1:5000/api/v1/initial-positions?fund_id=1"
curl "http://127.0.0.1:5000/api/v1/initial-positions?blogger_id=1&fund_id=1"
```

预期：

1. 都返回 `data.items`、`data.page`、`data.page_size`、`data.total`。
2. `blogger_id=1` 只返回博主 1 的数据。
3. `fund_id=1` 只返回基金 1 的数据。
4. 同时传两个筛选条件时，只返回同时满足条件的数据。

---

### 步骤 10：验证初始持仓编辑和重复校验

**必要性：**  
初始持仓录入可能写错份额或成本，编辑功能必须可用；重复数据会导致观察结果混乱。

编辑：

```bash
curl -X PUT "http://127.0.0.1:5000/api/v1/initial-positions/1" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"shares":13000,"cost_amount":16000,"record_date":"2026-09-30"}'
```

验证重复：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/initial-positions" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":1,"fund_id":1,"shares":12000,"cost_amount":15600,"record_date":"2026-09-30"}'
```

预期：

1. 编辑接口返回 `code: 0`，份额和成本更新。
2. 重复新增返回 `INITIAL_POSITION_DUPLICATED`，HTTP 状态码是 `409`。

---

### 步骤 11：验证博主删除和级联删除

**必要性：**  
需求文档要求删除博主时级联删除初始持仓。这是数据一致性验收重点。

先确认博主 1 有初始持仓：

```bash
curl "http://127.0.0.1:5000/api/v1/initial-positions?blogger_id=1"
```

删除博主 1：

```bash
curl -X DELETE "http://127.0.0.1:5000/api/v1/bloggers/1"
```

再查询：

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers/1"
curl "http://127.0.0.1:5000/api/v1/initial-positions?blogger_id=1"
```

预期：

1. 删除接口返回 `code: 0`。
2. 博主详情返回 `BLOGGER_NOT_FOUND`。
3. 初始持仓列表 `blogger_id=1` 的结果为空。

---

### 步骤 12：验证错误响应结构

**必要性：**  
前端需要根据统一错误结构展示提示。所有错误响应都不应返回 HTML 或随机结构。

执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/0"

curl -i -X PUT "http://127.0.0.1:5000/api/v1/funds/0" \
  -H "Content-Type: application/json" \
  -d '{"name":"随便","fund_code":"ACCT999"}'

curl -i -X PUT "http://127.0.0.1:5000/api/v1/initial-positions/0" \
  -H "Content-Type: application/json" \
  -d '{"blogger_id":2,"fund_id":1,"shares":1,"cost_amount":1,"record_date":"2026-09-30"}'

curl -X POST "http://127.0.0.1:5000/api/v1/bloggers" \
  -H "Content-Type: application/json" \
  -d '{}'
```

说明：基金和初始持仓第一版只有列表、新增、编辑三个接口，没有 `GET /api/v1/funds/{fund_id}` 和 `GET /api/v1/initial-positions/{id}`。  
所以这里用 `PUT` 而不是 `GET` 来验证「路径参数非法」这个场景。  
如果对不存在的路由发 `GET`，Flask 会返回 HTML 404 页面，那不是业务错误，不要当成验收失败。

预期：

1. HTTP 状态码符合接口文档。
2. 响应包含 `code`、`message`、`details`。
3. 没有返回 HTML 错误页。

---

### 步骤 13：填写验收清单

**必要性：**  
验收结论必须有依据。逐条核对下面清单，能通过才勾选，不能通过就记录问题。

| 序号 | 验收项 | 结果 | 说明 |
| --- | --- | --- | --- |
| 1 | 可以新增博主 | 通过 / 未通过 |  |
| 2 | 博主名称重复会被拒绝 | 通过 / 未通过 |  |
| 3 | 可以查询博主列表 | 通过 / 未通过 |  |
| 4 | 可以查询博主详情 | 通过 / 未通过 |  |
| 5 | 可以编辑博主信息 | 通过 / 未通过 |  |
| 6 | 可以删除博主 | 通过 / 未通过 |  |
| 7 | 删除博主会级联删除初始持仓 | 通过 / 未通过 |  |
| 8 | 可以新增基金 | 通过 / 未通过 |  |
| 9 | 基金代码重复会被拒绝 | 通过 / 未通过 |  |
| 10 | 可以查询基金列表 | 通过 / 未通过 |  |
| 11 | 可以编辑基金信息 | 通过 / 未通过 |  |
| 12 | 可以新增初始持仓 | 通过 / 未通过 |  |
| 13 | 博主或基金不存在时新增初始持仓会被拒绝 | 通过 / 未通过 |  |
| 14 | 同一博主、基金、记录日期不能重复新增初始持仓 | 通过 / 未通过 |  |
| 15 | 可以查询初始持仓列表 | 通过 / 未通过 |  |
| 16 | 初始持仓列表返回博主名称、基金名称、基金代码 | 通过 / 未通过 |  |
| 17 | 可以编辑初始持仓 | 通过 / 未通过 |  |
| 18 | 所有接口返回统一 JSON 结构 | 通过 / 未通过 |  |
| 19 | 所有接口使用 `/api/v1/` 前缀 | 通过 / 未通过 |  |
| 20 | 接口文档与实际行为一致 | 通过 / 未通过 |  |

---

### 步骤 14：整理验收报告

**必要性：**  
验收报告可以交给前端联调使用，也方便后端新手复盘。

报告格式：

```markdown
# 第一版基础数据模块验收报告

## 验收结论

- 通过 / 未通过

## 已验收接口

- GET /api/v1/bloggers
- POST /api/v1/bloggers
- GET /api/v1/bloggers/{blogger_id}
- PUT /api/v1/bloggers/{blogger_id}
- DELETE /api/v1/bloggers/{blogger_id}
- GET /api/v1/funds
- POST /api/v1/funds
- PUT /api/v1/funds/{fund_id}
- GET /api/v1/initial-positions
- POST /api/v1/initial-positions
- PUT /api/v1/initial-positions/{initial_position_id}

## 发现的问题

1. 问题描述
2. 复现请求
3. 期望结果
4. 实际结果
5. 严重程度

## 后续建议

1. 建议一
2. 建议二
```

## 验证方式

最终验收通过的标准：

1. 上面的 20 项验收清单全部为「通过」。
2. 没有未修复的严重问题。
3. 前端联调需要的接口都有响应。
4. 响应字段和 `docs/api/v1-basic-management.md` 一致。
5. 错误码和 HTTP 状态码符合接口文档。
6. 删除博主后初始持仓没有残留。

## 常见坑

### 1. 用旧数据验收

如果数据库里已经有同名博主或同代码基金，可能误以为新增失败。

建议：

- 验收前先查列表。
- 测试数据使用容易识别的名称，例如 `验收博主A`。
- 如果冲突，换一个新名称或新代码。

### 2. 只测成功请求

只测 `code: 0` 不能证明接口可用。  
必须同时测参数错误、资源不存在、重复数据。

### 3. 忽略级联删除

删除博主后必须重新查询初始持仓。  
不要只看删除接口返回成功。

### 4. 忽略响应字段

前端不能使用文档里不存在的字段。  
验收时要对照 `docs/api/v1-basic-management.md` 检查字段名和类型。

### 5. 验收过程中顺手改代码

验收阶段应先记录问题。  
如果边验收边改代码，容易遗漏已经验证过的功能。

### 6. 新增接口返回了 201 或直接报 TypeError

本项目所有成功响应统一返回 `200`，新增接口也一样。

如果新增基金或新增初始持仓时报：

```text
TypeError: success() got an unexpected keyword argument 'http_status'
```

说明 `funds.py` 或 `initial_positions.py` 里写成了：

```python
return success(data=data, http_status=201)
```

改成：

```python
return success(data=data)
```

排查命令：

```bash
grep -rn "http_status=201" app/
```

预期没有任何输出。

## 完成标准

以下条件全部满足，任务 013 才算完成：

1. 已执行完整验收清单。
2. 20 项验收项全部通过。
3. 已生成验收报告。
4. 已列出发现的问题或确认没有问题。
5. 已确认第一版基础数据模块可以交给前端联调。

## 完成后请反馈

1. 验收结论：通过或未通过。
2. 验收清单结果。
3. 发现的问题、复现命令、期望结果和实际结果。
4. 验收报告文件路径。
5. 是否可以进入前端联调阶段。
