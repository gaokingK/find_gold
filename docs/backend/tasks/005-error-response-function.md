# 任务 005：创建统一错误响应函数

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务引入 HTTP 状态码和 Flask 双值返回，同时要把错误响应抽象成可复用函数；还需要用一个真实接口验证它。

## 任务目标

新增一个统一错误响应函数，让后端的错误返回结构保持一致。

完成后，访问：

```text
http://127.0.0.1:5000/api/v1/bloggers?status=xxx
```

应返回 HTTP 状态码 `400`，响应体为：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "status 参数不合法",
  "details": [
    {
      "field": "status",
      "message": "status 只允许 observing 或 active"
    }
  ]
}
```

访问：

```text
http://127.0.0.1:5000/api/v1/bloggers?status=observing
```

仍然返回 HTTP 状态码 `200`。

## 范围说明

本任务只做错误响应函数和一个简单的 `status` 参数校验。

不包含：

- 数据库查询
- 博主列表真实数据
- 复杂参数校验
- 全局异常处理
- 日志系统

## 前置条件

任务 004 已经完成，并且以下文件存在：

```text
backend/app/utils/responses.py
backend/app/routes/bloggers.py
```

## 新概念：HTTP 状态码

HTTP 状态码的英文是 HTTP Status Code。

它用来告诉客户端这次请求的结果是什么。

本项目常用的状态码：

| 状态码 | 含义 |
| --- | --- |
| 200 | 成功 |
| 400 | 客户端传参错误 |
| 404 | 资源不存在 |
| 409 | 业务冲突 |
| 500 | 服务器内部错误 |

Flask 里可以通过这种写法返回 JSON 和状态码：

```python
return jsonify({...}), 400
```

这叫 Flask 双值返回：第一个值是响应体，第二个值是 HTTP 状态码。

## 执行目录

所有命令默认在以下目录执行：

```bash
cd /mnt/d/people/find_gold/backend
```

每次新开终端后先激活虚拟环境：

```bash
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：确认任务 004 的文件存在

**必要性：**  
本任务要修改 `responses.py` 和 `bloggers.py`。先确认文件存在，可以避免修改错误位置。

执行：

```bash
find app -maxdepth 4 -type f -print | sort
```

预期至少能看到：

```text
app/routes/bloggers.py
app/routes/health.py
app/utils/responses.py
```

---

### 步骤 2：在 `responses.py` 中新增 `error()`

**必要性：**  
这是本任务的核心。错误响应结构必须统一，否则以后每个接口都可能自己写一种错误格式，前端处理起来会很混乱。

修改文件：

```text
backend/app/utils/responses.py
```

把文件内容替换为：

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


def error(code, message, details=None, http_status=400):
    if details is None:
        details = []

    return jsonify(
        {
            "code": code,
            "message": message,
            "details": details
        }
    ), http_status
```

代码中出现的新对象：

| 名称 | 说明 |
| --- | --- |
| `error()` | 统一错误响应函数 |
| `code` | 业务错误码，字符串，例如 `VALIDATION_ERROR` |
| `message` | 给前端或用户看的错误提示 |
| `details` | 可选的错误明细，通常是一个数组 |
| `http_status` | HTTP 状态码，默认 `400` |
| `return jsonify(...), http_status` | Flask 双值返回：JSON 响应体 + HTTP 状态码 |

注意：

- 成功响应里的 `code` 是数字 `0`。
- 错误响应里的 `code` 是字符串错误码，例如 `VALIDATION_ERROR`。
- 这两个 `code` 含义不同，不要混淆。

---

### 步骤 3：修改 `bloggers.py`，使用 `error()`

**必要性：**  
这一步给 `error()` 一个真实使用场景：当 `status` 参数不合法时，返回统一的错误响应。这样不是只写了一个没人调用的函数。

修改文件：

```text
backend/app/routes/bloggers.py
```

把文件内容替换为：

```python
from flask import Blueprint, request

from app.utils.responses import error, success


bloggers_bp = Blueprint("bloggers", __name__)


@bloggers_bp.get("/api/v1/bloggers")
def list_bloggers():
    keyword = request.args.get("keyword", "")
    status = request.args.get("status", "")

    allowed_statuses = ["observing", "active"]

    if status and status not in allowed_statuses:
        return error(
            code="VALIDATION_ERROR",
            message="status 参数不合法",
            details=[
                {
                    "field": "status",
                    "message": "status 只允许 observing 或 active"
                }
            ],
            http_status=400
        )

    return success(
        {
            "keyword": keyword,
            "status": status
        }
    )
```

说明：

1. `status` 为空字符串时，表示没有传这个参数，不报错。
2. `status` 不是空字符串时，必须在 `observing` 和 `active` 中间。
3. 如果不合法，直接返回 `error()`。
4. 如果合法，继续返回 `success()`。

---

### 步骤 4：重启 Flask 服务

**必要性：**  
修改 Python 文件后需要重启服务，否则验证的可能是旧代码。

先停止旧服务：

```text
Ctrl + C
```

再启动：

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
python run.py
```

---

## 验证方式

### 1. 合法 status

另开一个 WSL 终端执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers?status=observing"
```

预期：

```text
HTTP/1.1 200 OK
```

响应体：

```json
{"code":0,"message":"ok","data":{"keyword":"","status":"observing"}}
```

### 2. 不合法 status

执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers?status=xxx"
```

预期：

```text
HTTP/1.1 400 BAD REQUEST
```

响应体：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "status 参数不合法",
  "details": [
    {
      "field": "status",
      "message": "status 只允许 observing 或 active"
    }
  ]
}
```

### 3. 不传 status

执行：

```bash
curl -i "http://127.0.0.1:5000/api/v1/bloggers"
```

预期：

```text
HTTP/1.1 200 OK
```

## 常见坑

### 1. 忘记返回 HTTP 状态码

如果 `error()` 写成：

```python
return jsonify({...})
```

Flask 默认会返回 `200`。  
错误响应也显示成功，是不对的。

正确写法是：

```python
return jsonify({...}), http_status
```

---

### 2. 把业务错误码和 HTTP 状态码混淆

例如：

```json
{
  "code": "VALIDATION_ERROR"
}
```

这里的 `code` 是业务错误码。  
HTTP 状态码是响应头里的 `400`。

两者不是同一个东西。

---

### 3. `details` 直接传 `None`

如果函数里不处理：

```python
details = details or []
```

可能把空列表、空字符串等值误处理。  
本任务使用：

```python
if details is None:
    details = []
```

更精确。

---

### 4. 修改后没有重启服务

先停止旧服务，再重新运行：

```bash
python run.py
```

---

## 完成标准

1. `responses.py` 中存在 `success()` 和 `error()`。
2. `error()` 能返回 JSON 和指定 HTTP 状态码。
3. `status=xxx` 时返回 `400`。
4. `status=observing` 时返回 `200`。
5. 错误响应结构包含 `code`、`message`、`details`。

## 完成后请反馈

请把下面命令的输出发给后端协调人：

```bash
find app -maxdepth 4 -type f -print | sort
curl -i "http://127.0.0.1:5000/api/v1/bloggers?status=observing"
curl -i "http://127.0.0.1:5000/api/v1/bloggers?status=xxx"
```

任务 005 验收通过后，再进入任务 006：接入 MySQL 基础连接。
