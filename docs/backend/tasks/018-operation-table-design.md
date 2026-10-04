# 任务 018：操作记录表设计

## 预计完成时间

预计完成时间：约 1 小时。

估算依据：本任务不写代码，业务口径和接口契约已经由需求方确认并写进 `docs/api/v1-operations.md`，你只需要把表结构部分整理成一份设计文档，供任务 019 建表时照着写 SQL。

## 任务目标

产出操作记录表 `operations` 的第一版表结构设计文档。

完成后可以：

1. 明确 `operations` 表有哪些字段、什么类型、是否必填。
2. 明确表与 `bloggers`、`funds` 的外键关系。
3. 明确要建哪些索引，以及为什么不建唯一索引。
4. 明确第一版不做哪些金融规则。
5. 任务 019 可以直接照着设计文档写建表 SQL。

## 范围说明

本任务只做表结构设计文档。

不包含：

- 建表 SQL 执行（任务 019）
- Flask 接口开发（任务 020、021、022）
- 接口文档编写（已完成，见下方「设计依据」）
- 净值表、持仓快照、收益计算
- 前端页面、登录权限、OCR

## 前置条件

1. 任务 013 已完成，第一版基础数据模块手工验收通过。
2. 任务 017 已完成，现有接口测试可以通过。
3. `bloggers`、`funds`、`initial_positions` 三张表已经可用。

## 设计依据

接口契约已经写好，**不要自己改，也不要自己另定一套口径**：

```text
docs/api/v1-operations.md
```

这份文档是前后端唯一契约，里面已经确认了：

- 支持哪三种操作类型
- 每个字段的名称、类型、是否必填
- `shares` 和 `amount` 在不同操作类型下的校验规则
- `operation_date` 的合法范围
- 第一版有哪些接口、没有哪些接口

本任务要做的是把其中「数据库表结构」这部分整理成设计文档。  
如果你在整理过程中发现接口文档里有矛盾或说不通的地方，**停下来反馈**，不要自己决定。

## 新概念：操作记录表

操作记录表的英文是 Operation Table。

它用来记录某个博主对某只基金做出的操作，例如买入、卖出、现金分红。

关键理解：操作记录只表示「发生了什么」，不表示「现在还剩多少」。  
当前持仓要用初始持仓加上所有操作记录算出来，这是第 7 天持仓快照任务的工作，不是这张表的工作。

## 已确认的业务口径

本阶段只支持以下操作类型：

| operation_type | 中文含义 | 精简版处理 |
| --- | --- | --- |
| `buy` | 买入 | 记录买入份额和买入金额 |
| `sell` | 卖出 | 记录卖出份额和卖出金额 |
| `dividend_cash` | 现金分红 | 记录分红金额，不改变份额 |

本阶段不支持的规则：

1. 不记录手续费。
2. 不记录税费。
3. 不支持红利再投资。
4. 不支持基金拆分、合并。
5. 不支持自动调仓。
6. 不处理复杂净值复权。
7. 不处理用户权限。

## 执行目录

```bash
cd /mnt/d/people/find_gold
```

注意本任务产出的是项目级文档，执行目录是**项目根目录**，不是 `backend/`。

## 具体步骤

### 步骤 1：确认操作记录的主视角

**必要性：**  
操作记录必须能回答「谁在什么时间对哪只基金做了什么」。因此表必须同时关联博主和基金。

确认关系：

```text
operations.blogger_id -> bloggers.id
operations.fund_id    -> funds.id
```

---

### 步骤 2：确认字段定义

**必要性：**  
字段定义决定建表 SQL 和接口参数。先确认字段，再写 SQL，可以减少返工。

表名：

```text
operations
```

字段定义：

| 字段 | 类型 | 是否必填 | 示例值 | 说明 |
| --- | --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | 是 | `1` | 主键，后端生成 |
| blogger_id | INT | 是 | `1` | 关联 `bloggers.id` |
| fund_id | INT | 是 | `101` | 关联 `funds.id` |
| operation_type | VARCHAR(20) | 是 | `buy` | 操作类型，第一版只允许 `buy`、`sell`、`dividend_cash` |
| operation_date | DATE | 是 | `2026-09-30` | 操作日期，格式 `YYYY-MM-DD` |
| shares | DECIMAL(18, 4) | 是 | `1000.0000` | 份额。数据库层面必填，接口层面 `dividend_cash` 可以不传，由后端补 `0` |
| amount | DECIMAL(18, 2) | 是 | `15600.00` | 金额 |
| remark | VARCHAR(255) | 否 | `第一次买入` | 备注，最多 255 字符 |
| created_at | DATETIME | 是 | `2026-09-30 10:00:00` | 创建时间，数据库自动生成 |
| updated_at | DATETIME | 是 | `2026-09-30 10:00:00` | 更新时间，数据库自动维护 |

