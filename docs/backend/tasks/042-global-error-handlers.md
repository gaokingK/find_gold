# 任务 042：注册全局错误处理器

> **批次说明**：本任务属于 040 之后的补发批次，不是插在 013 后面。
> 001–040 里遗漏了全局错误兜底，现在补上。内容本身独立，随时可以做。
> 前置要求是 `error()` 函数（005 产出）和至少一个接收 JSON 请求体的 POST 接口（009 产出）都已存在。

## 预计完成时间

预计完成时间：约 1.5 小时。

估算依据：引入一个新概念（`errorhandler` 装饰器）和一个配置项（`PROPAGATE_EXCEPTIONS`）。代码是 5 个结构几乎一样的处理函数，改动量小；时间主要花在四种场景的验证和「debug 模式下 500 处理器不生效」这个坑上。不涉及数据库改动和业务逻辑。

## 任务目标

让下面四类场景返回 **统一的 JSON 错误结构**，而不是 Flask 默认的 HTML 错误页：

| 场景 | HTTP 状态码 | `code` |
| --- | --- | --- |
| 请求体不是合法 JSON | 400 | `INVALID_JSON` |
| 请求没有带 `Content-Type: application/json` | 400 | `INVALID_JSON` |
| 请求路径不存在 | 404 | `ENDPOINT_NOT_FOUND` |
| 请求方法不被允许 | 405 | `METHOD_NOT_ALLOWED` |
| 未捕获异常 | 500 | `INTERNAL_ERROR` |

完成后，请求一个不存在的路径：

```bash
curl -i http://127.0.0.1:5000/api/v1/not-exist
```

应该返回：

```json
{"code":"ENDPOINT_NOT_FOUND","details":[],"message":"请求路径不存在"}
```

**响应头的 `Content-Type` 必须是 `application/json`。**

---

## 范围说明

本任务只做**全局兜底**。

以下情况**不由本任务处理**，它们由各个接口自己返回：

- 参数校验失败（由接口自己调用 `error(code="VALIDATION_ERROR", ...)`）
- 业务冲突，例如博主名称重复（接口自己返回 409）
- 资源不存在，例如查询一个不存在的博主 ID（接口自己返回 404 + `BLOGGER_NOT_FOUND`）

一句话区分边界：**接口能预料到的错误，接口自己返回；接口没预料到、直接崩了或者根本没匹配上路由的，由本任务的全局处理器兜底。**

本任务不修改任何业务逻辑，不改动数据库。

---

## 前置条件

任务 013 已经完成，并且：

1. `app/utils/responses.py` 里有 `error()` 函数（任务 005 产出）。
2. 已经存在能接收 JSON 请求体的接口：`POST /api/v1/bloggers`（任务 009 产出）。
3. 任务 041（CORS）已完成。

验证前置条件：

```bash
curl -i -X POST http://127.0.0.1:5000/api/v1/bloggers \
  -H "Content-Type: application/json" \
  -d '{"name":"测试博主","sector":"科技","observe_start_date":"2026-10-01"}'
```

应该能正常写入并返回 `code: 0`。

**为什么它能独立补发**：它只依赖两样已经存在的东西——`error()` 函数（005 产出）和一个能接收 JSON 的 POST 接口（009 产出）。不依赖任何其他新任务，所以放在补发批次里做完全没问题。

---

## 为什么必须做这一步

Flask 在下面这些情况下，**默认返回的是一段 HTML**：

```html
<!doctype html>
<html lang=en>
<title>404 Not Found</title>
<h1>Not Found</h1>
<p>The requested URL was not found on the server...</p>
```

前端用 axios 请求，拿到的 `response.data` 是一整个 HTML 字符串。前端代码按 JSON 去取 `.code`、`.message`，取到的是 `undefined`，轻则页面显示「undefined」，重则直接抛错白屏。

而这类问题在开发阶段很隐蔽：用 curl 测试时终端里确实能看到 HTML，但开发者的注意力在「接口有没有返回」上，容易忽略返回的是 HTML 不是 JSON。等到前端联调时才爆发，那个时候要回头排查所有接口。

**所以这一步放在所有后续接口之前做。**

---

## 新概念：`errorhandler` 错误处理器装饰器

英文是 Error Handler，中文叫**错误处理器**。

`@app.errorhandler(...)` 是 Flask 提供的装饰器，作用是：**当应用抛出某种错误时，不要走 Flask 默认的处理方式，改走你写的这个函数。**

它的工作方式很像路由：

| 对比 | 路由 | 错误处理器 |
| --- | --- | --- |
| 装饰器 | `@bp.get("/xxx")` | `@app.errorhandler(404)` |
| 触发条件 | 请求的路径匹配上了 | 处理过程中抛出了对应的错误 |
| 返回值 | 正常响应 | 错误响应 |

