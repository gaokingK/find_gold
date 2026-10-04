# 任务 019：创建并初始化操作记录表

## 预计完成时间

预计完成时间：约 1.5 小时。

估算依据：本任务需要新建操作记录 SQL 文件、改造初始化脚本支持多个 SQL 文件、执行建表并验证外键和索引，最后同步测试夹具；都是 SQL 和脚本改动，不涉及 Flask 接口。

## 任务目标

把任务 018 确认的操作记录表设计落地到 MySQL。

完成后可以：

1. 项目中有独立的操作记录 SQL 文件。
2. 初始化脚本可以同时创建基础表和操作记录表。
3. 开发数据库 `fund_db` 中存在 `operations` 表。
4. `operations` 表包含外键和索引。
5. 重复执行初始化脚本不会报错。
6. 测试数据库 `fund_test_db` 也会自动创建 `operations` 表，并且每个测试前会被清空。

## 范围说明

本任务只处理建表和初始化。

不包含：

- 新增操作记录接口
- 查询操作记录接口
- 修改接口
- 删除接口
- 持仓快照
- 收益计算

## 前置条件

1. 任务 018 已完成，`docs/backend/design/operations-table-design.md` 已产出。
2. 任务 007 已完成，`backend/database/v1-basic-management.sql` 可用。
3. 任务 006 已完成，`scripts/check_db.py` 可以连接 MySQL。
4. 任务 015 已完成，`backend/tests/conftest.py` 里有测试数据库夹具。
5. MySQL 用户有建表权限。

## 新概念：增量 SQL 文件

增量 SQL 文件是在已有数据库结构基础上追加的新表 SQL 文件。  
本任务新建 `v2-operations.sql`，不去修改已经稳定的 `v1-basic-management.sql`。

这样做的好处是：

1. 第一版基础表结构保持稳定。
2. 操作记录表可以单独检查。
3. 后续新增净值表时也可以继续拆分文件。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建操作记录 SQL 文件

**必要性：**  
SQL 建表语句应该保存在项目里，方便新环境初始化和后续检查表结构。

新建文件：

```text
backend/database/v2-operations.sql
```

内容：

```sql
CREATE TABLE IF NOT EXISTS operations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    blogger_id INT NOT NULL,
    fund_id INT NOT NULL,
    operation_type VARCHAR(20) NOT NULL,
    operation_date DATE NOT NULL,
    shares DECIMAL(18, 4) NOT NULL DEFAULT 0,
    amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
    remark VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_operations_blogger
        FOREIGN KEY (blogger_id) REFERENCES bloggers(id),
    CONSTRAINT fk_operations_fund
        FOREIGN KEY (fund_id) REFERENCES funds(id),
    INDEX idx_operations_blogger_date (
        blogger_id, operation_date
    ),
    INDEX idx_operations_fund_date (
        fund_id, operation_date
    ),
    INDEX idx_operations_type (operation_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

说明：

- `CREATE TABLE IF NOT EXISTS` 表示表不存在时才创建，重复执行脚本更安全。
- `FK` 是 Foreign Key（外键），用来保证 `blogger_id` 和 `fund_id` 必须存在。
- `DECIMAL` 适合保存金额和份额，避免浮点数误差。
- 两个外键都**不带** `ON DELETE CASCADE`。这是有意的：删除博主时必须由应用层先删掉他的操作记录，再删博主。这件事在任务 022 里做。

---

### 步骤 2：修改初始化脚本

**必要性：**  
以后项目会有多个 SQL 文件，初始化脚本应该能依次执行，而不是只处理一个文件。

修改文件：

```text
backend/scripts/init_db.py
```

把原来只读取一个 SQL 文件的方式改为读取多个 SQL 文件。

把文件内容替换为：

```python
from pathlib import Path

from pymysql import connect

from app.config import DB_CONFIG


BASE_DIR = Path(__file__).resolve().parent.parent
SQL_PATHS = [
    BASE_DIR / "database" / "v1-basic-management.sql",
    BASE_DIR / "database" / "v2-operations.sql",
]


