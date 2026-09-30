# 后端第 5–9 天 / 40 小时功能闭环计划（v2）

## 说明

本计划替代上一版偏工程化的第 5–9 天计划，改为优先推进业务功能闭环。

执行原则仍然遵守 `AGENTS.md`：

1. 按顺序推进。
2. 一个任务只引入少量新概念。
3. 每个任务完成后必须验证。
4. 上一任务未验收，不开始下一任务。
5. 后续单独生成任务文档，再交给新手执行。

## 已确认口径

| 项目 | 口径 |
| --- | --- |
| 优先方向 | 日常操作记录、净值数据、持仓快照、简单收益、汇总看板 |
| 操作记录 | 精简版 |
| 净值数据 | 手动录入 / CSV 导入 |
| 收益范围 | 成本、市值、累计收益率 |
| 暂缓内容 | 登录、权限、OCR、自动净值同步、完整金融指标、Docker、CI/CD |
| 数据库 | 继续使用 MySQL |
| API 前缀 | `/api/v1/` |
| 成功响应 | 统一返回 HTTP `200`，新增接口也不返回 `201` |
| 收益率边界 | 成本小于或等于 `0` 时，收益率返回 `null`，不返回 `0`，也不抛异常 |
| 份额边界 | 第一版不校验超额卖出，计算出的剩余份额可以为负，由使用者自己发现录入错误 |
| 金额精度 | 数据库用 `DECIMAL`；涉及累加的计算要用 `Decimal`，不要用 `float` |

## 任务编号说明

**第 5 天的任务编号（018–022）已确定**，任务文档已经写好。

**第 5–9 天的任务编号已全部确定：第 5 天是 018–022，第 6 天是 023–028，第 7 天是 029–032，第 8 天是 033–036，第 9 天是 037–040。**

后续如果插入新任务，不能随意占用已生成任务的编号；可以在后续新计划中继续编号，或在允许的位置插入字母后缀编号（例如 `036A`），并同步更新所有交叉引用。

## 总目标

第 5–9 天完成一个最小业务闭环：

```text
日常操作记录
    ↓
净值数据
    ↓
持仓快照
    ↓
简单收益计算
    ↓
博主 / 基金 / 总体看板
```

## 总工时

| 天数 | 主题 | 任务范围 | 预计工时 |
| --- | --- | --- | --- |
| 第 5 天 | 日常操作记录基础模块 | 018–022（已确定） | 8 小时 |
| 第 6 天 | 净值数据基础模块 | 023–028 | 8 小时 |
| 第 7 天 | 持仓快照模块 | 029–032 | 8 小时 |
| 第 8 天 | 简单收益计算 | 033–036（已确定） | 8 小时 |
| 第 9 天 | 汇总看板与交付检查 | 037–040（已确定） | 8 小时 |

合计：40 小时。

---

## 第 5 天：日常操作记录基础模块

| 顺序 | 任务 | 预计工时 | 产出 |
| --- | --- | --- | --- |
| 1 | 018 操作记录表设计 | 1 小时 | `docs/backend/design/operations-table-design.md` |
| 2 | 019 操作记录建表和初始化 | 1.5 小时 | `operations` 表 + 测试夹具同步 |
| 3 | 020 新增操作记录接口 | 2 小时 | `POST /api/v1/operations` 可用 |
| 4 | 021 操作记录查询接口 | 1.5 小时 | `GET /api/v1/operations` 可用 |
| 5 | 022 删除接口与操作记录测试 | 2 小时 | `DELETE /api/v1/operations/{id}` + `test_operations.py` |

合计 8 小时。

### 第 5 天的接口契约

操作记录的接口文档已经写好，前后端共用：

```text
docs/api/v1-operations.md
```

任务 018–022 都以它为准。开发过程中发现文档说不通的地方，反馈，不要自己改。

### 操作记录精简版口径

本阶段只支持以下类型：

| 类型 | 中文含义 | 精简版处理 |
| --- | --- | --- |
| `buy` | 买入 | 份额增加，成本金额增加 |
| `sell` | 卖出 | 份额减少，成本按比例减少 |
| `dividend_cash` | 现金分红 | 记录金额，不自动改变份额；接口允许省略 `shares`，后端补 `0` |

本阶段不做：

- 手续费
- 税费
- 红利再投资
- 拆分合并
- 自动调仓
- 超额卖出校验
- 编辑操作记录（录错的记录删除后重新录入）
- 操作记录详情接口
- 复杂账务规则

### 第 5 天要注意的一处连带影响

`operations` 表建好之后，原来能跑通的 `DELETE /api/v1/bloggers/{blogger_id}` 会因为外键约束而失败。  
这件事在任务 022 里修：删博主前先删他的操作记录。  
**任务 019 完成到任务 022 完成之间，删除博主接口处于不可用状态**，这是已知的，不要当成新 bug 反馈。

---

## 第 6 天：净值数据基础模块

