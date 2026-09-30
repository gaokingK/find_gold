# 后端 3 天 / 24 小时任务计划

## 说明

这是任务池，不是让新手后端一次全部执行。

执行原则仍然遵守 `AGENTS.md`：

1. 按顺序推进。
2. 一个任务只引入少量新概念。
3. 每个任务完成后必须验证。
4. 上一任务未验收，不开始下一任务。

## 总工时

| 任务 | 内容 | 预计工时 |
| --- | --- | --- |
| 001 | 搭建 Flask 环境并跑通 Hello World | 2 小时 |
| 002 | 拆分 Flask 项目结构 | 1.5 小时 |
| 003 | 创建统一成功响应函数 | 1 小时 |
| 004 | 理解和使用 query 参数 | 1.5 小时 |
| 005 | 创建统一错误响应函数 | 2 小时 |
| 006 | 接入 MySQL 基础连接 | 2 小时 |
| 007 | 初始化第一版基础数据表 | 2 小时 |
| 008 | 实现博主列表查询接口 | 2 小时 |
| 009 | 实现新增博主接口 | 2 小时 |
| 010 | 实现博主详情、编辑、删除接口 | 2 小时 |
| 011 | 实现基金列表、新增、编辑接口 | 2 小时 |
| 012 | 实现初始持仓列表、新增、编辑接口 | 2 小时 |
| 013 | 手工联调与验收检查 | 2 小时 |

合计：24 小时。

## 3 天安排

### 第 1 天：基础能力

| 顺序 | 任务 | 预计工时 | 产出 |
| --- | --- | --- | --- |
| 1 | 001 Flask 环境 | 2 小时 | Flask 服务可启动 |
| 2 | 002 项目结构拆分 | 1.5 小时 | `app/`、`routes/` 结构可用 |
| 3 | 003 统一成功响应函数 | 1 小时 | `success()` 可复用 |
| 4 | 004 query 参数 | 1.5 小时 | 能读取 GET query 参数 |
| 5 | 005 统一错误响应函数 | 2 小时 | `error()` 可复用 |

第 1 天目标：后端具备统一响应结构，能处理基础 GET 参数。

### 第 2 天：数据库与博主模块

| 顺序 | 任务 | 预计工时 | 产出 |
| --- | --- | --- | --- |
| 6 | 006 MySQL 基础连接 | 2 小时 | Flask 能连接 MySQL |
| 7 | 007 初始化基础数据表 | 2 小时 | 博主、基金、初始持仓表可创建 |
| 8 | 008 博主列表查询接口 | 2 小时 | `GET /api/v1/bloggers` 可用 |
| 9 | 009 新增博主接口 | 2 小时 | `POST /api/v1/bloggers` 可用 |

第 2 天目标：数据库可用，博主模块支持查询和新增。

### 第 3 天：完整基础数据模块

| 顺序 | 任务 | 预计工时 | 产出 |
| --- | --- | --- | --- |
| 10 | 010 博主详情、编辑、删除 | 2 小时 | 博主 CRUD 完成 |
| 11 | 011 基金接口 | 2 小时 | 基金查询、新增、编辑完成 |
| 12 | 012 初始持仓接口 | 2 小时 | 初始持仓查询、新增、编辑完成 |
| 13 | 013 手工联调与验收检查 | 2 小时 | 第一版基础数据模块可交付 |

第 3 天目标：第一版基础数据管理接口闭环。

## 当前任务

当前应执行的任务见：

```text
docs/backend/plans/README.md
```

进度只记在那一个文件里。本文档只说明第 1–3 天包含哪些任务，不写当前进度——写两处就一定会有一处过期。

第 1–3 天的任务文件：

```text
docs/backend/tasks/001-flask-hello-world.md
docs/backend/tasks/002-project-structure-split.md
docs/backend/tasks/003-success-response-function.md
docs/backend/tasks/004-query-parameters.md
docs/backend/tasks/005-error-response-function.md
docs/backend/tasks/006-mysql-basic-connection.md
docs/backend/tasks/007-init-basic-tables.md
docs/backend/tasks/008-blogger-list-api.md
docs/backend/tasks/009-create-blogger-api.md
docs/backend/tasks/010-blogger-detail-update-delete.md
docs/backend/tasks/011-fund-list-create-update.md
docs/backend/tasks/012-initial-position-list-create-update.md
docs/backend/tasks/013-manual-integration-and-acceptance.md
```

## 接口契约

第 1–3 天的三个模块（博主、基金、初始持仓）接口文档：

```text
docs/api/v1-basic-management.md
```

任务 008–013 都以它为准。发现文档说不通的地方，反馈，不要自己改。

两条容易踩的约定：

1. **成功响应统一返回 HTTP `200`**，新增接口也不返回 `201`。`success()` 没有 `http_status` 参数，传了会报 `TypeError`。
2. **列表接口的 `sort_by` 必须走白名单**，`page_size` 上限 `100`。排序字段是拼进 SQL 的，去掉白名单就是 SQL 注入。

## 验收节奏

每完成一个任务，新手后端需要反馈：

1. 修改或新增的文件列表。
2. 验证命令和输出。
3. 响应字段是否和 `docs/api/v1-basic-management.md` 一致（从任务 008 起）。
4. 有没有发现接口文档说不通的地方。
5. 遇到的问题。
6. 是否有未完成项。

只有任务验收通过后，才继续下一个任务。
