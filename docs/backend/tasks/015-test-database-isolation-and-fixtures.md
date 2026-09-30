# 任务 015：测试数据库隔离与通用测试夹具

## 预计完成时间

预计完成时间：约 2.5 小时。

估算依据：本任务需要改造测试夹具，让接口测试使用独立的 `fund_test_db`，并在每个测试前清空三张表；需要处理数据库创建、表初始化、外键约束和「防误删开发库」的守卫逻辑，是第 4 天最容易出问题的一个任务，所以留出额外时间。

## 任务目标

让接口测试不污染开发数据库。

完成后可以：

1. 测试代码使用独立的 `fund_test_db`。
2. 测试运行前自动创建测试数据库和基础表。
3. 每个测试开始前自动清空 `bloggers`、`funds`、`initial_positions`。
4. 一旦配置指向开发数据库 `fund_db`，测试会在清空数据之前直接中止。
5. `pytest -q` 至少有 3 个测试通过。

## 范围说明

本任务只处理测试数据库隔离和通用测试夹具。

不包含：

- 博主模块测试
- 基金模块测试
- 初始持仓模块测试
- 生产数据库配置
- 数据库迁移

## 前置条件

1. 任务 014 已完成，`pytest -q` 能运行健康检查测试。
2. `backend/pytest.ini` 存在，`pytest -q` 不再报 `ModuleNotFoundError`。
3. `backend/database/v1-basic-management.sql` 存在。
4. MySQL 用户有创建数据库的权限。

## 新概念：测试数据库隔离、autouse fixture

### 测试数据库隔离

测试数据库隔离是指自动化测试使用单独的数据库，例如 `fund_test_db`。  
这样可以避免测试数据污染开发数据库 `fund_db`。

### autouse fixture

autouse fixture 是 pytest 中一种自动生效的夹具。  
不需要在每个测试函数参数里手动传入，它会自动在每个测试前执行。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=你的数据库密码
```

说明：本任务开始真正连接 MySQL，必须先导出上面几个环境变量，否则密码是空字符串，会报 `Access denied for user`。  
`DB_NAME` 不要导出，`tests/conftest.py` 会自己把它设置成 `fund_test_db`。  
数据库密码只通过环境变量传入，不要写进任何会提交到 Git 的文件。

## 具体步骤

### 步骤 1：修改 `tests/conftest.py`

**必要性：**  
如果不隔离数据库，测试会直接写入开发库。以后运行测试可能删掉或清空你正在开发的数据。

修改文件：

```text
backend/tests/conftest.py
```

把内容替换为：

```python
import os

os.environ["DB_NAME"] = "fund_test_db"

from pathlib import Path

import pytest
from pymysql import connect

from app import create_app
from app.config import DB_CONFIG


BASE_DIR = Path(__file__).resolve().parent.parent
SQL_PATH = BASE_DIR / "database" / "v1-basic-management.sql"
TEST_DB_NAME = "fund_test_db"


def assert_test_database():
    current = DB_CONFIG.get("database")

    if current != TEST_DB_NAME:
        raise RuntimeError(
            f"测试只允许连接 {TEST_DB_NAME}，当前配置是 {current}，已中止测试"
        )


def server_connection():
    config = DB_CONFIG.copy()
    config.pop("database")
    return connect(**config)


def get_test_connection():
    assert_test_database()

    config = DB_CONFIG.copy()
    config["database"] = TEST_DB_NAME
    return connect(**config)


