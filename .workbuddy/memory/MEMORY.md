# Fund Lens 项目长期记忆

## 项目定位
基金博主追踪系统（Fund Lens）。追踪基金博主持仓、买卖操作、收益表现，基于净值自主计算收益，
不信任平台展示的收益率。前端 Vue3 + Vite + TS（已完成，跑 mock 数据）；后端 Flask + MySQL。

## 当前协作模式（2026-10-26 确立）
- 后端**外包给一名新手工程师**，甲方（用户）不写后端代码。
- 我的角色：**需求分析 + 持续发布任务文档 + 功能验收**。
- 后端工程师推代码后，由用户通知我，我去验收。
- **重心是 task 的产出与审阅，不要过度纠结现有代码写成什么样**（用户明确要求）。

## 硬性约定
- 工作主分支：**master**。后端工程师从 master 新建独立分支推代码，我去该分支验收。
- 仓库：git@github.com:gaokingK/find_gold.git。`my-dev` 分支上有未合并的早期后端半成品。
- 任务文档位置：`docs/backend/tasks/`（现有 001–040）；计划：`docs/backend/plans/`。
- `docs/backend/plans/README.md` 顶部「当前应执行任务」是唯一进度指针，由我维护（曾停在 004 已过期）。
- 审阅报告：`docs/backend/review/`；验收记录：`docs/backend/acceptance/`。

## 验收环境
本机无 MySQL、无 Flask。已建隔离 venv：
`C:\Users\MW26090224424\.workbuddy\binaries\python\envs\default\Scripts\python.exe`
（Flask 3.0.3 / PyMySQL / pytest 9.1.1）。数据库连接信息待用户提供。

## 已知存量缺陷（待发修复任务）
1. `backend/database/v1-basic-management.sql` 用 `create_at`/`update_at`，
   但代码与早期 `backend/database/schema.sql` 用 `created_at`/`updated_at` — 两套 schema 命名冲突。
2. `bloggers.py` 的 `calculate_status()` 返回 `'obsering'`（拼写错误），
   参数校验只放行 `observing`/`active`。
3. `backend/requirements.txt` 锁定 `PyMySQL==1.1.1`，实际安装到 1.4.6。

## 全局技术约定
- 成功响应统一 HTTP 200（新增也不返回 201）；路径前缀 `/api/v1/`；后端字段 snake_case。
- 测试只连 `fund_test_db`（夹具会 TRUNCATE），连到 `fund_db` 会清空开发数据。
- 排序字段必须走白名单，page_size 上限 100。
- 金额份额用 DECIMAL，累加用 Decimal 不用 float。
- 成本 ≤ 0 时收益率返回 null；无净值日期市值返回 null（不许用最近净值顶替）。
- 第一版不校验超额卖出，剩余份额可为负，照实返回。
- DB 密码只走环境变量，不进 Git。

## 用户偏好
资深平台负责人（CMDB 方向）。要**直接判断和硬规则**，不要罗列中立选项、不要铺垫客套。
需要可落地的判据，而非泛泛方法论。
