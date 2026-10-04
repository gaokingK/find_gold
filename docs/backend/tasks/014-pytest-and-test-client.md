# 任务 014：搭建 pytest 与 Flask Test Client

## 预计完成时间

预计完成时间：约 2.5 小时。

估算依据：本任务主要安装测试依赖、创建测试目录、配置 pytest 的模块搜索路径、编写一个健康检查测试；需要理解 pytest、Flask Test Client 和 fixture 三个新概念，其中「pytest 怎么找到 `app` 模块」是新手最容易卡住的一步，所以留出额外时间。

## 任务目标

搭建后端自动化测试基础环境。

完成后可以：

1. 在终端运行 `pytest -q`。
2. Flask 应用可以被测试代码导入。
3. 能用 Flask Test Client 模拟一次 HTTP 请求。
4. `/health` 接口有第一个自动化测试。
5. `backend/pytest.ini` 固定了 pytest 的运行配置，换台机器也能跑。

## 范围说明

本任务只搭建测试环境和写一个健康检查测试。

不包含：

- 数据库测试
- 博主模块测试
- 基金模块测试
- 初始持仓模块测试
- 前端测试

## 前置条件

1. 任务 013 已完成，第一版基础数据模块手工验收通过。
2. Flask 服务可以在本地启动。
3. `backend/.venv` 虚拟环境可用。

## 新概念：pytest、Flask Test Client、fixture

### pytest

pytest 是 Python 常用的自动化测试框架。  
它会自动发现名字以 `test_` 开头的函数和文件，并提供断言、fixture 等测试工具。

### Flask Test Client

Flask Test Client 是 Flask 提供的测试工具。  
它不需要真正启动服务，就可以模拟 HTTP 请求，例如 `GET /health`。

### fixture

fixture 是 pytest 提供的“测试前置数据”机制。  
比如多个测试都需要同一个 Flask 应用和客户端，就可以把它们写成 fixture，避免重复代码。

### pytest.ini 与 pythonpath

`pytest.ini` 是 pytest 的配置文件，放在项目根目录（这里是 `backend/`）。  
pytest 启动时会读取它，里面的配置对所有人、所有机器都生效，不需要每次手敲参数。

`pythonpath` 是 `pytest.ini` 里的一个配置项，作用是把指定目录加入 Python 的模块搜索路径。

这一项**必须配**。原因是：直接运行 `pytest` 命令时，pytest 不会把当前目录加入模块搜索路径，它只会把测试文件所在的 `tests/` 目录加进去。于是 `tests/conftest.py` 里的 `from app import create_app` 会找不到 `backend/app`，报 `ModuleNotFoundError: No module named 'app'`。  
配上 `pythonpath = .` 之后，`backend/` 目录会被加入搜索路径，`app` 就能被导入了。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=你的数据库密码
```

说明：本任务只测 `/health`，暂时不连数据库，但下一个任务 015 会真的连 MySQL。  
现在就把这几个环境变量导出，可以避免 015 里出现 `Access denied for user` 却不知道原因。  
`DB_NAME` 不用导出，`tests/conftest.py` 会自己设置成 `fund_test_db`。

数据库密码只通过环境变量传入，不要写进任何会提交到 Git 的文件。

## 具体步骤

### 步骤 1：创建测试依赖文件

**必要性：**  
测试依赖和生产依赖应该分开，避免把测试工具带入生产部署。

新建文件：

```text
backend/requirements-dev.txt
```

内容：

```text
pytest==8.3.4
```

执行：

```bash
pip install -r requirements-dev.txt
```

---

### 步骤 2：创建测试目录

**必要性：**  
测试代码应该和业务代码分开，方便查找和维护。

执行：

```bash
mkdir -p tests
```

不需要在 `tests` 目录里创建 `__init__.py`。pytest 可以直接发现测试文件。

---

### 步骤 3：创建 pytest 配置文件

**必要性：**  
不做这一步，下面的 `pytest -q` 会直接报 `ModuleNotFoundError: No module named 'app'`。  
因为 pytest 不会自动把 `backend/` 目录加入模块搜索路径，`tests/conftest.py` 里的 `from app import create_app` 就会失败。  
这一步是本任务最关键的配置，不能跳过。

新建文件：

```text
backend/pytest.ini
```

内容：

```ini
[pytest]
pythonpath = .
testpaths = tests
```

逐行说明：

- `[pytest]` 是配置段名，pytest 只读这一段。
- `pythonpath = .` 把 `pytest.ini` 所在目录（也就是 `backend/`）加入模块搜索路径，这样 `import app` 才能成功。
- `testpaths = tests` 告诉 pytest 只在 `tests` 目录里找测试文件，不要去扫 `.venv` 或 `database`，可以让测试启动更快。

注意 `pytest.ini` 必须放在 `backend/` 目录下，和 `run.py`、`app/` 同级，不要放进 `tests/`。

---

### 步骤 4：创建测试配置文件

**必要性：**  
多个测试都会用到同一个 Flask 应用和测试客户端。集中写在 `conftest.py` 里，可以避免重复代码。

新建文件：

```text
backend/tests/conftest.py
```

内容：

```python
import os

