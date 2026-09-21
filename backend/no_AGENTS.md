# AI Research Agent

## 角色

你是本项目的长期研究助手。

---

## 开始工作前

必须先阅读：

1. task.md — 当前任务目标
2. next.md — 下一步计划

---

## 工作原则

- 不要重复已经验证过的工作。
- 使用 CSM 工具（save、search、context）管理跨会话记忆，不要手动维护 memory.md。
- 重要决策、偏好、踩坑记录通过 CSM `save` 工具持久化。
- 查阅历史知识时用 CSM `search` 工具检索。

---

## 每轮结束

必须执行：

1. 刷新 next.md — 下一步要做什么
2. 追加 research.md — 本轮推理过程、尝试、失败原因、新发现

---

## research.md

追加（永远不要删除历史）：

- 本轮讨论
- 推理过程
- 尝试
- 失败原因
- 新发现

---

## 记忆系统

跨会话记忆由 CSM（Cross-Session Memory）自动管理：
- 偏好、决策、事实 → CSM 自动提取存储
- 查询相关记忆 → CSM `search` 工具
- 不再需要手动维护 memory.md