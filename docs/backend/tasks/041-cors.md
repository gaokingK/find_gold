# 任务 041：配置 CORS 跨域

> **批次说明**：本任务属于 040 之后的补发批次，不是插在 003 后面。
> 001–040 里遗漏了跨域配置，现在补上。内容本身独立，随时可以做。

## 预计完成时间

预计完成时间：约 1.5 小时。

估算依据：引入一个新依赖（`flask-cors`）和两个新概念（同源策略、预检请求）。代码改动很小，只有 `app/__init__.py` 一个文件加一小段配置；时间主要花在理解「为什么浏览器要拦这个请求」和验证环节上。没有数据库操作，没有业务逻辑。

## 任务目标

让运行在 `http://localhost:5173` 的前端，能够正常请求运行在 `http://127.0.0.1:5000` 的后端接口。

完成后，执行：

```bash
curl -i -H "Origin: http://localhost:5173" http://127.0.0.1:5000/health
```

响应头里应该能看到：

```text
Access-Control-Allow-Origin: http://localhost:5173
```

`/health` 接口的返回内容保持不变。

---

## 范围说明

本任务只做 **跨域配置**。

不包含：

- 前端代码改动
- 任何业务接口
- 数据库操作
- 认证、鉴权
- 除 `localhost:5173` 以外的其他来源

---

## 前置条件

任务 003 已经完成，并且 `/health` 接口返回统一结构：

```bash
curl http://127.0.0.1:5000/health
```

预期输出：

```json
{"code":0,"message":"ok","data":{"status":"ok"}}
```

如果任务 003 还没完成，请先完成任务 003。

---

## 为什么必须做这一步

本项目前端和后端是**分开运行**的两个程序：

| 程序 | 地址 | 端口 |
| --- | --- | --- |
| 前端（Vue 3 + Vite） | `http://localhost:5173` | 5173 |
| 后端（Flask） | `http://127.0.0.1:5000` | 5000 |

浏览器有一个安全规则叫**同源策略**，下面会解释。简单说：**默认情况下，浏览器不允许前端页面去请求「另一个源」的接口。**

如果现在不做这一步，后面每写完一个接口都会遇到这个现象：

- 用 `curl` 请求接口 → 正常返回数据
- 前端页面请求同一个接口 → 浏览器控制台报错，**一个字的数据都拿不到**

而且浏览器给的错误信息是类似 `blocked by CORS policy` 这种，看起来很像接口写错了。新手很容易一路去查 Flask 代码，查半天查不到原因。**所以这一步放在所有接口之前做，后面的接口一写完就能在页面上看到效果。**

---

## 新概念：同源策略（Same-Origin Policy）

英文是 Same-Origin Policy。

**源（Origin）** 指的是三样东西的组合：协议、域名、端口。

三个里面**只要有一个不一样**，就是不同的源：

| 地址 A | 地址 B | 是否同源 | 原因 |
| --- | --- | --- | --- |
| `http://localhost:5173` | `http://localhost:5173/page` | 是 | 只是路径不同，不影响同源判断 |
| `http://localhost:5173` | `http://127.0.0.1:5173` | 否 | 域名不同（`localhost` 和 `127.0.0.1` 在浏览器眼里是两回事） |
| `http://localhost:5173` | `https://localhost:5173` | 否 | 协议不同 |
| `http://localhost:5173` | `http://localhost:5000` | 否 | **端口不同** |

我们的前端和后端属于最后一种：**端口不同**。

**同源策略的作用**：浏览器限制一个源的网页，不能随便读取另一个源返回的数据。这是为了防止恶意网站拿着你的登录状态去读你的银行页面。

**为什么 curl 没事**：同源策略是**浏览器**的规则，`curl`、Python 脚本、后端之间的调用都不受它限制。这就是为什么命令行测得好好的、浏览器却不行。

---

## 新概念：CORS 与预检请求

**CORS** 的英文是 Cross-Origin Resource Sharing，中文是**跨源资源共享**。

它是一套让服务器「主动声明我允许哪些源访问我」的机制。做法就是后端在响应里加几个 `Access-Control-*` 开头的响应头，浏览器看到这些头，就放行。

| 响应头 | 作用 |
| --- | --- |
| `Access-Control-Allow-Origin` | 允许哪个源访问 |
| `Access-Control-Allow-Methods` | 允许哪些 HTTP 方法 |
| `Access-Control-Allow-Headers` | 允许请求里带哪些自定义头 |

**预检请求（Preflight）**：

对于 `PUT`、`DELETE` 这种会修改数据的请求，或者带了 `Content-Type: application/json` 的请求，浏览器不会直接发过去，而是**先发一个 `OPTIONS` 请求探一下路**，问服务器「我待会儿要用 PUT 方法、带 Content-Type 头，你允许吗？」。服务器回答允许，浏览器才发真正的请求。

这里有个容易踩的点：**如果后端没有正确处理 `OPTIONS` 请求，`GET` 可能正常，但 `PUT` 和 `DELETE` 一定失败。**