os.environ["DB_NAME"] = "fund_test_db"

import pytest

from app import create_app


@pytest.fixture()
def app():
    return create_app()


@pytest.fixture()
def client(app):
    return app.test_client()
```

说明：

- `os.environ["DB_NAME"] = "fund_test_db"` 先设置测试数据库名，后面数据库测试会用到。
- `app` fixture 返回 Flask 应用对象。
- `client` fixture 返回 Flask Test Client。

---

### 步骤 5：创建健康检查测试

**必要性：**  
先测试最简单的接口，验证测试环境本身是否正确。这个测试通过后，才说明 pytest 和 Test Client 都可用。

新建文件：

```text
backend/tests/test_health.py
```

内容：

```python
def test_health(client):
    response = client.get("/health")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["message"] == "ok"
    assert body["data"]["status"] == "ok"
```

---

### 步骤 6：运行测试

**必要性：**  
必须实际运行测试，确认环境搭建成功。

执行：

```bash
pytest -q
```

预期输出类似：

```text
1 passed in 0.20s
```

## 验证方式

执行：

```bash
pytest -q
```

如果看到 `1 passed`，说明测试环境搭建成功。

## 常见坑

### 1. 在错误目录运行 pytest

pytest 必须在 `backend` 目录下运行。

正确执行目录：

```bash
cd /mnt/d/people/find_gold/backend
pytest -q
```

不要在项目根目录运行。

### 2. 找不到 `app` 模块

如果报：

```text
ModuleNotFoundError: No module named 'app'
```

按下面顺序排查，**第一个原因最常见**：

原因一：没有创建 `backend/pytest.ini`，或者里面缺少 `pythonpath = .`。

```bash
cat pytest.ini
```

预期能看到 `pythonpath = .`。如果文件不存在，回到步骤 3。

原因二：`pytest.ini` 放错了位置，比如放进了 `tests/`。它必须和 `app/`、`run.py` 同级。

```bash
ls pytest.ini app run.py
```

原因三：运行目录不对，或者虚拟环境没有激活。

```bash
pwd
which python
```

确认 `pwd` 是 `/mnt/d/people/find_gold/backend`，并且 `which python` 指向 `.venv/bin/python`。

补充说明：如果一时没配好 `pytest.ini`，临时用下面命令也能跑通，因为 `python -m` 会把当前目录加入模块搜索路径：

```bash
python -m pytest -q
```

但这只是临时办法。本任务仍然要求创建 `pytest.ini`，让 `pytest -q` 直接可用。

### 3. 测试文件命名错误

pytest 默认只识别符合规则的文件和函数名。

文件名应该是：

```text
test_health.py
```

函数名应该是：

```python
def test_health(client):
```

不要写成 `check_health.py` 或 `def health_test()`。

### 4. 忘记安装 pytest

如果报：

```text
No module named 'pytest'
```

执行：

```bash
pip install -r requirements-dev.txt
```

### 5. `conftest.py` 和 `pytest.ini` 位置放反

两个文件的位置不一样，不要混：

```text
backend/pytest.ini          ← 和 app/、run.py 同级
backend/tests/conftest.py   ← 在 tests/ 里面
```

`conftest.py` 不要放到 `backend/` 或项目根目录，`pytest.ini` 也不要放进 `tests/`。

检查命令：

```bash
ls pytest.ini tests/conftest.py
```

## 完成标准

以下条件全部满足，任务 014 才算完成：

1. `backend/requirements-dev.txt` 存在。
2. `pytest` 已安装。
3. `backend/pytest.ini` 存在，且包含 `pythonpath = .`。
4. `backend/tests/conftest.py` 存在。
5. `backend/tests/test_health.py` 存在。
6. 直接执行 `pytest -q`（不加 `python -m`）至少有 1 个测试通过。
7. 测试没有依赖手工启动 Flask 服务。

## 完成后请反馈

1. 新增的文件列表。
2. `pytest.ini` 的内容。
3. `pytest -q` 的完整输出。
4. 是否在正确目录执行。
5. 遇到的问题和未完成项。
