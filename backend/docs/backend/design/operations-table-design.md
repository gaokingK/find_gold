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