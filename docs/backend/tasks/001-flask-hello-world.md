# 任务 001：搭建 Flask 环境并跑通 Hello World

## 任务目标

完成第一版后端开发环境初始化，并跑通一个最小 Flask 服务。完成后，你可以在本机通过浏览器或 `curl` 访问：

```text
http://127.0.0.1:5000/health
```

并看到：

```json
{"code":0,"message":"ok","data":{"status":"ok"}}
```

这个任务不连接数据库，不实现业务接口，只验证 Flask 环境可用。

---

## 前置条件

1. 已进入项目根目录：`/mnt/d/people/find_gold`
2. 已安装 WSL Ubuntu。
3. 已安装 Python 3.10 或更高版本。
4. 已阅读以下文档：
   - `AGENTS.md`
   - `docs/requirements/v1-basic-management.md`
   - `docs/api/v1-basic-management.md`

---

## 执行目录约定

下面的命令默认都在 WSL 中执行。

如果你已经在 WSL 终端里，进入项目后端目录：

```bash
cd /mnt/d/people/find_gold/backend
```

如果你在 Windows 终端里，可以统一使用这种形式：

```bash
wsl bash -lc "cd /mnt/d/people/find_gold/backend && python3 --version"
```

---

## 具体步骤

### 1. 确认 Python 版本

在 WSL 中执行：

```bash
cd /mnt/d/people/find_gold/backend
python3 --version
```

预期输出类似：

```text
Python 3.10.12
```

只要版本号是 `3.10` 或更高即可。

---

### 2. 创建 Python 虚拟环境

在 `/mnt/d/people/find_gold/backend` 下执行：

```bash
python3 -m venv .venv
```

这条命令会创建一个 `.venv` 目录，用来隔离本项目依赖。

创建完成后检查目录：

```bash
ls -la
```

你应该能看到：

```text
.venv
```

---

### 3. 激活虚拟环境

执行：

```bash
source .venv/bin/activate
```

激活成功后，终端提示符前会出现：

```text
(.venv)
```

以后每次重新打开终端，进入 `/mnt/d/people/find_gold/backend` 后都要先执行：

```bash
source .venv/bin/activate
```

---

### 4. 创建依赖文件

新建文件：

```text
backend/requirements.txt
```

文件内容写入：

```text
Flask==3.0.3
```

可以用编辑器创建，也可以在 WSL 中执行：

```bash
touch requirements.txt
```

然后用编辑器打开并写入内容。

---

### 5. 安装 Flask

在虚拟环境激活状态下执行：

```bash
pip install -r requirements.txt
```

安装完成后验证 Flask 是否可用：

```bash
python -c "import flask; print(flask.__version__)"
```

预期输出：

```text
3.0.3
```

---

### 6. 创建最小 Flask 应用

在 `backend` 目录下新建目录：

```bash
mkdir app
```

然后新建文件：

```text
backend/app/__init__.py
```

文件内容写入：

```python
from flask import Flask, jsonify


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
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

    return app
```

再新建文件：

```text
backend/run.py
```

文件内容写入：

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

### 7. 启动 Flask 服务

确认你在：

```bash
cd /mnt/d/people/find_gold/backend
```

并且虚拟环境已激活：

```bash
source .venv/bin/activate
```

然后执行：

```bash
python run.py
```

预期输出类似：

```text
 * Serving Flask app 'run'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

---

## 验证方式

服务启动后，不要关闭当前终端。

另开一个 WSL 终端，执行：

```bash
curl http://127.0.0.1:5000/health
```

预期输出：

```json
{"code":0,"message":"ok","data":{"status":"ok"}}
```

也可以在浏览器访问：

```text
http://127.0.0.1:5000/health
```

---

## 常见坑

### 1. 命令跑到了 Windows 里

如果你看到类似 `python3: command not found`、路径显示为 `C:\...`、或者 `cd /mnt/d/people/find_gold/backend` 不成功，先确认你是在 WSL 终端里执行命令。

可以执行：

```bash
pwd
```

预期输出：

```text
/mnt/d/people/find_gold/backend
```

---

### 2. 虚拟环境没有激活

如果你执行 `pip install` 时安装到了全局 Python，或者看不到终端前缀 `(.venv)`，说明虚拟环境没有激活。

回到后端目录执行：

```bash
source .venv/bin/activate
```

---

### 3. 端口被占用

如果启动时报错类似：

```text
Address already in use
```

说明 `5000` 端口被占用。先不要急着改端口，可以先查找占用进程：

```bash
lsof -i:5000
```

如果确认不是重要服务，可以结束对应进程，或者临时把 `run.py` 里的 `port=5000` 改成 `port=5001`，并用新端口验证。

---

### 4. `ModuleNotFoundError: No module named 'flask'`

通常是虚拟环境没有激活，或者 Flask 没有安装成功。

先确认虚拟环境已激活：

```bash
source .venv/bin/activate
```

然后重新安装：

```bash
pip install -r requirements.txt
```

---

### 5. `ModuleNotFoundError: No module named 'app'`

通常是启动位置不对。必须保证你在 `backend` 目录下执行：

```bash
cd /mnt/d/people/find_gold/backend
python run.py
```

不要在项目根目录 `/mnt/d/people/find_gold` 执行，也不要在 `app` 目录内部执行。

---

## 完成标准

以下三项全部通过，本任务才算完成：

1. `python3 --version` 显示 3.10 或更高版本。
2. Flask 服务能正常启动。
3. `curl http://127.0.0.1:5000/health` 能返回统一 JSON 结构。

---

## 完成后请反馈

完成后，把下面信息发给我：

```bash
python3 --version
python -c "import flask; print(flask.__version__)"
curl http://127.0.0.1:5000/health
```

我会根据你的反馈确认任务 001 是否通过，然后再给任务 002：项目结构拆分和统一响应函数。