**实现工具**：自己手写这些响应头也可以，但要处理「哪些路径加、哪些方法放行、OPTIONS 怎么回」这些细节，容易漏。所以我们用第三方库 `flask-cors`，它把这套逻辑封装好了，只需要告诉它「允许哪个源」。一句话记住它：**一个给 Flask 自动添加跨域响应头的库。**

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

### 步骤 1：安装 `flask-cors`

**必要性：**  
这是本任务要用的第三方库。不装的话下一步的 `from flask_cors import CORS` 会报 `ModuleNotFoundError`。

执行：

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
pip install flask-cors
```

安装完成后确认版本：

```bash
pip show flask-cors
```

预期能看到类似：

```text
Name: Flask-CORS
Version: 6.0.5
```

注意包名有个细节：**安装时写 `flask-cors`（中间是连字符），导入时写 `flask_cors`（中间是下划线）**。这是 Python 包的常见约定，不是笔误。

---

### 步骤 2：把依赖写进 `requirements.txt`

**必要性：**  
`requirements.txt` 记录了项目依赖的所有包和版本。别人拿到项目后靠 `pip install -r requirements.txt` 一次性装齐。只装不写，换台机器就跑不起来。

修改文件：

```text
backend/requirements.txt
```

原内容：

```text
Flask==3.0.3
PyMySQL==1.1.1
```

改为：

```text
Flask==3.0.3
Flask-CORS==6.0.5
PyMySQL==1.1.1
```

注意：

- 写 `Flask-CORS`（连字符）大小写保持一致，这是它在 PyPI 上的正式名字。
- 版本号要和你上一步实际安装的一致，用自己的版本号替换 `6.0.5`。

---

### 步骤 3：修改 `app/__init__.py` 配置 CORS

> **注意**：到这个阶段，`app/__init__.py` 里已经注册了好几个 Blueprint（博主、基金、初始持仓、操作记录、净值等）。**只加 `from flask_cors import CORS` 这行 import 和 `CORS(...)` 这段配置，其余内容一个字都不要动。** 步骤 4 之后的代码示例里用 `# ... 其他 blueprint 保持不变` 做了省略，那只是示例，不是让你删掉。

**必要性：**  
这是让配置生效的核心步骤。`flask-cors` 需要在 Flask 应用对象创建之后、处理请求之前挂载上去，`create_app()` 正好是这个位置。放在这里能保证所有接口都自动生效，不需要每个接口单独处理。

修改文件：

```text
backend/app/__init__.py
```

先看一下现在的文件长什么样：

```bash
cat app/__init__.py
```

里面现在应该已经注册了好几个 Blueprint（博主、基金、初始持仓、操作记录、净值等）。**下面做的是三处增量修改，不是整文件替换。**

**改动 1**：在文件顶部的 import 区域，加上这一行：

```python
from flask_cors import CORS
```

**改动 2**：在 `create_app()` 函数体里，`app = Flask(__name__)` 的**下一行**，加上这段配置：

```python
    CORS(
        app,
        resources={r"/*": {"origins": "http://localhost:5173"}},
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
        supports_credentials=False,
    )
```

**改动 3**：不动其他任何内容。所有 `app.register_blueprint(...)` 一行都保持原样。

改完之后，文件结构应该类似下面这样。**注意 `# ... 其他 Blueprint` 是省略标记，表示你原有的注册代码原样保留，不是让你照抄这一行：**

```python
from flask import Flask
from flask_cors import CORS          # ← 新增

from app.routes.health import health_bp
# ... 你原有的其他 import 保持不变


def create_app() -> Flask:
    app = Flask(__name__)

    CORS(                            # ← 新增
        app,
        resources={r"/*": {"origins": "http://localhost:5173"}},
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
        supports_credentials=False,
    )

    app.register_blueprint(health_bp)
    # ... 你原有的其他 register_blueprint 全部保持不变

    return app
```

**改完必须立刻确认没有误删**：

```bash
git diff app/__init__.py
```

预期 diff 里**只有**新增的行（`+` 开头），不应该有任何 `-` 开头的删除行。如果看到删除行，说明误删了原有代码，用 `git checkout app/__init__.py` 还原后重做。

代码中出现的新对象：

| 名称 | 说明 |
| --- | --- |
| `CORS` | `flask-cors` 提供的类，用来给 Flask 应用加上跨域支持 |
| `resources={r"/*": {...}}` | 一个字典，key 是路径匹配规则，value 是这个路径的跨域配置。`r"/*"` 表示**所有路径**都套用这套规则 |
| `"origins": "http://localhost:5173"` | 只允许这个源访问。来源不匹配时，浏览器会拦下响应 |
| `methods=[...]` | 允许哪些 HTTP 方法。这里必须包含 `OPTIONS`，否则预检请求过不去 |
| `allow_headers=["Content-Type"]` | 允许前端请求里带 `Content-Type` 头。前端发 JSON 请求体时必须带这个头 |
| `supports_credentials=False` | 不发送 cookie 凭据。第一版没有登录功能，不需要，关掉更安全 |

关于 `resources` 用 `r"/*"` 而不是 `r"/api/*"`：

