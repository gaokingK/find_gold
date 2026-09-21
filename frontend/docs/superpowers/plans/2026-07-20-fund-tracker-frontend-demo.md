# Fund Tracker Frontend Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 在独立前端仓库中生成一个可运行、可点击、使用模拟数据的基金博主追踪 Demo，先验证博主浏览、收益查看、截图导入和人工确认流程，再接入独立 Flask 后端仓库。

**Architecture:** 前端使用 Vue 3 单页应用，Vite 负责开发服务器和生产构建，Vue Router 负责页面路由，Element Plus 负责后台管理组件，ECharts 负责收益与持仓图表。Demo 阶段所有数据通过 `src/mocks/` 提供，页面只依赖 `src/services/` 定义的接口，不直接依赖 Flask、MySQL 或 Umi-OCR。未来接入后端时只替换 service 实现，不修改页面组件的业务数据结构。

**Tech Stack:** Vue 3、Vite、TypeScript、Vue Router 4、Element Plus、ECharts、Vitest、Vue Test Utils。

## 为什么选择 Vue 3 + Vite + Element Plus

1. **适合当前产品形态。** 这是单用户、后台管理型应用，核心交互是表格、筛选、表单、文件上传、弹窗确认和详情页。Element Plus 已覆盖这些组件，首版不需要从零设计和实现控件。
2. **开发反馈快。** Vite 官方提供 Vue 模板、开发服务器、HMR 和 `vite build` 生产构建，适合先快速验证页面，再逐步接 API。
3. **前后端天然解耦。** Vue 产出静态 `dist/`，部署时可以由 Nginx 托管；Flask 只提供 API。1C1G 服务器不需要运行 Node.js，也不会因前端框架增加运行时内存负担。
4. **后续扩展成本低。** Vue Router、TypeScript 和独立 service 层可以承载后续的 OCR 审核、净值同步、收益计算和历史数据功能。
5. **比 Flask 模板更适合当前交互。** Flask 模板可以更快显示静态页面，但上传后审核、局部刷新、筛选状态、详情图表会逐渐变成模板与 JavaScript 混杂；独立 SPA 更符合用户已经确定的两个仓库边界。
6. **比 React + Ant Design 更省首版决策成本。** 两套方案都可行，但当前没有既有 React 代码或团队约束；Vue 的单文件组件和 Element Plus 的中文后台组件更适合单人快速开发。

官方依据：Vite Vue 脚手架为 `npm create vite@latest <app> -- --template vue-ts`；Element Plus 支持通过 `app.use(ElementPlus)` 和全局样式快速接入；Vue 3 使用 `createApp` 挂载应用。

## Global Constraints

- 前端和后端必须是两个独立 Git 仓库；本计划中的前端仓库路径均相对于前端仓库根目录。
- 实现前端 Demo 时不得修改 Flask 后端仓库，也不得把后端代码复制到前端仓库。
- Demo 阶段不得调用真实 Umi-OCR、天天基金、蛋卷或任何外部 API。
- Demo 阶段不得要求 MySQL、Redis、登录系统或用户认证。
- 所有页面展示文案使用中文；代码标识符和文件名使用英文。
- 所有金额使用人民币元，展示两位小数；收益率和回撤使用百分比，展示两位小数。
- 观察天数少于 30 天时，状态必须是 `观察期中`，收益指标显示为 `--`，不得伪装成正式排名数据。
- 不实现真实基金收益算法；Demo 只展示固定模拟结果，真实计算由后端阶段实现。
- 不实现真实 OCR 解析；上传后的 OCR 结果必须由本地 mock service 返回确定性数据。
- 不能使用 `any`、`@ts-ignore` 或 `@ts-expect-error` 绕过 TypeScript 错误。
- 依赖安装后必须提交 `package-lock.json`，使用 `npm ci` 可重复安装。

## Repository Boundary

### This independent frontend repository owns

