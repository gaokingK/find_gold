# Fund Lens：基金博主追踪系统

一个用于追踪基金博主持仓、买卖操作和收益表现的研究型 Web 应用。  
项目目标是基于截图、OCR 识别、基金净值和原始操作记录，自主计算博主收益指标，而不是直接信任平台展示的收益率。

> 演示说明：当前前端 Demo 使用本地 mock 数据，不连接真实后端、真实净值接口或真实 OCR 服务，数据不能用于投资决策。

---

## 项目定位

Fund Lens 希望解决这些问题：

1. 追踪一批基金博主的观察期表现。
2. 录入或识别博主的日常买卖操作。
3. 通过净值和持仓数据自行计算收益率、累计收益、最大回撤等指标。
4. 保留截图和 OCR 原始数据，保证后续审计与复核。

核心原则：

- 自主计算收益，不信任平台展示的收益率。
- 数据可追溯，截图和 OCR 结果长期保存。
- 人工校验优先，OCR 结果必须经过确认后才进入正式数据。

---

## 当前状态

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| 前端 Demo | 已有基础版本 | Vue 3 + Vite + TypeScript，使用本地 mock 数据 |
| 第一版需求 | 已确认 | 先做博主管理、基金管理、初始持仓 |
| 接口文档 | 已生成 | 使用 `/api/v1/` 前缀 |
| 后端实现 | 进行中 | 当前仓库中还没有完整 Flask 服务实现 |
| 数据库设计 | 已有初稿 | 见 `backend/database/schema.sql` |
| OCR / 净值 / 收益计算 | 未开始 | 属于后续版本 |

---

## 技术栈

### 前端

- Vue 3
- Vite
- TypeScript
- Vue Router
- Element Plus
- ECharts
- Vitest

### 后端

- Python
- Flask
- MySQL

### 后续能力

- Umi-OCR
- 天天基金 / 蛋卷等净值数据源
- 定时净值同步
- 收益与回撤计算

---

## 目录结构

```text
.
├── AGENTS.md
├── README.md
├── backend/
│   ├── database/
│   │   └── schema.sql
│   ├── docs/
│   │   ├── algorithm-design.md
│   │   ├── ocr-extraction-design.md
│   │   ├── requirements.md
│   │   └── technical-spec.md
│   └── test/
├── docs/
│   ├── api/
│   │   └── v1-basic-management.md
│   ├── backend/
│   │   └── tasks/
│   └── requirements/
│       └── v1-basic-management.md
└── frontend/
    ├── package.json
    ├── src/
    └── tests/
```

---

## 文档索引

### 当前有效文档

| 文档 | 说明 |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | 当前阶段要求、角色分工、后端任务编排规则 |
| [`docs/requirements/v1-basic-management.md`](docs/requirements/v1-basic-management.md) | 第一版基础数据管理需求 |
| [`docs/api/v1-basic-management.md`](docs/api/v1-basic-management.md) | 第一版接口文档 |
| [`docs/backend/tasks/`](docs/backend/tasks) | 面向新手后端的分步开发任务 |

### 早期设计文档

以下文档位于 `backend/docs/`，内容偏整体设计和后续模块：

| 文档 | 说明 |
| --- | --- |
| [`backend/docs/requirements.md`](backend/docs/requirements.md) | 原始整体需求 |
| [`backend/docs/technical-spec.md`](backend/docs/technical-spec.md) | 原始技术方案 |
| [`backend/docs/algorithm-design.md`](backend/docs/algorithm-design.md) | 收益、持仓、回撤算法设计 |
| [`backend/docs/ocr-extraction-design.md`](backend/docs/ocr-extraction-design.md) | OCR 字段提取与去重设计 |

注意：如果早期文档与 `docs/` 下的当前版本文档冲突，以 `AGENTS.md`、`docs/requirements/` 和 `docs/api/` 为准。

---

## 第一版范围

第一版聚焦基础数据管理，不做 OCR、净值、收益计算。

### 包含模块

