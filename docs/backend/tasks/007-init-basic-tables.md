# 任务 007：初始化第一版基础数据表

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务引入 SQL 建表、主键、唯一索引、外键和初始化脚本；需要创建三个基础表并验证。

## 任务目标

创建第一版需要的三个基础数据表：

```text
bloggers
funds
initial_positions
```

完成后，执行：

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
python -m scripts.init_db
```

脚本应成功执行，并显示这三个表已经存在。

## 范围说明

本任务只创建第一版基础数据模块需要的表。

不包含：

- 截图表
- 操作记录表
- 净值表
- 收益快照表
- ORM 模型
- 数据库迁移工具
- 触发器、存储过程、视图

## 前置条件

任务 006 已经完成，并且：

```bash
python -m scripts.check_db
```

能成功连接 MySQL。

## 新概念：DDL

DDL 的英文是 Data Definition Language，中文叫数据定义语言。

用来定义数据库结构，例如：

- 创建数据库
- 创建表
- 创建索引

本任务使用的主要语句是：

```sql
CREATE TABLE IF NOT EXISTS ...
```

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建 SQL 文件

**必要性：**  
建表语句应该保存在项目里，方便新人重新初始化数据库，也方便以后检查表结构。

新建文件：

```text
backend/database/v1-basic-management.sql
```

内容：

```sql
CREATE TABLE IF NOT EXISTS bloggers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    sector VARCHAR(50) NOT NULL,
    observe_start_date DATE NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_bloggers_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS funds (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    fund_code VARCHAR(20) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_funds_code (fund_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS initial_positions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    blogger_id INT NOT NULL,
    fund_id INT NOT NULL,
    shares DECIMAL(18, 4) NOT NULL DEFAULT 0,
    cost_amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
    record_date DATE NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_initial_positions_blogger
        FOREIGN KEY (blogger_id) REFERENCES bloggers(id),
    CONSTRAINT fk_initial_positions_fund
        FOREIGN KEY (fund_id) REFERENCES funds(id),
    UNIQUE INDEX idx_initial_positions_unique (
        blogger_id, fund_id, record_date
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

字段说明：

| 表 | 字段 | 说明 |
| --- | --- | --- |
| `bloggers` | `name` | 博主名称，唯一 |
| `bloggers` | `sector` | 所属板块 |
| `bloggers` | `observe_start_date` | 观察开始日 |
| `funds` | `fund_code` | 基金代码，唯一 |
| `initial_positions` | `blogger_id` | 关联博主 |
| `initial_positions` | `fund_id` | 关联基金 |
| `initial_positions` | `shares` | 持有份额 |
| `initial_positions` | `cost_amount` | 成本金额 |
| `initial_positions` | `record_date` | 记录日期 |

---

### 步骤 2：创建初始化脚本

**必要性：**  
有了初始化脚本，新环境可以快速创建同样的表结构，避免手动执行多条 SQL 导致遗漏。

新建文件：

```text
backend/scripts/init_db.py
```

内容：

```python
from pathlib import Path

from pymysql import connect

from app.config import DB_CONFIG


BASE_DIR = Path(__file__).resolve().parent.parent
SQL_PATH = BASE_DIR / "database" / "v1-basic-management.sql"


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
    sql = SQL_PATH.read_text(encoding="utf-8")
    statements = [item.strip() for item in sql.split(";") if item.strip()]

    conn = connect(**DB_CONFIG)

    try:
        with conn.cursor() as cursor:
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

---

### 步骤 3：执行初始化脚本

**必要性：**  
这一步验证 SQL 文件和脚本是否真的可用。

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

---

### 步骤 4：再次执行验证幂等性

**必要性：**  
SQL 使用了 `CREATE TABLE IF NOT EXISTS`，第二次执行不应该报错。这可以保证脚本重复执行时更安全。

再次执行：

```bash
python -m scripts.init_db
```

预期不会报错。

## 验证方式

脚本输出中应包含：

```text
bloggers
funds
initial_positions
```

也可以用下面的命令查看表结构：

```bash
mysql -u root -p fund_db
```

进入 MySQL 后执行：

```sql
SHOW TABLES;
DESC bloggers;
DESC funds;
DESC initial_positions;
```

## 常见坑

### 1. SQL 文件路径错误

初始化脚本是在 `backend` 目录执行的，不要在项目根目录执行。

正确命令：

```bash
cd /mnt/d/people/find_gold/backend
python -m scripts.init_db
```

---

### 2. 外键创建失败

如果之前手动创建过结构不一致的表，可能导致外键失败。

不要随便删除数据。先反馈错误信息，再决定处理方式。

---

### 3. 数据库账号权限不足

如果报：

```text
Access denied
```

说明当前 MySQL 用户可能没有创建数据库或表的权限。

先用管理员账号确认：

```bash
mysql -u root -p
```

---

### 4. 环境变量没有设置

每次新开终端都要重新设置：

```bash
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=你的数据库密码
export DB_NAME=fund_db
```

## 完成标准

1. `database/v1-basic-management.sql` 存在。
2. `scripts/init_db.py` 存在。
3. `python -m scripts.init_db` 能成功执行两次。
4. 数据库中存在 `bloggers`、`funds`、`initial_positions` 三个表。
5. 三个表字段与本文档一致。

## 完成后请反馈

请把下面命令的输出发给后端协调人：

```bash
python -m scripts.init_db
cat database/v1-basic-management.sql
```

任务 007 验收通过后，再进入任务 008：实现博主列表查询接口。