- Vue/Vite 工程配置和静态资源。
- 页面、路由、组件、模拟数据和 service adapter。
- 前端展示状态、表单校验、上传审核交互。
- 后续通过 HTTP 调用 Flask API 的客户端代码。

### The backend repository owns

- Flask API、MySQL 数据、收益计算、净值同步和 Umi-OCR 调用。
- 文件长期存储、OCR 原文持久化和操作审计。
- API 鉴权（如果未来增加）。

### Integration rule

页面只能依赖 `src/services/*.ts` 导出的函数和 `src/types/*.ts` 的类型。页面不得直接写 `fetch`、不得导入 mock JSON、不得拼接后端 URL。Demo 使用 mock adapter；真实接入时新增 `http` adapter，并通过 `VITE_DATA_MODE=mock|http` 选择实现。

## Demo Scope

首版固定实现五个路由，覆盖原需求中的四个核心模块和历史记录模块：

| Route | 页面 | 目的 |
|---|---|---|
| `/` | 博主总览 | 按板块浏览博主，查看观察状态和收益摘要 |
| `/bloggers/:id` | 博主详情 | 查看收益卡片、持仓表、持仓分布、操作频率和操作历史 |
| `/import` | 截图导入 | 选择操作日期、上传图片、查看 mock OCR、编辑并确认记录 |
| `/history` | 历史记录 | 按日期查看截图、OCR 状态和已确认操作 |
| `/settings` | 基础设置 | 管理博主、基金和初始持仓的模拟数据 |

### Explicitly out of scope

- 登录、注册、权限和多用户协作。
- 真实 OCR、真实 NAV、真实数据库和真实文件上传。
- 删除博主后的级联数据处理。
- 复杂图表导出、Excel 导入、拖拽排序和移动端 App。
- 真实的收益率、最大回撤和成本计算。

## Fixed Mock Data Contract

在 `src/types/domain.ts` 中定义以下类型，页面和 service 必须使用这些类型：

```ts
export type BloggerStatus = 'active' | 'observing' | 'inactive'
export type OperationType = 'buy' | 'sell'
export type ReviewAction = 'pending' | 'accepted' | 'rejected'

export interface BloggerSummary {
  id: number
  name: string
  sector: string
  observeStartDate: string // YYYY-MM-DD
  observeDays: number
  status: BloggerStatus
  returnRate: number | null // decimal, 0.1568 = 15.68%
  profit: number | null
  maxDrawdown: number | null // decimal, -0.0823 = -8.23%
  operationCount: number
}

export interface Position {
  fundId: number
  fundName: string
  fundCode: string
  shares: number
  costBasis: number
  currentNav: number
  marketValue: number
  profit: number
  allocation: number // decimal
}

export interface Operation {
  id: number
  bloggerId: number
  fundId: number
  fundName: string
  operationDate: string
  operationType: OperationType
  amount: number
  shares: number | null
  screenshotId: number | null
  reviewAction: ReviewAction
  suspectedDuplicate: boolean
}

export interface BloggerDetail extends BloggerSummary {
  positions: Position[]
  operations: Operation[]
  monthlyOperationCount: Array<{ month: string; count: number }>
}

export interface ParsedOcrRecord {
  id: string
  bloggerName: string
  sector: string
  fundName: string
  operationAmount: number
  holdingProfit: number | null
  cumulativeProfit: number | null
  return1y: number | null
  return3y: number | null
  maxDrawdown: number | null
  suspectedDuplicate: boolean
  reviewAction: ReviewAction
}

export interface ScreenshotImportResult {
  screenshotId: number
  fileName: string
  operationDate: string
  rawText: string
  records: ParsedOcrRecord[]
}
```

### Required mock scenarios

The mock data must include all of these cases:

1. 一个观察超过 30 天且有正收益的博主。
2. 一个观察不足 30 天的博主，`returnRate`、`profit`、`maxDrawdown` 均为 `null`，页面显示 `观察期中` 和 `--`。
3. 一个收益为负且有最大回撤的博主。
4. 一个 OCR 记录被标记为疑似重复。
5. 一次上传中至少包含两条基金操作，其中一条可以被编辑后确认，另一条可以拒绝。

## Mock Service Interfaces

在 `src/services/` 中实现以下接口。页面只调用这些函数，不直接操作 mock 数组：

```ts
export interface BloggerQuery {
  sector?: string
  status?: BloggerStatus | 'all'
  keyword?: string
  sortBy?: 'returnRate' | 'observeDays' | 'profit'
}

export function listBloggers(query?: BloggerQuery): Promise<BloggerSummary[]>
export function getBloggerDetail(id: number): Promise<BloggerDetail>
export function listSectors(): Promise<string[]>
export function listHistory(operationDate?: string): Promise<ScreenshotImportResult[]>
export function listFunds(): Promise<Array<{ id: number; name: string; code: string }>>
export function listInitialPositions(bloggerId?: number): Promise<Position[]>
export function recognizeScreenshot(file: File, operationDate: string): Promise<ScreenshotImportResult>
export function confirmOcrRecords(
  screenshotId: number,
  records: ParsedOcrRecord[],
): Promise<{ accepted: number; rejected: number }>
```

Mock service requirements:

- Every function returns a Promise，以模拟 HTTP 延迟 150ms 至 300ms。
- `recognizeScreenshot` 不读取图片内容，只使用文件名和操作日期返回固定记录；文件名显示在结果中。
- `confirmOcrRecords` 只更新前端 mock store 的审核状态，并返回 accepted/rejected 数量。
- 页面刷新前的编辑和确认状态必须可见；不要求跨浏览器刷新持久化。
- service 不能抛出未处理异常；失败场景通过明确的 `Error` 返回给页面，由页面显示 `ElMessage.error`。

## Page Behavior

### 1. Overview `/`

- 页面标题：`博主总览`。
- 顶部显示总博主数、正式观察人数、观察期中人数、平均收益率四个摘要卡片。
- 筛选：关键词、板块、状态、排序字段。
- 表格列：博主名称、板块、观察开始日、观察天数、状态、收益率、累计收益、最大回撤、操作次数、详情。
- 点击“详情”跳转 `/bloggers/:id`。
- `observing` 行使用浅灰状态标签；收益率、累计收益、最大回撤显示 `--`。
- 空结果显示 Element Plus empty state，不显示假数据。

### 2. Detail `/bloggers/:id`

- 页面顶部有返回总览按钮、博主名称、板块、观察开始日和观察状态。
- 摘要卡片：收益率、累计收益、最大回撤、观察天数；不足 30 天的三项指标显示 `--`。
- 持仓表列：基金名称、代码、份额、成本、当前净值、市值、收益、占比。
- 使用 ECharts 饼图显示持仓分布，使用 ECharts 柱状图显示每月操作次数。
- 操作历史表列：日期、基金名称、买卖类型、金额、份额、来源截图、审核状态。
- 找不到 ID 时显示错误页，并提供返回总览按钮。

### 3. Import `/import`

- 首屏必须先选择操作日期；默认值为当天，格式 `YYYY-MM-DD`。
- 使用 `el-upload` 支持 PNG/JPG/JPEG，多选，单文件最大 10MB；Demo 不真正上传服务器。
- 文件选择后逐个调用 `recognizeScreenshot`，显示 loading、文件名、OCR 状态和结果数量。
- OCR 结果以可编辑表格展示：博主、板块、基金、操作金额、平台持有收益、平台累计收益、近一年收益率、近三年收益率、最大回撤率、审核操作。
- 疑似重复记录必须显示醒目标记，并在行内显示“与已有记录疑似重复”。
- 每条记录支持“编辑、接受、拒绝”；编辑状态保存到本地组件状态。
- 点击“确认本批记录”前，若还有 `pending` 记录，显示确认提示；确认后调用 `confirmOcrRecords`，显示统计结果并将记录标为已处理。
- 未选择日期、没有文件或操作金额不是合法数字时禁止提交，并显示字段错误。
- Demo 中不得调用后端 `/api/screenshots/upload`。