括号里可以填两种东西：

1. **HTTP 状态码数字**，例如 `404`、`405`、`500`。
2. **异常类**，例如 `werkzeug.exceptions.NotFound`。

本任务统一用**数字**，因为更好读。

**本任务要处理的一个具体状态码：415（Unsupported Media Type，不支持的媒体类型）**。当请求带了请求体、但 `Content-Type` 不是 `application/json` 时，Flask 不会去解析它，直接抛 415。前端忘带 `Content-Type` 是极其常见的错误，如果不处理这个状态码，前端拿到的响应体是空的，连错误信息都没有，完全没法排查。

本任务的口径是：**415 和「JSON 写错了」在前端看来是同一类错误——后端读不到请求体。**所以统一按 HTTP 400 + `INVALID_JSON` 返回，只是 `message` 不同。这样前端不需要为「忘带请求头」再写一套分支。具体写法见下面步骤 2 的 `handle_unsupported_media_type`。

---

## 新概念：`PROPAGATE_EXCEPTIONS`

英文 Propagate Exceptions，字面意思是「传播异常」。

它的含义是：**未捕获的异常要不要继续往外抛，还是交给 Flask 转成 500 响应。**

Flask 的这个配置默认值是 `None`，意思是「跟随 `DEBUG` 或 `TESTING` 开关」：

| 配置 | 行为 |
| --- | --- |
| `debug=True`（我们的 `run.py` 就是） | 异常继续外抛，终端显示完整错误栈，**500 处理器不生效** |
| `debug=False` | 异常被 Flask 转成 500 响应，**500 处理器生效** |

**我们的 `run.py` 里写的是 `debug=True`**，所以如果不显式把它关掉，你辛辛苦苦写的 500 处理器在开发环境下**一次都不会被调用**。这是本任务最大的坑。

解决办法是在 `create_app()` 里显式写一行：

```python
app.config["PROPAGATE_EXCEPTIONS"] = False
```

这样即使开着 debug 方便开发，未捕获异常也会走我们自己的 JSON 处理器。

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

### 步骤 1：确认 `error()` 函数存在

**必要性：**  
全局错误处理器要复用任务 005 产出的 `error()` 函数，保证错误响应结构和各处手动返回的错误完全一致。先确认它在，避免写完发现调用了一个不存在的东西。

执行：

```bash
cat app/utils/responses.py
```

应该能看到：

```python
def error(code, message, details=None, http_status=400):
```

注意 `error()` 的返回值是 `jsonify(...), http_status` 这种「响应体 + 状态码」的二元组。全局错误处理器直接 `return` 它即可。

---

### 步骤 2：新建错误处理器文件

**必要性：**  
把 5 个处理函数集中放在 `app/utils/error_handlers.py` 里，而不是堆在 `app/__init__.py`。原因是 `__init__.py` 是应用入口，职责应该只有「创建 app、注册东西」；错误处理的具体实现属于工具代码，放 `utils/` 下和 `responses.py` 保持一致的项目习惯。这样以后要加第六种错误处理，不用动入口文件。

新建文件：

```text
backend/app/utils/error_handlers.py
```

文件内容：

```python
from flask import Flask

from app.utils.responses import error


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def handle_bad_request(e):
        return error(
            code="INVALID_JSON",
            message="请求体不是合法的 JSON",
            http_status=400,
        )

    @app.errorhandler(404)
    def handle_not_found(e):
        return error(
            code="ENDPOINT_NOT_FOUND",
            message="请求路径不存在",
            http_status=404,
        )

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return error(
            code="METHOD_NOT_ALLOWED",
            message="请求方法不被允许",
            http_status=405,
        )

    @app.errorhandler(415)
    def handle_unsupported_media_type(e):
        return error(
            code="INVALID_JSON",
            message="请求头 Content-Type 必须是 application/json",
            http_status=400,
        )

    @app.errorhandler(500)
    def handle_internal_error(e):
        return error(
            code="INTERNAL_ERROR",
            message="服务器内部错误",
            http_status=500,
        )
```

代码中出现的新对象：

| 名称 | 说明 |
| --- | --- |
| `register_error_handlers(app)` | 我们自己写的注册函数，把下面 5 个处理器挂到传入的 Flask 应用上 |
| `@app.errorhandler(400)` | Flask 装饰器，表示「应用出现 400 类错误时调用下面这个函数」 |
| `(e)` 参数 | Flask 会把错误对象本身传进来。本任务不需要用到它的内容，但参数位置必须留着，不能省略 |
| `Flask` 类型标注 | 只是告诉读代码的人 `app` 是什么类型，运行上没有影响 |

注意几点：