注意 `shares` 那一行：数据库里它是 `NOT NULL`，但接口允许调用方在现金分红时不传这个字段。  
这两件事不矛盾——接口层发现是 `dividend_cash` 且没传 `shares` 时，自己填 `0` 再写库。这样数据库里不会出现 `NULL`，查询和汇总时不用到处判空。

---

### 步骤 3：确认操作类型规则

**必要性：**  
不同操作类型需要不同字段校验。如果不提前定义，后续接口容易写出脏数据。

| 操作类型 | shares 规则 | amount 规则 | 说明 |
| --- | --- | --- | --- |
| `buy` | 必填，大于 0 | 必填，大于 0 | 表示买入份额和买入金额 |
| `sell` | 必填，大于 0 | 必填，大于 0 | 表示卖出份额和卖出金额 |
| `dividend_cash` | 可不传；传了必须等于 0 | 必填，大于 0 | 表示现金分红金额 |

这张表和 `docs/api/v1-operations.md` 第 4 节的参数说明必须完全一致。整理时对照一遍。

---

### 步骤 4：确认索引和外键

**必要性：**  
索引影响查询速度，外键保证数据引用关系正确。

建议索引：

| 索引 | 作用 |
| --- | --- |
| `idx_operations_blogger_date (blogger_id, operation_date)` | 支持按博主和日期查询 |
| `idx_operations_fund_date (fund_id, operation_date)` | 支持按基金和日期查询 |
| `idx_operations_type (operation_type)` | 支持按操作类型筛选 |

建议外键：

| 外键 | 指向 | 说明 |
| --- | --- | --- |
| `fk_operations_blogger` | `bloggers(id)` | 博主必须存在 |
| `fk_operations_fund` | `funds(id)` | 基金必须存在 |

外键不加 `ON DELETE CASCADE`。  
这意味着要删除一个还有操作记录的博主时，必须先删掉他的操作记录，否则数据库会拒绝。这件事在任务 022 里处理，本任务只需要把这个结论写进设计文档。

---

### 步骤 5：确认第一版不做唯一约束的原因

**必要性：**  
同一个博主、同一只基金、同一天可能发生多次买入或卖出。因此操作记录表不能简单加「三字段唯一」约束。

结论：

```text
不设置 blogger_id + fund_id + operation_date 唯一索引。
```

原因是这些字段相同的多条记录在业务上是允许的。

代价是：录重了不会被数据库拦住。第一版接受这个代价，通过删除接口（任务 022）手工修正。

---

### 步骤 6：创建设计文档

**必要性：**  
设计结论要保存到项目里，任务 019 建表、第 7 天算持仓快照时都要引用。

新建文件：

```text
docs/backend/design/operations-table-design.md
```

目录如果不存在，先创建：

```bash
mkdir -p docs/backend/design
```

内容可以直接复制以下模板：