### 4. History `/history`

- 日期筛选默认最近操作日期。
- 表格列：截图文件名、操作日期、识别状态、记录数量、确认数量、查看详情。
- 查看详情打开抽屉，展示 OCR 原文和结构化记录。
- 不提供真实图片 URL；如果没有持久化预览地址，显示文件名和“Demo 未保存图片预览”。

### 5. Settings `/settings`

- 使用 tabs 分为：博主管理、基金管理、初始持仓。
- 博主管理：新增和编辑名称、板块、观察开始日；删除按钮在 Demo 中显示二次确认，但可以只从 mock store 删除。
- 基金管理：显示基金名称和代码，支持新增和编辑。
- 初始持仓：选择博主和基金，编辑份额、成本金额和记录日期；金额必须大于等于 0，份额必须大于等于 0。
- 所有表单使用 Element Plus Form 校验；成功后显示 `ElMessage.success`。

## Shared Layout and Visual Rules

- `AppShell.vue` 提供左侧导航、顶部标题和主内容区域。
- 侧边栏菜单固定为：总览、截图导入、历史记录、基础设置。
- 当前路由菜单项高亮；详情页仍高亮“总览”。
- 页面最大内容宽度不设固定窄宽，表格在桌面端占满主区域。
- 使用 Element Plus 默认组件风格，不引入第二套 UI 组件库。
- 使用 CSS 变量定义背景、边框、成功色、警告色和负收益色；负收益用红色，正收益用绿色，观察期用灰色。
- Demo 至少支持 1280px 桌面宽度和 768px 平板宽度；不要求手机端完整布局。
- 不使用渐变背景、营销页 Hero、登录页或与业务无关的装饰。

## Frontend Repository Structure

最终目录必须接近以下结构，允许只增加测试辅助文件，不改变职责边界：

