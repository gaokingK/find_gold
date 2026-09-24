# 任务 002：拆分 Flask 项目结构

## 任务目标

把任务 001 中的健康检查路由从 `app/__init__.py` 拆到独立的路由目录。

完成后，项目结构应变成：

```text
backend/
├── app/
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       └── health.py
├── requirements.txt
└── run.py
```

接口不变，仍然可以访问：

```text
http://127.0.0.1:5000/health
```

返回：

```json
{"code":0,"message":"ok","data":{"status":"ok"}}
```

---

## 前置条件

任务 001 已经完成，并且以下命令可以正常工作：

```bash
curl http://127.0.0.1:5000/health
```

如果任务 001 还没完成，请先完成任务 001。

---

## 新概念：Blueprint（蓝图）

Flask Blueprint 可以理解为“路由分组工具”。

当项目只有一个健康检查接口时，路由可以直接写在 `app/__init__.py` 里。之后会有博主、基金、初始持仓等接口，如果全部写在一起，文件会越来越乱。

Blueprint 的作用是把不同业务模块的路由拆到不同文件中。

本任务会创建一个 `health` Blueprint，后面还可以继续创建：

- `bloggers.py`
- `funds.py`
- `initial_positions.py`

### jsonify（JSON 响应工具）

`jsonify` 是 Flask 提供的把 Python 字典转换成 JSON HTTP 响应的工具。

它会做三件事：

1. 把 Python 的 `dict` 转成 JSON 字符串。
2. 设置响应头 `Content-Type: application/json`。
3. 把这个 JSON 响应返回给客户端。

如果不使用 `jsonify`，就需要自己调用 Python 标准库的 `json.dumps()`，并且手动设置响应头；否则前端拿到的可能不是标准的 JSON HTTP 响应。

---

## 执行目录

所有命令默认在以下目录执行：

```bash
cd /mnt/d/people/find_gold/backend
```

并且每次新开终端后先激活虚拟环境：

```bash
source .venv/bin/activate
```

---

## 具体步骤

### 步骤 1：确认当前项目结构

**必要性：**  
这一步是先确认任务 001 的基础环境还在。如果不先确认，可能出现你在修改一个不存在的 `app/__init__.py`，导致后面的步骤连续失败。

执行：

```bash
find app -maxdepth 2 -type f -print | sort
```

如果任务 001 完成，当前至少能看到：

```text
app/__init__.py
```

如果不存在，请先完成任务 001。

---

### 步骤 2：创建 `routes` 目录和包初始化文件

**必要性：**  
这是把“健康检查路由”和“应用创建逻辑”分开的第一步。`routes` 目录以后会承载健康检查、博主、基金、初始持仓等不同模块的路由。`__init__.py` 用来把 `routes` 声明成一个 Python 包，否则导入路径容易出问题。

在 `backend` 目录下执行：

```bash
mkdir -p app/routes
touch app/routes/__init__.py
```

完成后，`app/routes/__init__.py` 保持为空文件即可。

---

### 步骤 3：新建 `health.py` 路由文件

**必要性：**  
这一步把健康检查路由从主应用文件中移出去。以后新增业务模块时，也应该按类似方式拆分，否则所有接口都会堆在 `app/__init__.py` 里，文件会很快变得难以维护。

新建文件：

```text
backend/app/routes/health.py
```

文件内容：

```python
from flask import Blueprint, jsonify


health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
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

代码中出现的新对象：

| 名称 | 说明 |
| --- | --- |
| `Blueprint` | 蓝图，用来给路由分组 |
| `health_bp` | 这个健康检查路由分组的变量名 |
| `@health_bp.get("/health")` | 把 `health()` 函数注册为 `/health` 接口 |
| `jsonify` | JSON 响应工具，把 Python 字典转成 JSON HTTP 响应 |

---

### 步骤 4：修改 `app/__init__.py`

**必要性：**  
这一步让 Flask 应用知道 `health_bp` 这个路由分组的存在。如果不注册 Blueprint，即使 `health.py` 文件存在，Flask 也不会加载这个路由，访问 `/health` 会返回 404。

修改文件：

```text
backend/app/__init__.py
```

把原来的内容替换为：

```python
from flask import Flask

from app.routes.health import health_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(health_bp)

    return app
```

注意：

1. `app/__init__.py` 里不再写具体路由。
2. 它只负责创建 Flask 应用和注册 Blueprint。
3. 以后新增业务路由时，也要在 `create_app()` 里注册对应的 Blueprint。

---

### 步骤 5：确认 `run.py` 不需要修改

**必要性：**  
这一步是为了区分两类文件的职责：`run.py` 负责启动服务，`app/__init__.py` 负责创建应用。修改项目结构时，不应该随便改动启动入口，避免引入新的问题。

文件：

```text
backend/run.py
```

内容保持为：

```python
from app import create_app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
```

---

### 步骤 6：重启 Flask 服务

**必要性：**  
修改 Python 文件后，正在运行的 Flask 服务可能不会自动加载最新代码。重启服务能确保你现在验证的是修改后的结构，而不是旧进程的结果。

先停止旧服务。

在运行服务的终端按：

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
find app -maxdepth 3 -type f -print | sort
```

预期输出应包含：

```text
app/__init__.py
app/routes/__init__.py
app/routes/health.py
```

---

## 常见坑

### 1. `ImportError: cannot import name 'health_bp'`

检查文件路径是否正确：

```bash
cat app/routes/health.py
```

确认文件里有：

```python
health_bp = Blueprint("health", __name__)
```

并且确认 `app/__init__.py` 里的导入路径是：

```python
from app.routes.health import health_bp
```

---

### 2. 接口返回 404

通常是 Blueprint 没有注册。

检查 `app/__init__.py`，确认有：

```python
app.register_blueprint(health_bp)
```

---

### 3. 启动位置不对

必须在 `backend` 目录下启动：

```bash
cd /mnt/d/people/find_gold/backend
python run.py
```

不要在项目根目录 `/mnt/d/people/find_gold` 启动。

---

### 4. 虚拟环境没有激活

如果报：

```text
ModuleNotFoundError: No module named 'flask'
```

先执行：

```bash
source .venv/bin/activate
```

再启动服务。

---

## 完成标准

以下条件全部满足，任务 002 才算完成：

1. `app/routes/health.py` 存在。
2. `app/routes/health.py` 中定义了 `health_bp`。
3. `app/__init__.py` 只负责创建应用和注册 Blueprint。
4. `/health` 接口仍然返回统一 JSON 结构。
5. `find app -maxdepth 3 -type f -print | sort` 能看到新结构。

---

## 完成后请反馈

请把下面命令的输出发给后端协调人：

```bash
find app -maxdepth 3 -type f -print | sort
curl http://127.0.0.1:5000/health
```

任务 002 验收通过后，再进入任务 003：创建统一响应函数。
