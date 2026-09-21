# 需求文档 v1.0

---

## 1. 项目概述

### 1.1 目标
开发一个 Web 应用,帮助用户追踪约 100 位基金博主的日常操作,并通过原始买卖记录自行计算收益率等指标。

### 1.2 核心原则
- **自主计算收益**: 不信任平台提供的收益率,基于买卖记录和净值数据自行计算
- **数据可追溯**: 截图和 OCR 结果长期保存,支持审计
- **人工校验**: OCR 提取后需人工二次确认,避免错误和重复

### 1.3 用户规模
- 单用户(暂无需用户认证系统)

---

## 2. 功能需求

### 2.1 博主管理
- **添加博主**: 录入博主名称、所属板块
- **编辑博主**: 修改博主信息
- **删除博主**: 删除博主及其相关数据(需确认)
- **博主列表**: 按板块分组显示,展示观察天数、状态标记

### 2.2 初始持仓录入
- **手动录入**: 支持录入观察起始日的持仓情况
- **字段**: 博主、基金名称、持有份额、成本金额、起始日期
- **修改**: 支持后续修改初始持仓数据

### 2.3 日常操作录入

**流程:**
1. 用户选择操作日期
2. 上传截图(支持批量上传多张)
3. 系统调用 Umi-OCR 提取文本
4. 系统解析并结构化数据(博主名称、板块、基金名称、操作金额)
5. 系统标记疑似重复项(同一博主+同一基金+同一日期+相近金额)
6. 人工确认每条记录(接受/拒绝/编辑)
7. 存入数据库

**截图字段提取:**
- 板块
- 博主名称
- 持有收益金额(平台数据,仅供参考)
- 累计收益金额(平台数据,仅供参考)
- 近一年收益率(平台数据,仅供参考)
- 近三年收益率(平台数据,仅供参考)
- 最大回撤率(平台数据,仅供参考)
- 基金名称
- 操作(买卖金额)

**去重逻辑:**
- 相同博主 + 相同基金 + 相同日期 + 金额差异 < 10% → 标记为疑似重复
- 展示已存在的记录供用户对比确认

### 2.4 净值数据获取
- **自动拉取**: 根据基金名称或代码,自动从外部接口获取每日净值
- **净值数据源**: 待定(天天基金/蛋卷等)
- **存储**: 存储历史净值数据,减少重复请求

### 2.5 收益计算

**计算逻辑:**
- 起始点: 从观察日开始计算
- 最小观察期: 30 天
- 未满 30 天的博主: 显示特殊标记(如"观察期中"或灰色状态)

**计算指标:**

| 指标 | 计算方式 |
|------|----------|
| 收益率 | (当前市值 - 累计投入成本) / 累计投入成本 |
| 累计收益金额 | 当前市值 - 累计投入成本 |
| 最大回撤 | 历史最高点后的最大跌幅 |
| 持仓分布 | 各基金持仓占比(按市值) |
| 操作频率统计 | 每月/每季度操作次数 |

**分红处理:**
- 不单独记录分红事件
- 通过净值变化自动反映(分红后净值下降)

### 2.6 数据展示

**博主总览页:**
- 按板块分组
- 每个博主显示: 观察天数、收益率、累计收益、状态标记
- 支持按收益率/观察天数排序/筛选

**博主详情页:**
- 基本信息: 博主名称、板块、观察起始日
- 收益指标: 收益率、累计收益金额、最大回撤
- 持仓列表: 基金名称、份额、成本、当前市值、盈亏
- 操作历史: 日期、基金、操作类型(买入/卖出)、金额、份额
- 持仓分布图: 饼图展示各基金占比
- 操作频率图: 按月/季度统计操作次数

**历史数据页:**
- 截图归档: 按日期查看历史上传的截图
- OCR 结果: 查看提取的原始文本
- 操作记录: 查看确认后的结构化数据

---

## 3. 非功能需求

### 3.1 技术栈
- **后端**: Python Flask
- **数据库**: MySQL
- **前端**: 待定(建议 Vue.js 或 React)
- **OCR**: Umi-OCR(本地 HTTP 服务)

### 3.2 部署环境
- **服务器**: 云服务器 1C1G
- **存储**: 长期保存截图和 OCR 结果

### 3.3 性能要求
- 支持 100 位博主的日常数据录入和查询
- 单次截图 OCR 处理时间 < 5 秒
- 收益计算响应时间 < 2 秒

### 3.4 数据备份
- 定期备份 MySQL 数据库
- 截图文件存储(本地或对象存储)

---

## 4. 数据模型设计

### 4.1 博主表 (bloggers)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| name | VARCHAR(100) NOT NULL | 博主名称 |
| sector | VARCHAR(50) | 板块 |
| observe_start_date | DATE | 观察起始日 |
| created_at | DATETIME DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**索引:**
- PRIMARY KEY (id)
- INDEX idx_sector (sector)
- INDEX idx_observe_date (observe_start_date)