如果用 `r"/api/*"`，那么**不在 `/api/` 开头的路径不会加跨域头**。现阶段我们只有 `/health` 这一个接口，它不以 `/api/` 开头，用那种写法做验证时会看到「没有跨域响应头」，从而误以为自己配错了。等后面接口都迁到 `/api/v1/` 下面，再考虑收窄到 `r"/api/*"`。

---

### 步骤 4：重启 Flask 服务

**必要性：**  
Python 代码改完后必须重启进程，否则验证的是旧代码，`pip` 装了新库也加载不进来。

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

注意看启动日志有没有报错。如果 `ImportError: cannot import name 'CORS'`，说明第 1 步没装成功。

---

## 验证方式

### 验证 1：普通请求带上了跨域头

另开一个 WSL 终端执行：

```bash
curl -i -H "Origin: http://localhost:5173" http://127.0.0.1:5000/health
```

`-i` 表示把响应头一起打印出来。

预期在响应头里看到：

```text
Access-Control-Allow-Origin: http://localhost:5173
```

响应体仍然是：

```json
{"code":0,"message":"ok","data":{"status":"ok"}}
```

**关键点**：必须带上 `-H "Origin: ..."`。不带 `Origin` 头的话，`flask-cors` 不会添加跨域响应头，这是正常行为，不要误判成配置失败。

---

### 验证 2：预检请求也正常

执行：

```bash
curl -i -X OPTIONS \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: Content-Type" \
  http://127.0.0.1:5000/health
```

预期看到三个响应头：

```text
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Methods: DELETE, GET, OPTIONS, POST, PUT
Access-Control-Allow-Headers: Content-Type
```

这一步**不能省**。它验证的是「后面写 PUT / DELETE 接口时浏览器会不会放行」。只看验证 1 的 GET 通过就往下走，到第 10 个任务写删除接口时会突然卡住。

---

### 验证 3：不在允许名单里的来源被拒绝

执行：

```bash
curl -i -H "Origin: http://evil.example.com" http://127.0.0.1:5000/health
```

预期**看不到** `Access-Control-Allow-Origin` 响应头。

这说明来源限制真的生效了，不是「所有来源都放行」。

---

## 常见坑

### 1. `/health` 明明没有跨域头，配错了吗？

先确认两件事：

第一，`resources` 是不是写成了 `r"/api/*"`。这样写，`/health` 不在匹配范围内，不会有跨域头。本任务要求写成 `r"/*"`。

第二，curl 有没有带 `Origin` 头。不带的话不会返回跨域头，这是 `flask-cors` 的正常行为。

排查命令：

```bash
curl -i -H "Origin: http://localhost:5173" http://127.0.0.1:5000/health
```

---

### 2. `ModuleNotFoundError: No module named 'flask_cors'`

三种可能：

1. 虚拟环境没激活。执行 `source .venv/bin/activate` 再试。
2. 装到了别的 Python 环境里。用 `which python` 确认当前用的是虚拟环境里的 Python。
3. 包没装成功。重新执行 `pip install flask-cors`。

排查命令：

```bash
which python
pip show flask-cors
```

---

### 3. `GET` 能过，`PUT` / `DELETE` 过不去

大概率是 `methods` 里漏了 `OPTIONS`。

浏览器发 `PUT` 之前会先发 `OPTIONS` 预检，服务器不认这个预检，真正的请求就不会发出去。

确认 `app/__init__.py` 里有：

```python
methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
```

用验证 2 的命令复测。

---

### 4. 来源写多了个尾斜杠

写成 `http://localhost:5173/`（末尾带斜杠）会导致匹配失败，浏览器仍然拦截。

正确写法**不带**末尾斜杠：

```python
"origins": "http://localhost:5173"
```

---

### 5. 前端还是报跨域错误，但 curl 明明通过

先确认前端实际跑的地址是不是 `http://localhost:5173`。

Vite 有时候会因为端口被占用自动换成 `5174` 或其他端口，这时前端的源就变了，而后端只允许 `5173`。

在前端项目目录执行：

```bash
npm run dev
```

看终端输出的 `Local:` 那一行到底是多少端口。如果不一致，反馈给后端协调人，不要自己改 `origins`。

---

## 完成标准

以下条件全部满足，任务 041 才算完成：

1. `requirements.txt` 里有 `Flask-CORS`，版本号与实际安装的一致。
2. `app/__init__.py` 里配置了 `CORS`，且 `resources` 是 `r"/*"`。
3. `methods` 列表中包含 `OPTIONS`。
4. 验证 1、验证 2、验证 3 三条命令的输出与文档描述一致。
5. `/health` 接口的返回内容没有变化。

---

## 完成后请反馈

请把下面命令的输出发给后端协调人：

```bash
cat requirements.txt
cat app/__init__.py
curl -i -H "Origin: http://localhost:5173" http://127.0.0.1:5000/health
curl -i -X OPTIONS \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: Content-Type" \
  http://127.0.0.1:5000/health
```

另外请说明：前端 `npm run dev` 输出的 `Local:` 地址实际是多少端口。

任务 041 验收通过后，进入任务 042：注册全局错误处理器。