| 顺序 | 主题 | 预计工时 | 产出 |
| --- | --- | --- | --- |
| 1 | 023 统一分页与排序校验工具 | 1.5 小时 | 四个模块共用一份参数校验代码 |
| 2 | 024 净值表设计 | 1 小时 | `docs/backend/design/nav-history-table-design.md` |
| 3 | 025 净值表创建和唯一约束 | 1 小时 | `nav_history` 表 + 唯一约束 |
| 4 | 026 净值手动录入接口 | 2 小时 | `POST /api/v1/nav-history` 可用 |
| 5 | 027 净值 CSV 解析与校验 | 1.5 小时 | 能把上传的 CSV 解析成待入库的行，并逐行报错 |
| 6 | 028 净值 CSV 导入入库 | 1 小时 | `POST /api/v1/nav-history/import` 可用 |

合计 8 小时。

### 为什么第一项是「统一分页工具」

到第 5 天结束时，博主、基金、初始持仓、操作记录四个模块里会有四份几乎一样的 `page` / `page_size` / `sort_by` / `order` 校验代码。  
第 6 天还要再加净值模块，如果不先合并，就会变成五份。改一个规则（比如把 `page_size` 上限从 100 调到 200）要改五个地方，漏一个就出现行为不一致。

放在第 6 天开头做，是因为此时四个模块都有测试覆盖，重构后跑一遍 `pytest -q` 就能确认没改坏。第 5 天做则没有这个保障。

### 为什么 CSV 导入拆成两个任务

原计划「净值 CSV 导入接口」是一个 2 小时的任务，但它实际包含两组完全不同的新概念：

1. 文件上传、`multipart/form-data`、Python 的 `csv` 模块、编码问题（Excel 导出的 CSV 常见 GBK 和 BOM）。
2. 批量入库、部分成功怎么处理、逐行错误怎么返回给前端。

对新手来说这是 4 个以上的新概念挤在一个任务里，按 `AGENTS.md` 的要求必须拆开。  
拆法是：先只做解析和校验（不写库，返回解析结果和错误列表），确认解析对了再做入库。

### 净值数据口径

- 第一版不接外部数据源。
- 支持手动录入。
- 支持 CSV 导入。
- 同一 `fund_id + nav_date` 只允许一条净值。
- 后端只保存净值数值，不处理分红净值、复权净值等复杂口径。
- CSV 导入采用「全部成功才入库」还是「部分成功」，在净值表设计任务里确认后写进接口文档。

---

## 第 7 天：持仓快照模块

| 顺序 | 任务 | 预计工时 | 产出 |
| --- | --- | --- | --- |
| 1 | 029 快照日期与数据读取工具 | 2 小时 | `backend/app/utils/snapshot_data.py` |
| 2 | 030 单个博主持仓快照计算 | 2 小时 | `backend/app/services/position_snapshot.py` |
| 3 | 031 博主持仓快照接口 | 2 小时 | `GET /api/v1/bloggers/{blogger_id}/position-snapshots` |
| 4 | 032 持仓快照测试 | 2 小时 | `backend/tests/test_position_snapshots.py` |

合计 8 小时。

### 第 7 天的接口契约

持仓快照接口的接口文档在：

```text
docs/api/v1-position-snapshots.md
```

写代码前先读这份文档。接口字段一旦确定，变更必须同步更新文档，并通知前端。

### 持仓快照口径

- 第一版实时计算，不落库。
- 根据初始持仓和截至某日的操作记录计算。
- 卖出使用平均成本法。
- 不做持久化快照缓存。
- 第一版不校验超额卖出，所以计算出的剩余份额**可能为负**。接口照实返回，不要截断成 0，也不要报错——负数是给使用者看的信号，说明某笔操作录错了。
- 第一版只返回份额和成本，不返回市值、收益金额和收益率。

---

## 第 8 天：简单收益计算

| 顺序 | 任务 | 预计工时 | 产出 |
| --- | --- | --- | --- |
| 1 | 033 简单收益计算服务与精确净值查询工具 | 2 小时 | `calculate_position_returns()`、`calculate_total_returns()`、`get_nav_on_date_map()` |
| 2 | 034 单博主累计收益率接口 | 2 小时 | `GET /api/v1/bloggers/{blogger_id}/returns` |
| 3 | 035 单基金收益汇总接口 | 2 小时 | `GET /api/v1/bloggers/{blogger_id}/funds/{fund_id}/return` |
| 4 | 036 总体收益汇总接口 | 2 小时 | `GET /api/v1/returns/summary` |

合计 8 小时。

### 第 8 天的接口契约

简单收益的接口文档已经写好，前后端共用：

```text
docs/api/v1-returns.md
```

任务 033–036 都以它为准。开发过程中发现文档说不通的地方，反馈，不要自己改。

### 简单收益口径

第一版只计算：

| 指标 | 简化公式 |
| --- | --- |
| 成本 | 当前剩余成本 |
| 市值 | 当前份额 × 对应日期净值 |
| 累计收益率 | `(市值 - 成本) / 成本` |

三条边界规则，必须在第 8 天开始前写进接口文档：