def create_database():
    server_config = DB_CONFIG.copy()
    server_config.pop("database")

    conn = connect(**server_config)

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE DATABASE IF NOT EXISTS fund_db
                CHARACTER SET utf8mb4
                COLLATE utf8mb4_unicode_ci
                """
            )
        conn.commit()
    finally:
        conn.close()


def create_tables():
    conn = connect(**DB_CONFIG)

    try:
        with conn.cursor() as cursor:
            for sql_path in SQL_PATHS:
                if not sql_path.exists():
                    raise FileNotFoundError(f"SQL file not found: {sql_path}")

                sql = sql_path.read_text(encoding="utf-8")
                statements = [
                    item.strip()
                    for item in sql.split(";")
                    if item.strip()
                ]

                for statement in statements:
                    cursor.execute(statement)

            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()

        conn.commit()
        print("Created tables:")
        for row in tables:
            print(dict(row))
    finally:
        conn.close()


def main():
    create_database()
    create_tables()


if __name__ == "__main__":
    main()
```

说明：

- `FileNotFoundError` 表示找不到 SQL 文件时主动报错，避免静默跳过。
- `sql.split(";")` 是当前项目的简单处理方式，适合现在这种没有存储过程的 SQL 文件。

---

### 步骤 3：执行初始化脚本

**必要性：**  
必须实际执行，确认 SQL 文件没有语法错误，并且数据库里真的创建了表。

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

预期输出中包含 `operations`。

---

### 步骤 4：再次执行验证幂等性

**必要性：**  
初始化脚本以后会重复执行。如果第二次报错，说明建表语句或脚本写得不安全。

再次执行：

```bash
python -m scripts.init_db
```

预期不报错。

---

### 步骤 5：检查表结构

**必要性：**  
需要确认字段类型、外键和索引都正确。

执行：

```bash
mysql -u root -p fund_db
```

进入 MySQL 后执行：

```sql
SHOW TABLES;
DESCRIBE operations;
SHOW INDEX FROM operations;
```

预期能看到：

```text
id
blogger_id
fund_id
operation_type
operation_date
shares
amount
remark
created_at
updated_at
```

---

### 步骤 6：验证外键约束

**必要性：**  
外键可以防止操作记录指向不存在的博主或基金。

在 MySQL 中执行：

```sql
INSERT INTO operations (
    blogger_id,
    fund_id,
    operation_type,
    operation_date,
    shares,
    amount,
    remark
)
VALUES (
    999999,
    999999,
    'buy',
    '2026-09-30',
    1.0000,
    1.00,
    '外键测试'
);
```

预期报外键错误，类似：

```text
Cannot add or update a child row: a foreign key constraint fails
```

看到这个报错说明外键生效了，这是**预期结果**，不是失败。

---

### 步骤 7：同步测试数据库夹具

**必要性：**  
`backend/tests/conftest.py` 只知道 `v1-basic-management.sql`，也只清空三张基础表。  
如果不同步，会出现两个问题：

1. 测试数据库 `fund_test_db` 里没有 `operations` 表，任务 020 的接口测试一跑就报 `Table 'fund_test_db.operations' doesn't exist`。
2. 即使表建好了，`clean_db` 不清空它，测试之间会互相看到上一个测试留下的操作记录。

修改文件：

```text
backend/tests/conftest.py
```

第一处改动：把单个 SQL 路径改成列表。

原来是：

```python
SQL_PATH = BASE_DIR / "database" / "v1-basic-management.sql"
```

改成：

```python
SQL_PATHS = [
    BASE_DIR / "database" / "v1-basic-management.sql",
    BASE_DIR / "database" / "v2-operations.sql",
]
```

第二处改动：`prepare_test_database` 里执行 SQL 的部分，原来只读一个文件：

```python
        sql = SQL_PATH.read_text(encoding="utf-8")
        statements = [item.strip() for item in sql.split(";") if item.strip()]

        with conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
```

改成依次读多个文件：

```python
        with conn.cursor() as cursor:
            for sql_path in SQL_PATHS:
                sql = sql_path.read_text(encoding="utf-8")
                statements = [
                    item.strip()
                    for item in sql.split(";")
                    if item.strip()
                ]

                for statement in statements:
                    cursor.execute(statement)
```

第三处改动：`clean_db` 里的清空语句，在最前面加上 `operations`。

原来是：

```python
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("TRUNCATE TABLE initial_positions")
            cursor.execute("TRUNCATE TABLE funds")
            cursor.execute("TRUNCATE TABLE bloggers")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
```

改成：

```python
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("TRUNCATE TABLE operations")
            cursor.execute("TRUNCATE TABLE initial_positions")
            cursor.execute("TRUNCATE TABLE funds")
            cursor.execute("TRUNCATE TABLE bloggers")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
```

注意顺序：先清子表（`operations`、`initial_positions`），再清父表（`funds`、`bloggers`）。  
虽然前面已经关了外键检查，按这个顺序写仍然是好习惯——以后万一漏了 `SET FOREIGN_KEY_CHECKS = 0`，也不会立刻炸。

**不要动** `assert_test_database()` 和 `SELECT DATABASE()` 那两处守卫。它们保证测试只会清空 `fund_test_db`，一旦删掉，某次配置写错就可能清空开发库 `fund_db`。

---

### 步骤 8：运行已有测试确认没有破坏

**必要性：**  
刚才改了 `conftest.py`，这是所有测试共用的文件。必须确认前面 26 个测试还能全过，再往下做接口任务。

执行：

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=你的数据库密码

pytest -q
```

预期：和任务 017 完成时一样，全部通过，没有 failed 也没有 error。

如果报 `Table 'fund_test_db.operations' doesn't exist`，说明步骤 7 的第一处或第二处改动没生效。

## 验证方式

执行：

```bash
python -m scripts.check_db
python -m scripts.init_db
```

再进入 MySQL 检查：

```sql
SHOW TABLES LIKE 'operations';
DESCRIBE operations;
```

预期 `operations` 表存在，并且字段完整。

再确认测试库也建好了：

```bash
mysql -u root -p -e "SHOW TABLES FROM fund_test_db LIKE 'operations';"
```

预期能看到 `operations`。如果为空，先跑一次 `pytest -q`，`prepare_test_database` 会创建它。

最后确认测试仍然全部通过：

```bash
pytest -q
```

## 常见坑

### 1. SQL 文件路径错误

初始化脚本根据 `BASE_DIR` 查找：

```text
backend/database/v2-operations.sql
```

如果报：

```text
FileNotFoundError: SQL file not found
```

检查文件是否创建到了其他目录。

### 2. 外键创建失败

如果 `bloggers` 或 `funds` 表不存在，外键创建会失败。

先确认基础表存在：

```sql
SHOW TABLES;
```

必要时先执行基础表初始化。

### 3. MySQL 用户没有建表权限

如果报权限错误，说明当前用户无法创建表。  
需要使用有权限的账号，或者让 DBA 授权。

### 4. 重复执行报“表已存在”

检查 SQL 文件是否写成了：

```sql
CREATE TABLE operations
```

正确写法是：

```sql
CREATE TABLE IF NOT EXISTS operations
```

### 5. 金额和份额使用 FLOAT

不要使用：

```sql
FLOAT
DOUBLE
```

金额和份额应使用 `DECIMAL`，避免精度问题。

### 6. 只改了开发库，忘了测试库

这是本任务最容易漏的一步。

`python -m scripts.init_db` 只管开发库 `fund_db`。测试库 `fund_test_db` 的表是 `tests/conftest.py` 里的 `prepare_test_database` 建的，是另一套代码。  
只做步骤 1–6 就交差，任务 020 一写测试就会报表不存在，而且很难联想到是这里漏了。

检查命令：

```bash
grep -n "v2-operations\|TRUNCATE TABLE operations" tests/conftest.py
```

预期能看到两行：一行在 `SQL_PATHS` 里，一行在 `clean_db` 里。

### 7. 改 `conftest.py` 时顺手删掉了守卫

`assert_test_database()` 和 `clean_db` 里的 `SELECT DATABASE()` 检查必须保留。  
它们是防止测试清空开发数据库 `fund_db` 的最后一道防线。

检查命令：

```bash
grep -n "fund_test_db\|assert_test_database\|SELECT DATABASE" tests/conftest.py
```

### 8. 在测试库上跑外键测试语句

步骤 6 的 `INSERT` 要在开发库 `fund_db` 上执行。  
不要连到 `fund_test_db` 去插数据，那会让下一次测试看到脏数据（虽然 `clean_db` 会清掉，但容易让人误判）。

## 完成标准

以下条件全部满足，任务 019 才算完成：

1. `backend/database/v2-operations.sql` 存在。
2. `backend/scripts/init_db.py` 能依次执行多个 SQL 文件。
3. 开发库 `fund_db` 中 `operations` 表已创建。
4. `blogger_id` 和 `fund_id` 外键存在，且都不带 `ON DELETE CASCADE`。
5. 三个索引存在。
6. 重复执行初始化脚本不报错。
7. 向不存在的博主或基金插入操作记录会失败。
8. `tests/conftest.py` 的 `SQL_PATHS` 里包含 `v2-operations.sql`。
9. `tests/conftest.py` 的 `clean_db` 里包含 `TRUNCATE TABLE operations`，且在 `initial_positions` 之前。
10. `tests/conftest.py` 里的两处数据库守卫仍然存在。
11. `pytest -q` 全部通过，没有 failed 也没有 error。

## 完成后请反馈

1. 新增和修改的文件列表。
2. `python -m scripts.init_db` 的输出。
3. `DESCRIBE operations;` 的输出。
4. `SHOW INDEX FROM operations;` 的输出。
5. 外键失败测试的结果。
6. `grep -n "v2-operations\|TRUNCATE TABLE operations" tests/conftest.py` 的输出。
7. `pytest -q` 的完整输出。
8. 遇到的问题和未完成项。
