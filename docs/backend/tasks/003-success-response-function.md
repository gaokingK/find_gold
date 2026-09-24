# 任务 003：创建统一成功响应函数

## 任务目标

创建一个后端工具函数，把所有成功响应都统一成：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

完成后：

1. 新增 `app/utils/responses.py`。
2. 新增 `success()` 函数。
3. 修改 `/health` 接口，让它使用 `success()`。
4. `/health` 的返回结果保持不变。

接口仍然是：

```text
http://127.0.0.1:5000/health
```

返回：

```json
{"code":0,"message":"ok","data":{"status":"ok"}}
```

---

## 范围说明

本任务只做 **统一成功响应函数**。

错误响应函数暂不在本任务实现。原因是错误响应通常要和 HTTP 状态码、错误码、参数校验一起设计，如果现在一起做，会引入太多新概念。

本任务不接入数据库，不新增业务接口，不实现博主、基金、初始持仓功能。

---

## 前置条件

任务 002 已经完成，并且以下两个条件都满足：

1. 项目结构中已经有：

```text
backend/app/__init__.py
backend/app/routes/health.py
```

2. `/health` 接口可以正常访问：

```bash
curl http://127.0.0.1:5000/health
```

如果任务 002 还没完成，请先完成任务 002。

---

## 新概念：工具函数

工具函数的英文是 Utility Function。

可以理解为：  
**把一段会被多个地方重复使用的逻辑，写成一个独立函数。**

在本项目里，所有成功接口都希望返回同样的 JSON 结构：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

如果不做工具函数，以后每个接口都要手写一次：

```python
return jsonify(
    {
        "code": 0,
        "message": "ok",
        "data": {...}
    }
)
```

这样会带来两个问题：

1. 代码重复。
2. 以后调整响应结构时，需要修改很多接口。

所以本任务把成功响应逻辑抽成 `success()`。

---

## 执行目录

所有命令默认在以下目录执行：

```bash
cd /mnt/d/people/find_gold/backend
```

每次新开终端后，先激活虚拟环境：

```bash
source .venv/bin/activate
```

---

## 具体步骤

### 步骤 1：确认任务 002 的项目结构

**必要性：**  
本任务要在 `app/` 下新增 `utils/` 目录。先确认任务 002 的结构存在，可以避免在错误的位置创建文件。

执行：

```bash
find app -maxdepth 3 -type f -print | sort
```

预期至少能看到：

```text
app/__init__.py
app/routes/__init__.py
app/routes/health.py
```

如果看不到这些文件，请先完成任务 002。

---

### 步骤 2：创建 `utils` 目录

**必要性：**  
`utils` 是工具代码目录。后面可能会放响应函数、日期处理函数、参数校验函数等。现在先创建这个目录，是为了让工具代码有固定位置，避免以后把工具函数散落在路由文件里。

在 `backend` 目录下执行：

```bash
mkdir -p app/utils
touch app/utils/__init__.py
```

`app/utils/__init__.py` 保持为空文件即可。

---

### 步骤 3：新建统一成功响应函数文件

**必要性：**  
这是本任务的核心。把成功响应结构集中到一个函数里，以后所有成功接口都可以复用它，避免每个接口手写一遍 `code`、`message`、`data`。

新建文件：

```text
backend/app/utils/responses.py
```

文件内容：

```python
from flask import jsonify


def success(data=None):
    return jsonify(
        {
            "code": 0,
            "message": "ok",
            "data": data if data is not None else {}
        }
    )
```

代码中出现的新对象：

| 名称 | 说明 |
| --- | --- |
| `success()` | 统一成功响应函数，负责组装 `code`、`message`、`data` |
| `data=None` | Python 的默认参数写法。调用时可以不传 `data`，此时默认是 `None` |
| `data if data is not None else {}` | 如果调用方没有传 `data`，就返回空对象 `{}` |

注意：

