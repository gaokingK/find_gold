# 任务 006：接入 MySQL 基础连接

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务引入 MySQL 客户端库、连接配置和连接函数；同时要创建一个独立脚本验证数据库连接。

## 任务目标

让 Flask 后端能够连接 MySQL。

完成后，执行：

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
python -m scripts.check_db
```

应输出类似：

```text
MySQL connection OK: {'ok': 1}
```

## 范围说明

本任务只做数据库连接，不做业务表初始化，不实现业务接口。

不包含：

- 创建博主、基金、初始持仓表
- 实现博主接口
- ORM
- 数据库迁移工具
- 连接池

## 前置条件

1. 任务 005 已经完成。
2. 本机已经安装 MySQL。
3. 你知道 MySQL 的用户名和密码。

如果 MySQL 还没有安装，请先停止本任务，告诉我后再安排安装任务。

## 新概念：数据库连接

数据库连接的英文是 Database Connection。

Flask 本身不能直接访问 MySQL，需要通过一个数据库驱动程序连接数据库。本项目使用 `PyMySQL`。

`PyMySQL` 是一个用 Python 编写的 MySQL 客户端库。

本任务会建立两个文件：

- `app/config.py`：保存数据库配置。
- `app/db.py`：负责创建数据库连接。

## 执行目录

所有命令默认在以下目录执行：

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：安装 PyMySQL

**必要性：**  
没有数据库驱动，Python 无法连接 MySQL。

执行：

```bash
pip install PyMySQL==1.1.1
```

然后修改：

```text
backend/requirements.txt
```

确认里面有：

```text
Flask==3.0.3
PyMySQL==1.1.1
```

---

### 步骤 2：创建数据库配置文件

**必要性：**  
数据库主机、端口、用户名、密码不应该写死在业务代码里。集中放在 `config.py` 中，后面修改更方便。

新建文件：

```text
backend/app/config.py
```

内容：

```python
import os

from pymysql.cursors import DictCursor


DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "fund_db"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
}
```

说明：

| 名称 | 说明 |
| --- | --- |
| `DB_HOST` | 数据库地址，本机默认 `127.0.0.1` |
| `DB_PORT` | 数据库端口，MySQL 默认 `3306` |
| `DB_USER` | 数据库用户名 |
| `DB_PASSWORD` | 数据库密码 |
| `DB_NAME` | 数据库名 |
| `DictCursor` | 让查询结果以字典返回，而不是元组 |

---

### 步骤 3：创建数据库连接函数

**必要性：**  
以后每个需要查询数据库的接口都会用到连接。集中写一个 `get_connection()`，避免重复代码。

新建文件：

```text
backend/app/db.py
```

内容：

```python
from pymysql import connect

from app.config import DB_CONFIG


def get_connection():
    return connect(**DB_CONFIG)
```

---

### 步骤 4：创建数据库连接验证脚本

**必要性：**  
先确认数据库能连上，再去建表和写业务接口。否则后面出错时，很难判断是接口问题还是数据库问题。

新建目录和文件：

```bash
mkdir -p scripts
touch scripts/__init__.py
```

新建文件：

```text
backend/scripts/check_db.py
```

内容：

```python
from app.db import get_connection


def main():
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            row = cursor.fetchone()

        print("MySQL connection OK:", row)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

---

### 步骤 5：设置环境变量

**必要性：**  
数据库密码不应该提交到 Git。使用环境变量可以在不修改代码的情况下切换数据库配置。

在当前终端执行：

```bash
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=你的数据库密码
export DB_NAME=fund_db
```

注意：

- `DB_PASSWORD=你的数据库密码` 中不要有空格。
- 如果密码里有特殊字符，建议加引号。
- 新开终端后需要重新执行这些命令。

---

### 步骤 6：验证数据库连接

**必要性：**  
这是本任务的验收点。

执行：

```bash
python -m scripts.check_db
```

如果数据库 `fund_db` 还不存在，先创建：

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS fund_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

然后再次执行：

```bash
python -m scripts.check_db
```

## 验证方式

成功时输出类似：

```text
MySQL connection OK: {'ok': 1}
```

## 常见坑

### 1. `Access denied for user`

通常是用户名或密码错误。

可以用下面的命令验证：

```bash
mysql -u root -p
```

如果能进入 MySQL，说明账号密码可用。

---

### 2. `Unknown database 'fund_db'`

说明数据库不存在。

执行：

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS fund_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

---

### 3. `Can't connect to MySQL server`

可能是 MySQL 没启动。

在 WSL 中检查：

```bash
sudo service mysql status
```

如果没有运行，执行：

```bash
sudo service mysql start
```

---

### 4. `ModuleNotFoundError: No module named 'app'`

必须在 `backend` 目录执行：

```bash
cd /mnt/d/people/find_gold/backend
python -m scripts.check_db
```

---

### 5. 虚拟环境没有激活

如果报：

```text
ModuleNotFoundError: No module named 'pymysql'
```

先执行：

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## 完成标准

1. `requirements.txt` 中有 `PyMySQL`。
2. `app/config.py` 存在。
3. `app/db.py` 存在。
4. `scripts/check_db.py` 存在。
5. `python -m scripts.check_db` 能成功连接 MySQL。

## 完成后请反馈

请把下面命令的输出发给后端协调人：

```bash
cat requirements.txt
find app scripts -maxdepth 3 -type f -print | sort
python -m scripts.check_db
```

任务 006 验收通过后，再进入任务 007：初始化第一版基础数据表。
