# 任务 004：理解和使用 query 参数

## 预计完成时间

预计完成时间：约 1.5 小时。

估算依据：本任务只引入 `request.args` 这一个新概念，不涉及数据库、POST 请求和业务表。

## 任务目标

创建一个临时接口 `GET /api/v1/bloggers`，用于练习读取 query 参数。

完成后，下面的请求：

```text
http://127.0.0.1:5000/api/v1/bloggers?keyword=小星&status=observing
```

后端能读取：

```text
keyword = 小星
status = observing
```

并返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "keyword": "小星",
    "status": "observing"
  }
}
```

## 范围说明

本任务只做参数读取，不做真实业务查询。

不包含：

- 数据库查询
- 分页
- 排序
- 参数校验失败时的错误响应
- 真正的博主列表数据

## 前置条件

任务 003 已经完成，并且 `/health` 接口可以正常访问。

## 新概念：query 参数

query 参数的中文可以叫查询参数。

它出现在 URL 问号后面，例如：

```text
/api/v1/bloggers?keyword=小星&status=observing
```

用途是让客户端在不改变路径的情况下，向后端传递筛选条件。

Flask 中使用 `request.args` 读取 query 参数。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：确认任务 003 的项目结构

**必要性：**  
确认 `app/utils/responses.py` 和 `app/routes/health.py` 存在，避免在错误基础上开发。

```bash
find app -maxdepth 4 -type f -print | sort
```

### 步骤 2：新建 bloggers 路由文件

**必要性：**  
博主接口后面会越来越多，现在单独建立 `bloggers.py`，避免把博主路由继续塞到 `health.py` 里。

新建文件：

```text
backend/app/routes/bloggers.py
```

内容：

```python
from flask import Blueprint, request

from app.utils.responses import success


bloggers_bp = Blueprint("bloggers", __name__)


@bloggers_bp.get("/api/v1/bloggers")
def list_bloggers():
    keyword = request.args.get("keyword", "")
    status = request.args.get("status", "")

    return success(
        {
            "keyword": keyword,
            "status": status
        }
    )
```

代码中出现的新对象：

| 名称 | 说明 |
| --- | --- |
| `request` | Flask 提供的当前请求对象 |
| `request.args` | 保存 query 参数的对象 |
| `request.args.get("keyword", "")` | 读取 `keyword` 参数；如果不存在，返回空字符串 |

### 步骤 3：注册 bloggers Blueprint

**必要性：**  
Flask 只有注册 Blueprint 后，才能访问其中的路由。如果不注册，接口会返回 404。

修改文件：

```text
backend/app/__init__.py
```

替换为：

```python
from flask import Flask

from app.routes.health import health_bp
from app.routes.bloggers import bloggers_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(health_bp)
    app.register_blueprint(bloggers_bp)

    return app
```

### 步骤 4：重启服务

**必要性：**  
确保验证的是最新代码。

先按 `Ctrl + C` 停止服务，然后执行：

```bash
python run.py
```

## 验证方式

另开终端执行：

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers?keyword=小星&status=observing"
```

预期输出：

```json
{"code":0,"message":"ok","data":{"keyword":"小星","status":"observing"}}
```

再执行：

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers"
```

预期输出：

```json
{"code":0,"message":"ok","data":{"keyword":"","status":""}}
```

## 常见坑

### 1. 返回 404

检查 `bloggers_bp` 是否在 `app/__init__.py` 中注册。

### 2. 参数是 None

`request.args.get("keyword")` 在参数不存在时返回 `None`。  
本任务使用 `request.args.get("keyword", "")`，让默认值是空字符串。

### 3. URL 里的中文问题

`curl` 里包含中文时，建议加双引号：

```bash
curl "http://127.0.0.1:5000/api/v1/bloggers?keyword=小星"
```

## 完成标准

1. `app/routes/bloggers.py` 存在。
2. `bloggers_bp` 已注册。
3. 接口能读取 `keyword` 和 `status`。
4. 返回结构使用 `success()`。
5. 不包含数据库查询。

## 完成后请反馈

```bash
find app -maxdepth 4 -type f -print | sort
curl "http://127.0.0.1:5000/api/v1/bloggers?keyword=小星&status=observing"
```

任务 004 验收通过后，再进入任务 005：创建统一错误响应函数。
