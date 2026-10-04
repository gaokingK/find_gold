# 任务 040：功能闭环验收与文档同步

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务不新增业务代码，主要是逐个请求第 5–9 天交付的接口、核对响应字段和文档、运行完整测试、整理验收清单。工作量在核对和整理反馈，不在写代码。

## 任务目标

新建：

```text
docs/backend/design/day9-delivery-checklist.md
```

完成后可以：

1. 确认第 5–9 天所有任务都已完成。
2. 确认核心接口可以正常访问。
3. 确认实际响应字段和接口文档一致。
4. 确认 `pytest -q` 全部通过。
5. 输出一份可交接给前端的验收清单。
6. 把发现的问题、未完成项和文档差异整理成反馈。

## 范围说明

本任务只做验收和文档核对。

不包含：

- 新增业务功能
- 修改数据库表结构
- 优化性能
- 修改前端页面
- 部署
- Docker
- CI/CD
- 登录和权限

## 前置条件

1. 任务 037、038、039 已完成。
2. `pytest -q` 当前可以通过。
3. 本地 MySQL 可连接，测试接口时使用开发库 `fund_db`。
4. 自动化测试只能连接 `fund_test_db`。

## 新概念说明

### Acceptance Checklist（验收清单）

Acceptance Checklist 是一份逐项检查清单，用来说明功能是否达到可交付状态。  
它的作用是避免「我大概改完了」这种没有证据的结论，而是用命令输出和接口响应证明。

## 执行目录

```bash
cd /d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：核对已完成文件

**必要性：**  
第 5–9 天的功能分散在多个模块里。先确认关键文件都存在，可以避免漏交。

确认以下文件存在：

```text
backend/app/routes/operations.py
backend/app/routes/nav_history.py
backend/app/routes/position_snapshots.py
backend/app/routes/returns.py
backend/app/routes/dashboards.py
backend/app/utils/snapshot_data.py
backend/app/services/return_calculation.py
```

如果文件名和这里不一致，先反馈，不要自行重命名。

---

### 步骤 2：执行全量语法检查

**必要性：**  
接口文档和手工测试不能替代语法检查。先确认所有改动后的 Python 文件都能通过基础检查。

执行：

```bash
python -m py_compile app/routes/operations.py
python -m py_compile app/routes/nav_history.py
python -m py_compile app/routes/position_snapshots.py
python -m py_compile app/routes/returns.py
python -m py_compile app/routes/dashboards.py
python -m py_compile app/utils/snapshot_data.py
python -m py_compile app/services/return_calculation.py
```

预期都没有输出，并且退出码是 `0`。

---

### 步骤 3：运行完整自动化测试

**必要性：**  
第 5–9 天功能之间有依赖关系。只测最后一个模块不够，必须跑全量 `pytest`，确认前面的模块没有被改坏。

执行：

```bash
pytest -q
```

预期全部通过。  
如果失败，先停止验收，把完整错误输出反馈给任务下发人。

---

### 步骤 4：启动服务并核对操作记录接口

**必要性：**  
操作记录是持仓快照和收益计算的数据来源，必须确认接口可用。

启动服务：

```bash
python run.py
```

另开一个终端，在 `backend` 目录执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/operations"
```

再执行：

```bash
curl -i -X POST "http://127.0.0.1:5000/api/v1/operations" -H "Content-Type: application/json" -d "{\"blogger_id\":1,\"fund_id\":101,\"operation_type\":\"buy\",\"operation_date\":\"2026-09-30\",\"shares\":1000,\"amount\":13000}"
```

如果数据库里没有 ID 为 `1` 的博主或 ID 为 `101` 的基金，请换成实际存在的 ID，或者只记录「前置数据不足」。

预期响应结构符合：

```text
docs/api/v1-operations.md
```

---

### 步骤 5：核对净值接口

**必要性：**  
收益和看板依赖指定日期净值，必须确认净值录入和查询可用。

