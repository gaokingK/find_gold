# Fund Lens 基金博主追踪 Demo

这是一个独立的 Vue 3 + Vite + TypeScript 前端 Demo，用于验证基金博主浏览、收益查看、截图导入和人工审核流程。

## 环境与运行

- Node.js 22 或更高版本
- `npm ci`
- `npm run dev`
- `npm run test:unit`
- `npm run build`

Demo 阶段默认使用 `VITE_DATA_MODE=mock`，所有数据来自本地 mock service，不连接 Flask、MySQL、Umi-OCR、天天基金、蛋卷或任何真实净值接口。前端页面只依赖 `src/services/` 和 `src/types/`，没有上传真实文件或调用后端 API。

## 页面

- `/` 博主总览
- `/bloggers/:id` 博主详情
- `/import` 截图导入
- `/history` 历史记录
- `/settings` 基础设置

这是演示版本，收益数据是固定模拟结果，不能用于投资决策。