1. **5 个函数的 `details` 都不传**。`error()` 里 `details` 默认是 `None`，会转成 `[]`。全局兜底错误没有具体字段可以指出来，保持空数组。
2. **415 的 `http_status` 写的是 400**，不是 415。这是前面解释过的口径：对前端来说它和「JSON 写错了」是同一类问题。
3. **每个函数体里不要再写 `jsonify`**，统一复用 `error()`。

---

### 步骤 3：在 `create_app()` 里注册

**必要性：**  
上一步只是定义了函数，不去调用它就不会生效。注册必须发生在 `create_app()` 内部、Flask 应用对象创建之后，这样每次创建应用都会挂上这些处理器——包括以后 pytest 创建的测试用应用。

修改文件：

```text
backend/app/__init__.py
```

在导入部分加上：

```python
from app.utils.error_handlers import register_error_handlers
```

在 `create_app()` 函数体内，`app = Flask(__name__)` 之后加上这两行：

```python
    app.config["PROPAGATE_EXCEPTIONS"] = False
    register_error_handlers(app)
```

改完后，任务 041 加的内容还在，整个函数应该类似：

```python
from flask import Flask
from flask_cors import CORS

from app.routes.health import health_bp
from app.utils.error_handlers import register_error_handlers


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["PROPAGATE_EXCEPTIONS"] = False

    CORS(
        app,
        resources={r"/*": {"origins": "http://localhost:5173"}},
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
        supports_credentials=False,
    )

    register_error_handlers(app)

    app.register_blueprint(health_bp)
    # ... 其他 blueprint 保持不变

    return app
```

**`PROPAGATE_EXCEPTIONS = False` 这一行绝对不能漏。**漏掉的话，验证到第 5 个场景时会发现 500 处理器完全不生效，而且很难想到原因。

**这里是增量修改，不是整文件替换。** 你的 `app/__init__.py` 里现在已经有 `CORS(...)`（任务 041 加的）和好几个 `app.register_blueprint(...)`，全部保持原样，只新增 import 一行和函数体里两行。改完执行：

```bash
git diff app/__init__.py
```

确认 diff 里只有新增行（`+` 开头），没有删除行（`-` 开头）。

---

### 步骤 4：重启服务

**必要性：**  
Python 代码改动后必须重启进程才能生效，否则验证的是旧代码。

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

---

## 验证方式

下面 5 条验证**必须一条一条跑完**，每条都要看 `Content-Type` 是不是 `application/json`。只看状态码不够——状态码对了但返回 HTML 也算失败。

### 验证 1：路径不存在 → 404

```bash
curl -i http://127.0.0.1:5000/api/v1/not-exist
```

预期：

```text
HTTP/1.1 404 NOT FOUND
Content-Type: application/json
```

响应体：

```json
{"code":"ENDPOINT_NOT_FOUND","details":[],"message":"请求路径不存在"}
```

---

### 验证 2：方法不允许 → 405

`/api/v1/bloggers` 的详情接口是 `PUT`，列表接口支持 `GET` 和 `POST`。找一个不支持的方法，例如对只支持 GET 的路径发 DELETE：

```bash
curl -i -X DELETE http://127.0.0.1:5000/health
```

预期：

```text
HTTP/1.1 405 METHOD NOT ALLOWED
Content-Type: application/json
```

响应体：

```json
{"code":"METHOD_NOT_ALLOWED","details":[],"message":"请求方法不被允许"}
```

---

### 验证 3：请求体不是合法 JSON → 400

```bash
curl -i -X POST http://127.0.0.1:5000/api/v1/bloggers \
  -H "Content-Type: application/json" \
  -d '{name: 少了引号}'
```

预期：

```text
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json
```

响应体：

```json
{"code":"INVALID_JSON","details":[],"message":"请求体不是合法的 JSON"}
```

---

### 验证 4：忘带 `Content-Type` → 400

```bash
curl -i -X POST http://127.0.0.1:5000/api/v1/bloggers \
  -d '{"name":"测试博主"}'
```

注意这条**故意不写** `-H "Content-Type: application/json"`。

预期：

```text
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json
```

响应体：

```json
{"code":"INVALID_JSON","details":[],"message":"请求头 Content-Type 必须是 application/json"}
```

**这一步特别容易被忽略。** 漏掉 415 的处理器时，这条请求会返回 415 和空响应体，前端拿到 `null`，连错误信息都没有。

---

### 验证 5：未捕获异常 → 500

这一步需要临时改一行代码触发异常，验证完必须改回去。

临时修改 `app/routes/health.py`，在 `health()` 函数第一行加一句：

```python
    raise RuntimeError("临时测试用")
```

重启服务后执行：

```bash
curl -i http://127.0.0.1:5000/health
```

预期：

```text
HTTP/1.1 500 INTERNAL SERVER ERROR
Content-Type: application/json
```