在 `backend` 目录执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/nav-history"
```

再执行：

```bash
curl -i -X POST "http://127.0.0.1:5000/api/v1/nav-history" -H "Content-Type: application/json" -d "{\"fund_id\":101,\"nav_date\":\"2026-09-30\",\"nav\":2.4000}"
```

把 `fund_id` 换成实际存在的基金 ID。

预期响应结构符合：

```text
docs/api/v1-nav-history.md
```

---

### 步骤 6：核对持仓快照接口

**必要性：**  
持仓快照是收益计算的中间结果，必须确认份额和成本能算出来。

在 `backend` 目录执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/position-snapshots?snapshot_date=2026-09-30"
```

预期响应结构符合：

```text
docs/api/v1-position-snapshots.md
```

---

### 步骤 7：核对收益接口

**必要性：**  
收益模块是第 8 天的核心交付。需要分别核对单博主、单基金和总体收益。

在 `backend` 目录执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/returns?return_date=2026-09-30"
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/funds/101/return?return_date=2026-09-30"
curl -i "http://127.0.0.1:5000/api/v1/returns/summary?return_date=2026-09-30"
```

把 `1` 和 `101` 换成实际存在且有持仓关系的 ID。

预期响应结构符合：

```text
docs/api/v1-returns.md
```

---

### 步骤 8：核对看板接口

**必要性：**  
看板是第 9 天的交付，也是前端总览页面的主要数据来源。

在 `backend` 目录执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/dashboards/bloggers?return_date=2026-09-30"
curl -i "http://127.0.0.1:5000/api/v1/dashboards/funds?return_date=2026-09-30"
curl -i "http://127.0.0.1:5000/api/v1/dashboards/recent-operations?start_date=2026-09-24&end_date=2026-09-30&limit=20"
```

预期响应结构符合：

```text
docs/api/v1-dashboards.md
```

---

### 步骤 9：核对错误场景和空数据

**必要性：**  
前后端联调时最容易出问题的是空数据、缺净值和参数错误，不能只测 happy path。

在 `backend` 目录执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers/1/returns?return_date=bad-date"
curl -i "http://127.0.0.1:5000/api/v1/bloggers/999999/returns?return_date=2026-09-30"
curl -i "http://127.0.0.1:5000/api/v1/dashboards/bloggers?return_date=2999-12-31"
curl -i "http://127.0.0.1:5000/api/v1/dashboards/recent-operations?start_date=2026-09-30&end_date=2026-09-01"
```

预期都返回统一错误结构，HTTP 状态码和错误码符合接口文档。

---

### 步骤 10：创建验收清单

**必要性：**  
验收结果需要留下可复查的记录，不能只口头说「都通过了」。

新建文件：

```text
docs/backend/design/day9-delivery-checklist.md
```

写入以下内容：

```markdown
# 第 5–9 天功能闭环验收清单

## 验收结论

- [ ] 可以交付前端联调
- [ ] 有阻塞问题，暂不交付

## 自动化测试

- [ ] `pytest -q` 全部通过
- [ ] 已粘贴完整测试输出

## 操作记录模块

- [ ] `POST /api/v1/operations` 可用
- [ ] `GET /api/v1/operations` 可用
- [ ] `DELETE /api/v1/operations/{id}` 可用
- [ ] 响应字段和 `docs/api/v1-operations.md` 一致

## 净值数据模块

- [ ] `POST /api/v1/nav-history` 可用
- [ ] `GET /api/v1/nav-history` 可用
- [ ] `POST /api/v1/nav-history/import` 可用
- [ ] 响应字段和 `docs/api/v1-nav-history.md` 一致

## 持仓快照模块

- [ ] `GET /api/v1/bloggers/{blogger_id}/position-snapshots` 可用
- [ ] 响应字段和 `docs/api/v1-position-snapshots.md` 一致

## 简单收益模块

- [ ] `GET /api/v1/bloggers/{blogger_id}/returns` 可用
- [ ] `GET /api/v1/bloggers/{blogger_id}/funds/{fund_id}/return` 可用
- [ ] `GET /api/v1/returns/summary` 可用
- [ ] 响应字段和 `docs/api/v1-returns.md` 一致
- [ ] 缺净值时相关字段返回 `null`

## 看板模块

- [ ] `GET /api/v1/dashboards/bloggers` 可用
- [ ] `GET /api/v1/dashboards/funds` 可用
- [ ] `GET /api/v1/dashboards/recent-operations` 可用
- [ ] 响应字段和 `docs/api/v1-dashboards.md` 一致