```text
frontend-repo/
├── public/
├── src/
│   ├── assets/
│   ├── components/
│   │   ├── AppShell.vue
│   │   ├── MetricCard.vue
│   │   ├── BloggerStatusTag.vue
│   │   ├── PositionTable.vue
│   │   ├── OperationTable.vue
│   │   ├── OcrReviewTable.vue
│   │   └── EmptyState.vue
│   ├── layouts/
│   │   └── AppLayout.vue
│   ├── mocks/
│   │   ├── data.ts
│   │   └── store.ts
│   ├── router/
│   │   └── index.ts
│   ├── services/
│   │   ├── types.ts
│   │   ├── mock-service.ts
│   │   └── index.ts
│   ├── types/
│   │   └── domain.ts
│   ├── utils/
│   │   ├── formatters.ts
│   │   └── validators.ts
│   ├── views/
│   │   ├── OverviewView.vue
│   │   ├── BloggerDetailView.vue
│   │   ├── ImportView.vue
│   │   ├── HistoryView.vue
│   │   └── SettingsView.vue
│   ├── App.vue
│   ├── main.ts
│   └── styles.css
├── tests/
│   ├── unit/
│   │   ├── formatters.test.ts
│   │   ├── mock-service.test.ts
│   │   └── import-flow.test.ts
│   └── e2e/  # 可选；若未配置浏览器，不得阻塞 unit/build 验证
├── .env.example
├── index.html
├── package.json
├── package-lock.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## Future Flask API Contract

Demo 先使用 mock service，但必须让真实 adapter 可以无歧义替换。后端 API 的 HTTP 路径和最小响应契约固定如下：

```text
GET    /api/bloggers?sector=&status=&keyword=&sort_by=
GET    /api/bloggers/{id}
GET    /api/bloggers/sectors
GET    /api/funds
GET    /api/initial-positions?blogger_id=
GET    /api/history?operation_date=
POST   /api/screenshots/upload   multipart: operation_date, files[]
POST   /api/screenshots/{id}/confirm
```

响应外层统一为：

```json
{ "code": 0, "message": "ok", "data": {} }
```

错误响应统一为：

```json
{ "code": 400, "message": "可读的中文错误信息", "data": null }
```

后端字段命名可以保持 snake_case；真实 adapter 必须在边界处转换为前端的 camelCase 类型。页面组件不能同时兼容两套字段命名。

## Implementation Tasks

### Task 1: Scaffold the independent frontend repository

**Files:**
- Create: `package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig*.json`, `index.html`
- Create: `src/main.ts`, `src/App.vue`, `src/styles.css`
- Create: `.env.example`, `README.md`

**Steps:**

- [ ] 在独立前端仓库根目录执行：

```bash
npm create vite@latest . -- --template vue-ts
npm install vue-router@4 element-plus echarts
npm install -D vitest @vue/test-utils jsdom
```

- [ ] 在 `package.json` 固定脚本：`dev: vite`、`build: vite build`、`preview: vite preview`、`test:unit: vitest run`。
- [ ] 在 `src/main.ts` 使用 `createApp(App)`，注册 router 和 Element Plus，并导入 `element-plus/dist/index.css` 与 `src/styles.css`。
- [ ] 在 `.env.example` 定义 `VITE_DATA_MODE=mock` 和 `VITE_API_BASE_URL=http://localhost:5000`。
- [ ] README 必须写明 Node.js 版本要求、`npm ci`、`npm run dev`、`npm run test:unit`、`npm run build` 和 Demo 不连接后端。

**Verification:**

```bash
npm ci
npm run build
npm run test:unit
```

Expected: build exits 0; test command succeeds even before page-specific tests are added.

### Task 2: Define domain types, mock data, and service boundary

**Files:**
- Create: `src/types/domain.ts`
- Create: `src/mocks/data.ts`, `src/mocks/store.ts`
- Create: `src/services/types.ts`, `src/services/mock-service.ts`, `src/services/index.ts`
- Create: `src/utils/formatters.ts`, `src/utils/validators.ts`
- Test: `tests/unit/formatters.test.ts`, `tests/unit/mock-service.test.ts`

**Steps:**

- [ ] 复制本计划的 `Fixed Mock Data Contract` 类型，不增加第二套同义类型。
- [ ] 创建满足五个 required mock scenarios 的固定数据。
- [ ] 实现 `listBloggers` 的关键词、板块、状态过滤和收益/观察天数/累计收益排序。
- [ ] 实现 `getBloggerDetail`、`listHistory`、`listFunds`、`listInitialPositions`。
- [ ] 实现 `recognizeScreenshot` 和 `confirmOcrRecords`，所有方法返回带 150ms 至 300ms 延迟的 Promise。
- [ ] `formatters.ts` 提供 `formatCurrency(value: number | null): string`、`formatPercent(value: number | null): string`、`formatDate(value: string): string`；null 必须返回 `--`。
- [ ] 单元测试必须覆盖 null 格式化、观察期数据筛选、疑似重复记录和确认后 accepted/rejected 计数。

**Verification:**

```bash
npm run test:unit -- tests/unit/formatters.test.ts tests/unit/mock-service.test.ts
```

Expected: all tests pass and no test imports a Vue view.

### Task 3: Add router and shared application shell

**Files:**
- Create: `src/router/index.ts`
- Create: `src/layouts/AppLayout.vue`
- Create: `src/components/AppShell.vue`, `src/components/MetricCard.vue`, `src/components/BloggerStatusTag.vue`, `src/components/EmptyState.vue`
- Modify: `src/App.vue`, `src/main.ts`