响应体：

```json
{"code":"INTERNAL_ERROR","details":[],"message":"服务器内部错误"}
```

**验证完立刻把那行 `raise` 删掉并重启服务。**`:w` 之后不要忘了这一步。

如果这里看到的仍然是 HTML 页面或者终端里出现完整错误栈，说明步骤 3 的 `PROPAGATE_EXCEPTIONS = False` 没加上。

---

### 验证 6：确认没有误伤正常接口

```bash
curl -i http://127.0.0.1:5000/health
```

必须仍然是：

```json
{"code":0,"message":"ok","data":{"status":"ok"}}
```

这一条防止「错误处理器写太宽，把正常响应也吞了」。

---

## 常见坑

### 1. `PROPAGATE_EXCEPTIONS` 没设，500 处理器永远不生效

**这是本任务第一大坑。**

`run.py` 里 `debug=True`，Flask 在这个模式下会把异常继续往外抛，用于显示调试页面。结果是终端里能看到完整错误栈，但客户端收到的是 HTML 或者干脆没有响应体，我们写的 `handle_internal_error` 一次都不会被调用。

排查：先看 `app/__init__.py` 里有没有

```python
app.config["PROPAGATE_EXCEPTIONS"] = False
```

没有就补上，然后重启服务再测。

---

### 2. 处理器函数忘了写参数

错误写法：

```python
@app.errorhandler(404)
def handle_not_found():
    return error(...)
```

Flask 调用处理器时一定会传一个错误对象进来。参数对不上会报：

```text
TypeError: handle_not_found() takes 0 positional arguments but 1 was given
```

正确写法必须留着参数位置：

```python
@app.errorhandler(404)
def handle_not_found(e):
    return error(...)
```

---

### 3. 函数名重复导致覆盖

如果在同一个文件里写了两个都叫 `handle_not_found` 的函数，后定义的会覆盖先定义的，而且 Python 不会报错。

排查：

```bash
grep -n "def handle_" app/utils/error_handlers.py
```

5 个函数的名字应该互不相同。

---

### 4. 忘了调用注册函数

文件写好了、`app/__init__.py` 里也导入了，但没写上 `register_error_handlers(app)`——处理器一个都不会生效，而且完全不报错。

排查：

```bash
grep -n "register_error_handlers" app/__init__.py
```

应该能看到两行：一行 `import`，一行函数调用。

---

### 5. 415 被当成 415 返回

如果验证 4 返回的是 `HTTP/1.1 415 UNSUPPORTED MEDIA TYPE` 且响应体为空，说明漏了 `@app.errorhandler(415)`，或者它的 `http_status` 写成了 415 而不是 400。

正确写法：

```python
@app.errorhandler(415)
def handle_unsupported_media_type(e):
    return error(
        code="INVALID_JSON",
        message="请求头 Content-Type 必须是 application/json",
        http_status=400,
    )
```

---

### 6. 改完 `health.py` 忘了还原

验证 5 加的那行 `raise RuntimeError("临时测试用")` 如果忘了删，`/health` 会一直返回 500。

完成前务必执行：

```bash
cat app/routes/health.py
curl -i http://127.0.0.1:5000/health
```

确认 `/health` 恢复正常再提交。

---

## 完成标准

以下条件全部满足，任务 042 才算完成：

1. `app/utils/error_handlers.py` 存在，里面有 5 个处理器，覆盖 400 / 404 / 405 / 415 / 500。
2. `app/__init__.py` 里调用了 `register_error_handlers(app)`。
3. `app/__init__.py` 里有 `app.config["PROPAGATE_EXCEPTIONS"] = False`。
4. 验证 1 到 6 全部通过，每条响应的 `Content-Type` 都是 `application/json`。
5. `app/routes/health.py` 里临时加的 `raise` 已删除，`/health` 恢复正常。
6. 没有修改任何业务逻辑代码。
7. **`git diff app/__init__.py` 里只有新增行，没有删除行**（确认没误删 CORS 配置和已有 Blueprint 注册）。

---

## 完成后请反馈

请把下面命令的输出发给后端协调人：

```bash
cat app/utils/error_handlers.py
cat app/__init__.py
cat app/routes/health.py
curl -i http://127.0.0.1:5000/api/v1/not-exist
curl -i -X DELETE http://127.0.0.1:5000/health
curl -i -X POST http://127.0.0.1:5000/api/v1/bloggers \
  -H "Content-Type: application/json" \
  -d '{name: 少了引号}'
curl -i -X POST http://127.0.0.1:5000/api/v1/bloggers \
  -d '{"name":"测试博主"}'
curl -i http://127.0.0.1:5000/health
git diff app/__init__.py
```

任务 042 验收通过后，进入任务 043：统一测试工厂函数。