1. 博主管理
   - 新增博主
   - 查询博主列表
   - 查询博主详情
   - 编辑博主
   - 删除博主

2. 基金管理
   - 新增基金
   - 查询基金列表
   - 编辑基金

3. 初始持仓
   - 新增初始持仓
   - 查询初始持仓列表
   - 编辑初始持仓

### 第一版不包含

- 截图上传
- OCR 识别
- 净值同步
- 操作记录
- 收益计算
- 最大回撤
- 用户认证
- 权限系统

---

## 前端启动

### 环境要求

- Node.js 22 或更高版本
- npm

### 安装依赖

在项目根目录下执行：

```bash
cd frontend
npm ci
```

### 本地开发

```bash
npm run dev
```

默认使用本地 mock 数据，不依赖 Flask 后端。

### 单元测试

```bash
npm run test:unit
```

### 构建生产包

```bash
npm run build
```

### 页面列表

| 路由 | 页面 | 说明 |
| --- | --- | --- |
| `/` | 博主总览 | 展示博主列表、观察状态、收益相关 mock 指标 |
| `/bloggers/:id` | 博主详情 | 展示持仓、操作历史、图表 |
| `/import` | 截图导入 | 演示截图导入和 OCR 审核流程 |
| `/history` | 历史记录 | 查看导入批次和 OCR 原文 |
| `/settings` | 基础设置 | 管理博主、基金、初始持仓 mock 数据 |

---

## 后端开发状态

当前后端尚未提供完整可运行的 Flask 服务，正在按新手友好的任务拆分推进。

后续后端开发约定：

1. 使用 Flask。
2. 使用 MySQL。
3. API 路径统一使用 `/api/v1/`。
4. 后端 JSON 字段使用 `snake_case`，例如 `blogger_id`。
5. 前端内部字段可以使用 `camelCase`，由前端 service 层负责映射。
6. 接口返回结构应保持统一。

数据库初稿位于：

```text
backend/database/schema.sql
```

后端开发任务位于：

```text
docs/backend/tasks/
```

---

## API 约定

### 路径

统一使用版本前缀：

```text
/api/v1/
```

### 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

### 错误响应

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

### 常见状态码

| HTTP 状态码 | 含义 |
| --- | --- |
| 200 | 成功 |
| 400 | 参数错误 |
| 404 | 资源不存在 |
| 409 | 业务冲突 |
| 500 | 服务器内部错误 |

---

## 角色与协作方式

| 角色 | 职责 |
| --- | --- |
| 前端负责人 | 负责前端页面、交互和技术栈选型 |
| 后端开发 | 负责按接口文档实现 Flask 后端 |
| AI 助手 | 负责维护需求文档、接口文档，并按新手友好方式编排后端任务 |

协作原则：

1. 需求未确认前，不直接修改页面或后端代码。
2. 接口字段一旦确定，变更必须同步更新接口文档。
3. 后端任务必须按难度递进拆分。
4. 每个任务必须有明确目标、步骤、必要性和验证方式。
5. 前端可以在后端未完成时基于接口文档使用 mock 数据开发。

---

## 后续规划

### 第二阶段：基础数据接口

- 实现 Flask 环境和项目结构
- 接入 MySQL
- 实现博主、基金、初始持仓接口
- 统一参数校验和错误响应

### 第三阶段：截图与 OCR

- 截图上传
- Umi-OCR 集成
- OCR 字段提取
- 疑似重复检测
- 人工确认流程

### 第四阶段：净值数据

- 接入基金净值数据源
- 基金代码与名称匹配
- 每日净值同步
- 历史净值存储

### 第五阶段：收益计算

- 根据初始持仓和操作记录计算份额
- 根据净值计算市值
- 计算收益率、累计收益
- 计算最大回撤
- 生成持仓和收益快照

---

## 免责声明

本项目仅用于个人研究与数据追踪。  
项目中的前端 Demo 数据是 mock 数据，不能用于投资决策。  
后续即使接入真实数据，项目输出也不构成任何投资建议。