@pytest.fixture(scope="session")
def prepare_test_database():
    assert_test_database()

    conn = server_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE DATABASE IF NOT EXISTS fund_test_db
                CHARACTER SET utf8mb4
                COLLATE utf8mb4_unicode_ci
                """
            )
        conn.commit()
    finally:
        conn.close()

    conn = get_test_connection()

    try:
        sql = SQL_PATH.read_text(encoding="utf-8")
        statements = [item.strip() for item in sql.split(";") if item.strip()]

        with conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)

        conn.commit()
    finally:
        conn.close()


@pytest.fixture(scope="session")
def app(prepare_test_database):
    return create_app()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(prepare_test_database):
    conn = get_test_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS current_db")
            current_db = cursor.fetchone()["current_db"]

            if current_db != TEST_DB_NAME:
                raise RuntimeError(
                    f"拒绝清空数据库 {current_db}，只允许清空 {TEST_DB_NAME}"
                )

            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("TRUNCATE TABLE initial_positions")
            cursor.execute("TRUNCATE TABLE funds")
            cursor.execute("TRUNCATE TABLE bloggers")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        conn.commit()
    finally:
        conn.close()

    yield
```

说明：

- `assert_test_database()` 是本任务最重要的一个函数。它在**任何连接、任何清空动作之前**检查数据库名，只要不是 `fund_test_db` 就直接抛异常中止测试。
- `RuntimeError` 是 Python 内置异常，这里用它表示「环境不对，不能继续」。抛异常会让 pytest 立即报错退出，而不是继续往下清数据。
- `server_connection()` 不指定数据库，用来创建测试数据库。
- `get_test_connection()` 明确连接 `fund_test_db`，并且连接前先做一次检查。注意函数名不要写成 `test_connection`，原因见「常见坑」第 6 条。
- `clean_db` 里还用 `SELECT DATABASE()` 向 MySQL 再确认一次当前库名。这是双重保险：第一道检查看的是 Python 里的配置，第二道检查看的是数据库实际连上了哪个库。
- `prepare_test_database` 使用 `scope="session"`，表示整个测试会话只准备一次数据库。
- `clean_db` 使用 `autouse=True`，每个测试开始前都会清空表。
- `SET FOREIGN_KEY_CHECKS = 0` 只用于测试库，用来允许清空有外键关联的表。

**为什么守卫必须写在 `clean_db` 里面：**  
`clean_db` 是 `autouse=True`，它在每个测试函数之前运行，比任何测试代码都早。  
如果只在测试函数里写 `assert DB_CONFIG["database"] == "fund_test_db"`，那么等这个断言运行时，`clean_db` 已经把表清空了——数据已经没了，断言才报红，保护没有意义。  
所以检查必须放在执行 `TRUNCATE` 之前。

---

### 步骤 2：新增隔离检查测试

**必要性：**  
需要有一个测试确认当前测试代码确实使用的是测试数据库，而不是开发数据库。

注意：这两个测试是「事后确认」，真正拦住误删的是 `conftest.py` 里的 `assert_test_database()`。  
两者都要有：守卫负责阻止事故，测试负责让配置错误在测试报告里显眼。

新建文件：

```text
backend/tests/test_database.py
```

内容：

```python
from app.config import DB_CONFIG


def test_database_name_is_test_database():
    assert DB_CONFIG["database"] == "fund_test_db"


def test_clean_db_fixture_can_run(client):
    response = client.get("/health")

    assert response.status_code == 200
```

---

### 步骤 3：验证守卫真的会拦下开发数据库

**必要性：**  
守卫代码写了不等于有用。必须实际构造一次「数据库名不对」的情况，确认它会抛异常中止，而不是默默继续清表。

这一步不会连接数据库，也不会清空任何数据。

执行：

```bash
python -c "
import os, sys
os.environ['DB_NAME'] = 'fund_db'
sys.path.insert(0, 'tests')
import conftest
conftest.assert_test_database()
"
```

预期报错，并且错误信息里能看到 `fund_db`：

```text
RuntimeError: 测试只允许连接 fund_test_db，当前配置是 fund_db，已中止测试
```

如果这条命令没有报错，说明守卫没生效，必须回到步骤 1 检查 `assert_test_database()` 是否写对、是否在 `get_test_connection()` 和 `clean_db` 里都调用了。

---

### 步骤 4：运行测试

**必要性：**  
需要确认测试数据库创建、表初始化、清空逻辑都能正常工作。

执行：

```bash
pytest -q
```

预期输出类似：

```text
3 passed in 0.50s
```

## 验证方式

执行：

```bash
pytest -q
```

如果看到 `3 passed`，说明测试数据库隔离已经生效。

再确认守卫有效：

```bash
python -c "
import os, sys
os.environ['DB_NAME'] = 'fund_db'
sys.path.insert(0, 'tests')
import conftest
conftest.assert_test_database()
"
```

预期抛出 `RuntimeError`。

也可以登录 MySQL 检查：

```bash
mysql -u root -p -e "SHOW DATABASES LIKE 'fund_test_db';"
```

预期能看到 `fund_test_db`。

最后确认开发库数据还在：

```bash
mysql -u root -p -e "SELECT COUNT(*) FROM fund_db.bloggers;"
```

跑完测试后，这个数字应该和跑测试之前一样。

## 常见坑

### 1. 环境变量设置太晚

如果先写了：

```python
from app.config import DB_CONFIG
```

再写：

```python
os.environ["DB_NAME"] = "fund_test_db"
```

那么 `DB_CONFIG` 可能已经使用了旧的数据库名。

正确顺序是先设置环境变量，再导入 `DB_CONFIG`。

### 2. 连不上数据库

如果报：

```text
Access denied for user
```

按顺序排查：

原因一：没有导出环境变量，`DB_PASSWORD` 是空字符串。回到「执行目录」一节，重新 `export`。

```bash
echo $DB_USER
echo ${DB_PASSWORD:+密码已设置}
```

第二条命令应该输出「密码已设置」。如果什么都没输出，说明密码没导出。

原因二：当前 MySQL 用户没有创建数据库的权限。可以先用管理员账号手动创建：

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS fund_test_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 3. SQL 文件路径错误

`SQL_PATH` 是根据 `tests/conftest.py` 所在位置向上找一级，再进入 `database` 目录。

确认文件存在：

```bash
ls -l database/v1-basic-management.sql
```

### 4. 外键约束导致清空失败

如果报：

```text
Cannot truncate a table referenced in a foreign key constraint
```

说明清空表时没有先执行：

```sql
SET FOREIGN_KEY_CHECKS = 0;
```

### 5. 误清空开发数据库

这是本任务最严重的风险。`clean_db` 会执行 `TRUNCATE`，一旦连错库，开发数据会被清空。

三条防线必须都在：

1. `conftest.py` 顶部先设置 `os.environ["DB_NAME"] = "fund_test_db"`，再导入 `DB_CONFIG`。
2. `get_test_connection()` 里调用 `assert_test_database()`。
3. `clean_db` 里用 `SELECT DATABASE()` 再确认一次，不是 `fund_test_db` 就抛 `RuntimeError`。

检查命令：

```bash
grep -n "fund_test_db\|assert_test_database\|SELECT DATABASE" tests/conftest.py
```

如果测试过程中出现任何指向 `fund_db` 的迹象，**立即停止测试**，先修守卫，再继续。

### 6. 把辅助函数命名成 `test_` 开头

`conftest.py` 里连接数据库的函数必须叫 `get_test_connection()`，不要叫 `test_connection()`。

pytest 会把任何以 `test_` 开头的函数当成测试用例去执行。  
这个函数需要参数、而且返回的是数据库连接，一旦被 pytest 收集就会报错或产生莫名其妙的失败。

同理，后面写 `tests/factories.py` 之类的辅助文件时，辅助函数也不要用 `test_` 开头。

## 完成标准

以下条件全部满足，任务 015 才算完成：

1. 测试代码使用 `fund_test_db`。
2. 测试数据库和基础表可以自动创建。
3. 每个测试前会清空三张基础表。
4. `conftest.py` 中有 `assert_test_database()`，并且在 `get_test_connection()` 和 `clean_db` 中都调用了。
5. `clean_db` 在执行 `TRUNCATE` 之前会检查数据库名。
6. 步骤 3 的守卫验证命令确实抛出了 `RuntimeError`。
7. `pytest -q` 至少有 3 个测试通过。
8. 开发数据库 `fund_db` 的数据在跑完测试后没有变化。

## 完成后请反馈

1. 修改的文件列表。
2. `pytest -q` 的完整输出。
3. 测试数据库是否为 `fund_test_db`。
4. 守卫验证命令的输出。
5. 跑测试前后 `fund_db.bloggers` 的条数对比。
6. 是否出现外键清空错误。
7. 遇到的问题和未完成项。