```markdown
# 操作记录表设计

## 文档信息

- 对应接口文档：`docs/api/v1-operations.md`
- 对应建表任务：`docs/backend/tasks/019-operation-table-create-and-init.md`

## 表名

operations

## 业务范围

第一版只支持：

- buy：买入
- sell：卖出
- dividend_cash：现金分红

## 字段定义

| 字段 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | 是 | 主键 |
| blogger_id | INT | 是 | 关联博主 |
| fund_id | INT | 是 | 关联基金 |
| operation_type | VARCHAR(20) | 是 | 操作类型 |
| operation_date | DATE | 是 | 操作日期 |
| shares | DECIMAL(18, 4) | 是 | 份额，数据库层面 NOT NULL |
| amount | DECIMAL(18, 2) | 是 | 金额 |
| remark | VARCHAR(255) | 否 | 备注 |
| created_at | DATETIME | 是 | 创建时间 |
| updated_at | DATETIME | 是 | 更新时间 |

## 操作规则

| operation_type | shares 规则 | amount 规则 |
| --- | --- | --- |
| buy | 大于 0 | 大于 0 |
| sell | 大于 0 | 大于 0 |
| dividend_cash | 接口可不传，传了必须等于 0；入库存 0 | 大于 0 |

## 索引

| 索引 | 字段 | 作用 |
| --- | --- | --- |
| idx_operations_blogger_date | blogger_id, operation_date | 按博主和日期查询 |
| idx_operations_fund_date | fund_id, operation_date | 按基金和日期查询 |
| idx_operations_type | operation_type | 按操作类型筛选 |

## 约束

1. blogger_id 必须存在于 bloggers 表，外键 fk_operations_blogger。
2. fund_id 必须存在于 funds 表，外键 fk_operations_fund。
3. operation_type 只允许 buy、sell、dividend_cash。
4. 不设置 blogger_id + fund_id + operation_date 唯一索引，因为同一天可以有多笔操作。
5. 外键不加 ON DELETE CASCADE。删除博主时，应用层必须先删除该博主的操作记录。

## 日期口径

1. operation_date 不能晚于今天。
2. 如果该博主该基金有初始持仓记录，operation_date 不能早于 initial_positions.record_date。
3. 没有初始持仓记录时，不限制下界。

## 第一版不做

- 手续费
- 税费
- 红利再投资
- 基金拆分合并
- 自动调仓
- 超额卖出校验
- 用户权限
```

## 验证方式

执行：

```bash
ls -l docs/backend/design/operations-table-design.md
```

预期文件存在。

再确认关键内容都在：

```bash
grep -c "buy\|sell\|dividend_cash\|blogger_id\|fund_id\|operation_date\|shares\|amount" docs/backend/design/operations-table-design.md
```

预期输出大于 0。

最后人工对照一遍：设计文档里的字段名、类型、校验规则，和 `docs/api/v1-operations.md` 第 3、4 节是否一致。

## 常见坑

### 1. 把「操作记录」当成「当前持仓」

操作记录只表示发生了什么，不直接表示当前还剩多少份额。  
当前持仓会在第 7 天的持仓快照任务里，根据初始持仓和操作记录实时计算，不落库。

### 2. 给操作记录加过强唯一约束

不要设置：

```text
blogger_id + fund_id + operation_date 唯一
```

因为同一天可能发生多笔买入。

### 3. 忘记关联博主和基金

如果表里只存基金代码或博主名称，后面改名称时会导致数据不一致。  
必须使用 `blogger_id` 和 `fund_id`。

### 4. 字段类型使用 FLOAT 或小数位太少

份额和金额都有小数，必须使用：

```sql
DECIMAL(18, 4)
DECIMAL(18, 2)
```

不要使用 `FLOAT` 或 `DOUBLE`。浮点数做金额累加会产生误差，比如 0.1 + 0.2 不等于 0.3，汇总收益时会对不上账。

### 5. 允许没有日期的操作

每个操作必须有 `operation_date`，否则后续算持仓快照时无法判断这笔操作该不该算进去。

### 6. 自己改接口口径

设计文档要服从 `docs/api/v1-operations.md`，不是反过来。  
发现不一致时先反馈，不要自己改接口文档——那份文档前端也在用。

### 7. 把设计文档放到 `backend/docs/`

产出路径是项目级的 `docs/backend/design/`，不是 `backend/docs/`。  
项目文档统一放在根目录的 `docs/` 下面，`backend/` 目录只放代码。

## 完成标准

以下条件全部满足，任务 018 才算完成：

1. `docs/backend/design/operations-table-design.md` 已创建。
2. 设计文档包含完整字段定义（10 个字段）。
3. 设计文档包含三种操作类型及各自的 `shares`、`amount` 规则。
4. 设计文档包含三个索引和两个外键。
5. 设计文档说明了为什么不设唯一索引。
6. 设计文档说明了外键不带 `ON DELETE CASCADE`，以及由此带来的删除顺序要求。
7. 设计文档明确说明第一版不做手续费、税费、红利再投资、超额卖出校验。
8. 字段名和类型与 `docs/api/v1-operations.md` 一致。

## 完成后请反馈

1. 设计文档路径。
2. 字段定义是否与 `docs/api/v1-operations.md` 完全一致。
3. 整理过程中有没有发现接口文档里说不通的地方。
4. 有没有你认为应该调整的字段或索引，以及理由。
5. 遇到的问题和未完成项。
