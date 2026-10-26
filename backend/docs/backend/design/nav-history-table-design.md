# 净值表设计

## 表名

nav_history

## 业务范围

第一版只保存某只基金某一天的单位净值。

## 字段定义

| 字段 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | 是 | 主键 |
| fund_id | INT | 是 | 关联基金 |
| nav_date | DATE | 是 | 净值日期 |
| nav | DECIMAL(18, 4) | 是 | 单位净值，必须大于 0 |
| created_at | DATETIME | 是 | 创建时间 |
| updated_at | DATETIME | 是 | 更新时间 |

## 唯一性

同一 fund_id + nav_date 只允许一条净值。

唯一索引：

- uk_nav_history_fund_date (fund_id, nav_date)

## 重复提交行为

同一 fund_id + nav_date 再次提交时，更新已有净值。

## 索引

| 索引 | 字段 | 作用 |
| --- | --- | --- |
| uk_nav_history_fund_date | fund_id, nav_date | 唯一约束和查询 |
| idx_nav_history_date | nav_date | 按日期查询 |

## 外键

| 外键 | 指向 | 说明 |
| --- | --- | --- |
| fk_nav_history_fund | funds(id) | 基金必须存在 |

## CSV 导入口径

1. CSV 列名：fund_code, nav_date, nav
2. 后端根据 fund_code 查找 fund_id。
3. 全部成功才入库。
4. 有一行错误就不写库。
5. CSV 内部不允许重复的 fund_code + nav_date。
6. 同一天已有净值时，导入会更新旧值。

## 第一版不做

- 自动净值同步
- 分红净值
- 累计净值
- 复权净值
- 净值编辑接口
- 净值删除接口
- 最大回撤
- 年化收益