1. **成本为 `0` 或负数时，收益率返回 `null`。** 不能直接算 `(市值 - 成本) / 成本`，那会抛 `ZeroDivisionError`，整个接口返回 500。全部卖出后成本正好是 0，这是正常业务状态，不是异常。
2. **对应日期没有净值时，市值返回 `null`，收益率也返回 `null`。** 不要拿最近一天的净值顶替，也不要当 0。前端需要能区分「亏到 0」和「没数据」。
3. **金额累加用 `Decimal`，不用 `float`。** `0.1 + 0.2` 在 `float` 下不等于 `0.3`，几十笔操作累加后总成本会对不上账。

本阶段不做：

- 最大回撤
- 年化收益
- 夏普比率
- 持仓分布
- 操作频率
- 复杂净值复权

---

## 第 9 天：汇总看板与交付检查

| 顺序 | 任务 | 预计工时 | 产出 |
| --- | --- | --- | --- |
| 1 | 037 博主总览看板接口 | 2 小时 | `GET /api/v1/dashboards/bloggers` |
| 2 | 038 基金分布看板接口 | 2 小时 | `GET /api/v1/dashboards/funds` |
| 3 | 039 近期操作统计接口 | 2 小时 | `GET /api/v1/dashboards/recent-operations` |
| 4 | 040 功能闭环验收与文档同步 | 2 小时 | `docs/backend/design/day9-delivery-checklist.md` |

合计 8 小时。

### 第 9 天的接口契约

看板的接口文档已经写好，前后端共用：

```text
docs/api/v1-dashboards.md
```

任务 037–039 都以它为准。任务 040 只做验收和文档差异核对。开发过程中发现文档说不通的地方，反馈，不要自己改。

第 9 天目标：第一版功能闭环可以交给前端展示。

---

## 当前边界

本阶段包含：

- 操作记录 CRUD。
- 净值手动录入和 CSV 导入。
- 持仓快照计算。
- 简单收益计算。
- 基础汇总看板接口。
- 接口测试。

本阶段不包含：

- 用户认证。
- 权限系统。
- OCR。
- 自动净值同步。
- Docker。
- CI/CD。
- 最大回撤。
- 年化收益。
- 复杂账务规则。
- 操作记录和净值的编辑接口。
- 前端页面实现。

## 当前任务

当前应执行的任务见：

```text
docs/backend/plans/README.md
```

第 5 天的五个任务文件：

```text
docs/backend/tasks/018-operation-table-design.md
docs/backend/tasks/019-operation-table-create-and-init.md
docs/backend/tasks/020-create-operation-api.md
docs/backend/tasks/021-operation-query-api.md
docs/backend/tasks/022-delete-operation-and-tests.md
```

第 6 天的六个任务文件：

```text
docs/backend/tasks/023-common-pagination-and-sort-validation.md
docs/backend/tasks/024-nav-history-table-design.md
docs/backend/tasks/025-nav-history-table-create-and-init.md
docs/backend/tasks/026-manual-nav-history-api.md
docs/backend/tasks/027-nav-history-csv-parse-and-validate.md
docs/backend/tasks/028-nav-history-csv-import-api.md
```

第 8 天的四个任务文件：

```text
docs/backend/tasks/033-return-calculation-service.md
docs/backend/tasks/034-blogger-returns-api.md
docs/backend/tasks/035-fund-return-api.md
docs/backend/tasks/036-total-returns-api.md
```

第 7 天的四个任务文件：

```text
docs/backend/tasks/029-snapshot-date-and-nav-query-tools.md
docs/backend/tasks/030-position-snapshot-calculation.md
docs/backend/tasks/031-position-snapshot-api.md
docs/backend/tasks/032-position-snapshot-tests.md
```

第 8 天的四个任务文件：

```text
docs/backend/tasks/033-return-calculation-service.md
docs/backend/tasks/034-blogger-returns-api.md
docs/backend/tasks/035-fund-return-api.md
docs/backend/tasks/036-total-returns-api.md
```

第 9 天的四个任务文件：

```text
docs/backend/tasks/037-blogger-overview-dashboard-api.md
docs/backend/tasks/038-fund-distribution-dashboard-api.md
docs/backend/tasks/039-recent-operations-statistics-api.md
docs/backend/tasks/040-delivery-check-and-doc-sync.md
```

第 5–9 天任务文档已全部生成。后续阶段要另外创建新的计划文档，不要在当前 40 小时计划里私自扩展任务。

## 验收节奏

每完成一个任务，新手后端需要反馈：

1. 修改或新增的文件列表。
2. 验证命令和输出。
3. `pytest -q` 的完整输出（从任务 019 起每个任务都要跑，贴原文，不要只写「都通过了」）。
4. 响应字段是否和接口文档一致。
5. 有没有发现接口文档说不通的地方。
6. 遇到的问题。
7. 是否有未完成项。

只有任务验收通过后，才继续下一个任务。

## 后续任务池

工程优化和高级功能已放入：

```text
docs/backend/plans/backend-task-backlog.md
```

避免后续忘记。