### 4.2 基金表 (funds)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| name | VARCHAR(100) NOT NULL | 基金名称 |
| fund_code | VARCHAR(20) | 基金代码(可选) |
| created_at | DATETIME DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引:**
- PRIMARY KEY (id)
- UNIQUE INDEX idx_fund_code (fund_code)
- INDEX idx_name (name)

### 4.3 初始持仓表 (initial_positions)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| blogger_id | INT NOT NULL | 博主ID |
| fund_id | INT NOT NULL | 基金ID |
| shares | DECIMAL(18,4) | 持有份额 |
| cost_amount | DECIMAL(18,2) | 成本金额 |
| record_date | DATE NOT NULL | 记录日期 |
| created_at | DATETIME DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**索引:**
- PRIMARY KEY (id)
- FOREIGN KEY (blogger_id) REFERENCES bloggers(id) ON DELETE CASCADE
- FOREIGN KEY (fund_id) REFERENCES funds(id)
- UNIQUE INDEX idx_blogger_fund_date (blogger_id, fund_id, record_date)

### 4.4 操作记录表 (operations)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| blogger_id | INT NOT NULL | 博主ID |
| fund_id | INT NOT NULL | 基金ID |
| operation_date | DATE NOT NULL | 操作日期 |
| operation_type | ENUM('buy', 'sell') NOT NULL | 买入/卖出 |
| amount | DECIMAL(18,2) | 金额(可为空) |
| shares | DECIMAL(18,4) | 份额(可为空) |
| screenshot_id | INT | 关联截图ID |
| created_at | DATETIME DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引:**
- PRIMARY KEY (id)
- FOREIGN KEY (blogger_id) REFERENCES bloggers(id) ON DELETE CASCADE
- FOREIGN KEY (fund_id) REFERENCES funds(id)
- FOREIGN KEY (screenshot_id) REFERENCES screenshots(id)
- INDEX idx_operation_date (operation_date)
- INDEX idx_blogger_date (blogger_id, operation_date)

### 4.5 截图表 (screenshots)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| file_path | VARCHAR(255) NOT NULL | 文件存储路径 |
| operation_date | DATE NOT NULL | 操作日期(用户选择) |
| ocr_raw_text | TEXT | OCR 原始文本 |
| ocr_parsed_data | JSON | 解析后的结构化数据 |
| status | ENUM('pending', 'confirmed', 'rejected') DEFAULT 'pending' | 处理状态 |
| uploaded_at | DATETIME DEFAULT CURRENT_TIMESTAMP | 上传时间 |

**索引:**
- PRIMARY KEY (id)
- INDEX idx_operation_date (operation_date)
- INDEX idx_status (status)

### 4.6 净值表 (nav_history)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| fund_id | INT NOT NULL | 基金ID |
| nav_date | DATE NOT NULL | 净值日期 |
| nav | DECIMAL(10,4) NOT NULL | 单位净值 |
| updated_at | DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**索引:**
- PRIMARY KEY (id)
- FOREIGN KEY (fund_id) REFERENCES funds(id) ON DELETE CASCADE
- UNIQUE INDEX idx_fund_date (fund_id, nav_date)

### 4.7 持仓快照表 (position_snapshots) - 用于计算历史收益

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT AUTO_INCREMENT | 主键 |
| blogger_id | INT NOT NULL | 博主ID |
| fund_id | INT NOT NULL | 基金ID |
| snapshot_date | DATE NOT NULL | 快照日期 |
| shares | DECIMAL(18,4) NOT NULL | 持有份额 |
| cost_basis | DECIMAL(18,2) NOT NULL | 成本基础 |
| market_value | DECIMAL(18,2) NOT NULL | 市值 |
| created_at | DATETIME DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引:**
- PRIMARY KEY (id)
- FOREIGN KEY (blogger_id) REFERENCES bloggers(id) ON DELETE CASCADE
- FOREIGN KEY (fund_id) REFERENCES funds(id)
- UNIQUE INDEX idx_blogger_fund_date (blogger_id, fund_id, snapshot_date)

---

## 5. 待确认事项

- [x] 净值数据接口选择(天天基金/蛋卷/其他) - 研究中
- [ ] 前端框架选择(Vue/React/其他)
- [ ] 截图存储方案(本地文件系统/对象存储)
- [ ] 1C1G 服务器是否足够(Umi-OCR 会占用一定内存)

---

## 6. 后续步骤

1. ~~确认需求文档是否有遗漏或需要调整~~
2. 确定净值数据接口
3. 确定前端框架
4. 进行技术架构设计
5. 开始开发
