# 任务 025：创建净值表和唯一约束

## 预计完成时间

预计完成时间：约 1 小时。

估算依据：本任务只把任务 024 的设计转成 SQL 文件，并接入初始化脚本和测试夹具；核心是建表和唯一约束，不写接口。

## 任务目标

创建净值表 `nav_history`。

完成后可以：

1. 项目中有独立的净值 SQL 文件。
2. 初始化脚本可以创建 `nav_history` 表。
3. 同一 `fund_id + nav_date` 只能存在一条净值。
4. 测试夹具会清空 `nav_history`。
5. 重复执行初始化脚本不报错。

## 范围说明

本任务只处理建表和初始化。

不包含：

- 手动录入接口
- CSV 解析
- CSV 导入接口
- 净值查询接口
- 持仓快照
- 收益计算

## 前置条件

1. 任务 024 已完成，净值表设计文档已确认。
2. 任务 019 已完成，`operations` 表已经创建。
3. 任务 023 已完成，公共分页与排序工具已接入。
4. MySQL 用户有建表权限。

## 新概念：唯一索引

唯一索引的英文是 Unique Index。

它保证数据库里不会出现重复的 `fund_id + nav_date`。  
即使两个请求几乎同时提交，数据库层也会阻止第二条重复数据写入。

这个约束是最后防线，不能只靠接口层校验。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建净值 SQL 文件

**必要性：**  
净值表是新的数据库结构，应该有独立 SQL 文件，方便检查和重复初始化。

新建文件：

```text
backend/database/v3-nav-history.sql
```

内容：

```sql
CREATE TABLE IF NOT EXISTS nav_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_id INT NOT NULL,
    nav_date DATE NOT NULL,
    nav DECIMAL(18, 4) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_nav_history_fund
        FOREIGN KEY (fund_id) REFERENCES funds(id),
    UNIQUE INDEX uk_nav_history_fund_date (
        fund_id, nav_date
    ),
    INDEX idx_nav_history_date (nav_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

说明：

- `DECIMAL(18, 4)` 用于保存净值。
- `UNIQUE INDEX uk_nav_history_fund_date` 是关键约束。
- `idx_nav_history_date` 用于按日期查询。

---

### 步骤 2：修改初始化脚本

**必要性：**  
初始化脚本需要知道新 SQL 文件的位置，否则不会创建净值表。

修改文件：

```text
backend/scripts/init_db.py
```

把 `SQL_PATHS` 改为：

```python
SQL_PATHS = [
    BASE_DIR / "database" / "v1-basic-management.sql",
    BASE_DIR / "database" / "v2-operations.sql",
    BASE_DIR / "database" / "v3-nav-history.sql",
]
```

其他逻辑保持不变。

---

### 步骤 3：执行初始化脚本

**必要性：**  
必须实际执行，确认 SQL 没有语法错误，并且表已经创建。

执行：

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=你的数据库密码
export DB_NAME=fund_db

python -m scripts.init_db
```

预期输出中包含 `nav_history`。

---

### 步骤 4：再次执行验证幂等性

**必要性：**  
初始化脚本以后会重复执行。第二次不应该报错。

再次执行：

```bash
python -m scripts.init_db
```

预期不报错。

---

### 步骤 5：检查表结构

**必要性：**  
需要确认字段类型、唯一索引和外键都正确。

进入 MySQL：

```bash
mysql -u root -p fund_db
```

执行：

```sql
SHOW TABLES LIKE 'nav_history';
DESCRIBE nav_history;
SHOW INDEX FROM nav_history;
```

预期能看到：

```text
id
fund_id
nav_date
nav
created_at
updated_at
```

并且能看到 `uk_nav_history_fund_date`。

---

### 步骤 6：验证唯一约束

**必要性：**  
唯一约束是本任务最重要的验收点。

先确认有一个基金，例如 `fund_id = 1`。  
然后在 MySQL 中执行：

```sql
INSERT INTO nav_history (
    fund_id,
    nav_date,
    nav
)
VALUES (
    1,
    '2026-09-30',
    1.2345
);
```

再执行同样的语句：

```sql
INSERT INTO nav_history (
    fund_id,
    nav_date,
    nav
)
VALUES (
    1,
    '2026-09-30',
    2.0000
);
```

预期第二条报重复键错误。

---

### 步骤 7：同步测试数据库夹具

**必要性：**  
`python -m scripts.init_db` 只管开发库 `fund_db`。测试库 `fund_test_db` 的表是 `backend/tests/conftest.py` 里的 `prepare_test_database` 建的，是**另一套代码**。

这一步有两处改动，缺任何一处都会出问题：

1. 不把 `v3-nav-history.sql` 加进 `conftest.py` 的 `SQL_PATHS`，测试库里就没有 `nav_history` 表。
2. `clean_db` 不清空 `nav_history`，上一个测试留下的净值会影响下一个测试。

而且这两处是连在一起的：如果只加了 `TRUNCATE TABLE nav_history` 而没加 `SQL_PATHS`，**每一个测试**都会在夹具阶段报 `Table 'fund_test_db.nav_history' doesn't exist`，整个测试套件直接 error，不只是净值测试挂掉。

修改文件：

```text
backend/tests/conftest.py
```

第一处改动：把 `SQL_PATHS` 改为（任务 019 已经把它改成列表，这里只追加一行）：

```python
SQL_PATHS = [
    BASE_DIR / "database" / "v1-basic-management.sql",
    BASE_DIR / "database" / "v2-operations.sql",
    BASE_DIR / "database" / "v3-nav-history.sql",
]
```