- `jsonify` 在任务 002 里已经介绍过，它是 Flask 提供的把 Python 字典转换成 JSON HTTP 响应的工具。
- 这里使用 `data if data is not None else {}`，而不是直接使用 `data or {}`，是因为以后有些接口可能希望返回 `[]`、`0` 或其他有意义的值。使用 `or` 可能会误把这些值替换成 `{}`。

---

### 步骤 4：修改 `health.py`

**必要性：**  
这一步把 `/health` 接口改为使用新的 `success()` 函数。这样可以立刻验证工具函数是否可用，同时让现有接口保持和接口文档一致的返回结构。

修改文件：

```text
backend/app/routes/health.py
```

把原来的内容替换为：

```python
from flask import Blueprint

from app.utils.responses import success


health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    return success(
        {
            "status": "ok"
        }
    )
```

修改点：

1. 不再直接导入 `jsonify`。
2. 改为导入 `success()`。
3. `health()` 函数只负责返回健康检查数据，不再负责手写响应结构。
4. `/health` 的返回结构保持不变。

---

### 步骤 5：确认 `app/__init__.py` 不需要修改

**必要性：**  
本任务只新增工具函数，并没有新增路由分组，所以不需要注册新的 Blueprint。确认这一点可以避免新手误改应用入口文件。

文件：

```text
backend/app/__init__.py
```

内容保持为：

```python
from flask import Flask

from app.routes.health import health_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(health_bp)

    return app
```

---

### 步骤 6：重启 Flask 服务

**必要性：**  
修改 Python 文件后，需要重启服务，确保验证的是最新代码，而不是旧进程返回的结果。

先在运行服务的终端按：

```text
Ctrl + C
```

然后重新启动：

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
python run.py
```

预期输出类似：

```text
 * Running on http://127.0.0.1:5000
```

---

## 验证方式

另开一个 WSL 终端执行：

```bash
curl http://127.0.0.1:5000/health
```

预期输出：

```json
{"code":0,"message":"ok","data":{"status":"ok"}}
```

再检查项目结构：

```bash
find app -maxdepth 4 -type f -print | sort
```

预期应包含：

```text
app/__init__.py
app/routes/__init__.py
app/routes/health.py
app/utils/__init__.py
app/utils/responses.py
```

---

## 常见坑

### 1. `ImportError: cannot import name 'success'`

先确认文件是否存在：

```bash
cat app/utils/responses.py
```

确认里面有：

```python
def success(data=None):
```

并且 `health.py` 里的导入路径是：

```python
from app.utils.responses import success
```

---

### 2. 返回结果还是旧结构

检查 `health.py` 是否还在直接调用 `jsonify()`。

正确写法应该是：

```python
return success(
    {
        "status": "ok"
    }
)
```

不是：

```python
return jsonify(
    {
        "code": 0,
        "message": "ok",
        "data": {
            "status": "ok"
        }
    }
)
```

---

### 3. `ModuleNotFoundError: No module named 'app'`

通常是启动位置不对。

必须回到 `backend` 目录启动：

```bash
cd /mnt/d/people/find_gold/backend
python run.py
```

---

### 4. `ModuleNotFoundError: No module named 'flask'`

通常是虚拟环境没有激活。

先执行：

```bash
source .venv/bin/activate
```

再启动服务。

---

## 完成标准

以下条件全部满足，任务 003 才算完成：

1. `app/utils/responses.py` 存在。
2. `success()` 函数存在。
3. `health.py` 使用 `success()`，不再直接手写 `code`、`message`、`data`。
4. `/health` 接口返回结构不变。
5. 项目结构中存在 `app/utils/` 目录。

---

## 完成后请反馈

请把下面命令的输出发给后端协调人：

```bash
find app -maxdepth 4 -type f -print | sort
curl http://127.0.0.1:5000/health
```

任务 003 验收通过后，再进入任务 004：给 Flask 接口增加 query 参数。