**Steps:**

- [ ] 注册五个固定路由：`/`、`/bloggers/:id`、`/import`、`/history`、`/settings`。
- [ ] `AppLayout.vue` 只负责渲染 router view；`AppShell.vue` 负责侧边栏、顶部标题和导航高亮。
- [ ] 详情路由仍让“总览”菜单项高亮。
- [ ] 菜单文案固定为：总览、截图导入、历史记录、基础设置。
- [ ] `MetricCard` 接收 `label`、`value`、`tone` props；不在组件内读取 mock 数据。
- [ ] `BloggerStatusTag` 接收 `BloggerStatus`，将 `active/observing/inactive` 映射为 `已达标/观察期中/未开始`。

**Verification:**

```bash
npm run build
```

Expected: all five paths compile; navigating directly to each path does not produce a TypeScript error.

### Task 4: Implement overview and detail views

**Files:**
- Create: `src/views/OverviewView.vue`, `src/views/BloggerDetailView.vue`
- Create: `src/components/PositionTable.vue`, `src/components/OperationTable.vue`
- Test: `tests/unit/overview-view.test.ts`

**Steps:**

- [ ] Overview 使用 service 加载数据，不直接导入 mock data。
- [ ] 实现四个摘要卡片、关键词/板块/状态筛选、排序和博主表格。
- [ ] 对 `observing` 博主严格显示 `观察期中`、指标 `--`。
- [ ] Detail 根据路由参数加载 `BloggerDetail`；实现摘要卡、持仓表、操作表和错误状态。
- [ ] 使用 ECharts 绘制持仓饼图和月度操作柱状图；图表数据只来自 `BloggerDetail.positions` 和 `monthlyOperationCount`。
- [ ] 图表容器必须在组件卸载时 `dispose`，避免路由切换造成实例泄漏。
- [ ] 测试至少覆盖：筛选后表格行数、观察期 `--`、详情链接参数和找不到 ID 的错误状态。

**Verification:**

```bash
npm run test:unit -- tests/unit/overview-view.test.ts
npm run build
```

### Task 5: Implement screenshot import and OCR review flow

**Files:**
- Create: `src/views/ImportView.vue`
- Create: `src/components/OcrReviewTable.vue`
- Create: `src/utils/upload.ts`
- Test: `tests/unit/import-flow.test.ts`

**Steps:**

- [ ] 日期字段默认当天且保存为 `YYYY-MM-DD`。
- [ ] 使用 Element Plus `el-upload` 支持 PNG/JPG/JPEG、多选和 10MB 单文件限制。
- [ ] 文件进入队列后调用 `recognizeScreenshot`，显示处理中、成功、失败三种状态。
- [ ] OCR 表格支持编辑操作金额、收益率和审核状态；编辑值必须保持在组件状态中，不能直接修改 mock 常量。
- [ ] 疑似重复记录用 warning tag 和文字提示突出显示。
- [ ] 没有日期、没有文件、金额不是有限数字时禁止确认。
- [ ] 确认前对 pending 记录显示 `ElMessageBox.confirm`；确认后调用 `confirmOcrRecords`，显示接受/拒绝统计。
- [ ] 测试覆盖：文件识别、编辑金额、拒绝记录、确认统计、缺少日期时不能确认。

**Verification:**

```bash
npm run test:unit -- tests/unit/import-flow.test.ts
npm run build
```

### Task 6: Implement history and settings views

**Files:**
- Create: `src/views/HistoryView.vue`, `src/views/SettingsView.vue`
- Test: `tests/unit/settings-view.test.ts`

**Steps:**