`prepare_test_database` 里遍历 `SQL_PATHS` 的循环不用动，加一行路径就够了。

第二处改动：在 `clean_db` 中把表清空顺序调整为：

```python
cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
cursor.execute("TRUNCATE TABLE nav_history")
cursor.execute("TRUNCATE TABLE operations")
cursor.execute("TRUNCATE TABLE initial_positions")
cursor.execute("TRUNCATE TABLE funds")
cursor.execute("TRUNCATE TABLE bloggers")
cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
```

说明：

- 因为已经关闭外键检查，顺序不是强制要求。
- 但把 `nav_history` 放在最前面，可以提醒后续开发者：有新的子表时也要加进来。

改完后用这条命令自查：

```bash
grep -n "v3-nav-history\|TRUNCATE TABLE nav_history" tests/conftest.py
```

预期能看到两行：一行在 `SQL_PATHS` 里，一行在 `clean_db` 里。只看到一行就是漏改。

**不要动** `assert_test_database()` 和 `clean_db` 里的 `SELECT DATABASE()` 那两处守卫。它们保证测试只会清空 `fund_test_db`，一旦删掉，某次配置写错就可能清空开发库 `fund_db`。

---

### 步骤 8：运行全部测试

**必要性：**  
确认修改测试夹具后，现有测试仍然通过。

执行：

```bash
pytest -q
```

预期全部通过。

## 验证方式

### 1. 初始化脚本

```bash
python -m scripts.init_db
```

预期不报错，输出包含 `nav_history`。

### 2. 表结构检查

```sql
SHOW TABLES LIKE 'nav_history';
DESCRIBE nav_history;
SHOW INDEX FROM nav_history;
```

预期表存在，字段完整，唯一索引存在。

### 3. 唯一约束测试

重复插入同一 `fund_id + nav_date`，预期第二条失败。

### 4. 测试夹具同步

```bash
grep -n "v3-nav-history\|TRUNCATE TABLE nav_history" tests/conftest.py
```

预期两行都在。

### 5. 自动化测试

```bash
pytest -q
```

预期全部通过。如果报 `Table 'fund_test_db.nav_history' doesn't exist`，说明步骤 7 的第一处改动没做。

## 常见坑

### 1. 忘记加唯一索引

如果只建了普通索引，重复数据仍然可以写入。  
必须使用：

```sql
UNIQUE INDEX uk_nav_history_fund_date (fund_id, nav_date)
```

### 2. 忘记把 SQL 文件加入 `SQL_PATHS`

如果 SQL 文件存在，但 `init_db.py` 没有引用它，表不会被创建。  
执行 `SHOW TABLES LIKE 'nav_history';` 可以发现。

### 3. 只改了开发库，忘了测试库

这是本任务最容易漏的一步，和任务 019 的坑 6 是同一个。

`init_db.py` 和 `tests/conftest.py` 是两套建表代码。只改 `init_db.py`，测试库 `fund_test_db` 里就没有 `nav_history` 表。

更坑的是：如果 `clean_db` 里加了 `TRUNCATE TABLE nav_history`，而 `SQL_PATHS` 没加，那么**每一个测试**都会在夹具阶段报错：

```text
Table 'fund_test_db.nav_history' doesn't exist
```

不是只有净值测试挂，是整个 `pytest -q` 全 error。

检查命令：

```bash
grep -n "v3-nav-history\|TRUNCATE TABLE nav_history" tests/conftest.py
```

预期能看到两行。

### 4. 改 `conftest.py` 时顺手删掉了守卫

`assert_test_database()` 和 `clean_db` 里的 `SELECT DATABASE()` 检查必须保留。  
它们是防止测试清空开发数据库 `fund_db` 的最后一道防线。

检查命令：

```bash
grep -n "fund_test_db\|assert_test_database\|SELECT DATABASE" tests/conftest.py
```

### 5. 金额或净值使用 FLOAT

不要使用：

```sql
FLOAT
DOUBLE
```

净值必须使用：

```sql
DECIMAL(18, 4)
```

### 6. 净值日期允许为空

`nav_date` 必须是 `NOT NULL`。  
没有日期的净值无法参与持仓快照和收益计算。

### 7. 忘记外键
`fund_id` 必须有外键：

```sql
FOREIGN KEY (fund_id) REFERENCES funds(id)
```

否则可能写入不存在的基金。

## 完成标准

以下条件全部满足，任务 025 才算完成：

1. `backend/database/v3-nav-history.sql` 已创建。
2. `backend/scripts/init_db.py` 的 `SQL_PATHS` 已包含 `v3-nav-history.sql`。
3. `nav_history` 表已创建。
4. `fund_id + nav_date` 唯一索引存在。
5. `fund_id` 外键存在。
6. 重复执行初始化脚本不报错。
7. `backend/tests/conftest.py` 的 `SQL_PATHS` 已包含 `v3-nav-history.sql`。
8. `backend/tests/conftest.py` 的 `clean_db` 里包含 `TRUNCATE TABLE nav_history`，且在 `operations` 之前。
9. `backend/tests/conftest.py` 里的两处数据库守卫仍然存在。
10. `pytest -q` 全部通过，没有 failed 也没有 error。

## 完成后请反馈

1. 新增和修改的文件列表。
2. `python -m scripts.init_db` 的输出。
3. `DESCRIBE nav_history;` 和 `SHOW INDEX FROM nav_history;` 的输出。
4. 唯一约束测试结果。
5. `pytest -q` 的完整输出。
6. 遇到的问题和未完成项。