## 边界场景

- [ ] 空数据返回 `200`
- [ ] 参数错误返回 `400 VALIDATION_ERROR`
- [ ] 博主或基金不存在返回对应 `404`
- [ ] 缺净值时返回 `null`，不使用最近净值兜底
- [ ] 成本为 `0` 时收益率返回 `null`

## 发现的问题

| 问题 | 影响 | 是否阻塞交付 | 负责人 | 状态 |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## 未完成项

| 事项 | 原因 | 后续处理 |
| --- | --- | --- |
|  |  |  |
```

根据实际验证结果勾选。  
发现问题时不要求在这里修复，先记录清楚。

---

### 步骤 11：核对文档差异

**必要性：**  
接口文档是前后端唯一契约。如果实际响应和文档不一致，前端会按错误字段开发。

逐项核对：

```text
docs/api/v1-operations.md
docs/api/v1-nav-history.md
docs/api/v1-position-snapshots.md
docs/api/v1-returns.md
docs/api/v1-dashboards.md
```

重点核对：

1. 路径是否一致。
2. 参数名是否一致。
3. 响应字段名是否一致。
4. HTTP 状态码是否一致。
5. 错误码是否一致。
6. 空值口径是否一致。

如果发现不一致，先反馈差异，不要私自改接口文档。确认修改方案后，必须先改文档，再改代码。

---

### 步骤 12：整理验收反馈

**必要性：**  
任务下发人需要根据反馈更新计划、接口文档和后续任务，不能只收到一句「完成了」。

按以下格式反馈：

```text
1. 验收结论：可以交付 / 暂不交付
2. 新增文件：...
3. 修改文件：...
4. pytest -q 完整输出：...
5. 已核对接口列表：...
6. 响应字段差异：...
7. 发现的问题：...
8. 未完成项：...
9. 建议进入下一个阶段的内容：...
```

## 验证方式

### 1. 语法检查

所有关键 Python 文件执行 `python -m py_compile`，预期没有输出。

### 2. 自动化测试

```bash
pytest -q
```

预期全部通过。

### 3. 接口验证

至少验证以下接口：

```text
GET /api/v1/operations
POST /api/v1/operations
GET /api/v1/nav-history
POST /api/v1/nav-history
GET /api/v1/bloggers/{blogger_id}/position-snapshots
GET /api/v1/bloggers/{blogger_id}/returns
GET /api/v1/bloggers/{blogger_id}/funds/{fund_id}/return
GET /api/v1/returns/summary
GET /api/v1/dashboards/bloggers
GET /api/v1/dashboards/funds
GET /api/v1/dashboards/recent-operations
```

预期都符合对应接口文档。

### 4. 验收清单

```bash
cat ../docs/backend/design/day9-delivery-checklist.md
```

预期文件存在，并且每个勾选项都有实际验证依据。

## 常见坑

### 1. 只测最后一个接口

后面接口依赖前面数据。  
必须跑全量 `pytest -q`，并逐组核对第 5–9 天接口。

### 2. 用开发库跑自动化测试

测试只能连 `fund_test_db`，因为测试夹具会清空数据。  
一旦发现测试可能连到 `fund_db`，立即停止。

### 3. 只测正常请求

空数据、缺净值、参数错误、资源不存在才是联调高发问题。  
必须按本任务的错误场景执行。

### 4. 发现文档不一致后直接改代码

接口字段变更必须先确认并更新文档，再改代码。  
否则前后端会出现两套口径。

## 完成标准

以下条件全部满足，任务 040 才算完成：

1. `docs/backend/design/day9-delivery-checklist.md` 已创建。
2. `pytest -q` 全部通过。
3. 第 5–9 天核心接口都已手工请求。
4. 实际响应字段和接口文档一致，或已记录明确差异。
5. 边界场景和错误场景已经验证。
6. 已按格式输出完整验收反馈。

## 完成后请反馈

1. 验收结论。
2. 新增和修改的文件列表。
3. `pytest -q` 完整输出。
4. 已核对接口列表。
5. 接口文档差异。
6. 发现的问题。
7. 未完成项。
8. 是否可以交付前端联调。