- [ ] History 调用 `listHistory`，支持日期筛选、状态显示和详情抽屉。
- [ ] OCR 原文使用等宽字体和可滚动容器展示；未保存图片明确显示 `Demo 未保存图片预览`。
- [ ] Settings 使用三个 tabs：博主管理、基金管理、初始持仓。
- [ ] 三类表单都必须有 Element Plus rules；数值字段不得为负数。
- [ ] 新增、编辑、删除只作用于 mock store；删除必须二次确认。
- [ ] 成功操作显示 `ElMessage.success`，失败显示 `ElMessage.error`。
- [ ] 测试覆盖表单必填校验和删除确认行为。

**Verification:**

```bash
npm run test:unit -- tests/unit/settings-view.test.ts
npm run build
```

### Task 7: Perform visual and functional QA for the complete Demo

**Files:**
- Modify: `README.md` only if startup or scope instructions are incomplete
- Create: `docs/demo-qa.md` in the frontend repository

**Steps:**

- [ ] 使用 `npm ci` 从 lockfile 全新安装。
- [ ] 使用 `npm run dev -- --host 127.0.0.1` 启动开发服务器。
- [ ] 手动验证五个路由可以进入，侧边栏高亮和返回按钮正常。
- [ ] 手动验证观察期中博主的三个收益指标均显示 `--`。
- [ ] 手动验证截图导入：选择日期、选择两张图片、看到 OCR 结果、编辑一条、拒绝一条、确认批次。
- [ ] 手动验证历史抽屉可以看到 OCR 原文和结构化记录。
- [ ] 手动验证基础设置的新增/编辑/删除确认和持仓数值校验。
- [ ] 在 1280px 桌面宽度和 768px 平板宽度检查表格无不可读的横向溢出；必要时允许表格自身横向滚动。
- [ ] 执行 `npm run test:unit` 和 `npm run build`，将结果和已知限制记录到 `docs/demo-qa.md`。

**Acceptance criteria:**

- `npm ci && npm run test:unit && npm run build` 全部退出码为 0。
- 五个路由可访问，页面不依赖后端服务。
- 所有 required mock scenarios 可在界面中观察到。
- OCR 审核流程可完成编辑、接受、拒绝和重复提示。
- 没有浏览器 console error、未处理 Promise rejection 或 TypeScript 错误。
- README 明确说明：这是 mock Demo，尚未接入 Flask、MySQL、Umi-OCR 和真实净值接口。

## Backend Integration Handoff

Demo 验收后，另一个后端实施计划只能按以下顺序接入：

1. 在前端新增 `src/services/http-service.ts`，实现与 mock service 同名的函数签名。
2. 在 `src/services/index.ts` 根据 `import.meta.env.VITE_DATA_MODE` 选择 mock 或 http adapter。
3. 只在 `http-service.ts` 处理 snake_case 到 camelCase 的映射、HTTP 状态码和 API 外层 `code/message/data`。
4. 页面、组件、类型和路由不因切换 adapter 而改变。
5. 真实上传接口使用 `FormData` 字段 `operation_date` 和 `files[]`，不能把图片转成 base64 发送给 Flask，除非后端契约另行修改。
6. 后端未实现时保留 `VITE_DATA_MODE=mock`，确保前端仍可独立演示。

## Plan Self-Review

- **Scope coverage:** 覆盖总览、详情、截图导入、历史、设置、mock 数据、未来 API 边界、测试和验收。
- **Placeholder scan:** 未留下未决占位事项；前端仓库名称和真实后端地址通过明确环境变量处理。
- **Type consistency:** 页面统一使用 `domain.ts` 类型；service 函数签名、mock 数据和未来 HTTP adapter 的函数名一致。
- **Repository isolation:** 所有实现路径都相对于独立前端仓库；本后端仓库只保存本计划，不要求复制或修改 Flask 代码。

## Official References

- Vue 3: https://vuejs.org/guide/quick-start.html
- Vite: https://vite.dev/guide/
- Element Plus installation: https://element-plus.org/en-US/guide/installation.html
- Element Plus quick start: https://element-plus.org/en-US/guide/quickstart.html
