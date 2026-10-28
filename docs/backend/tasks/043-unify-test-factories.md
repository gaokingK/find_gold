# 任务 043：统一测试工厂函数的用法

> **批次说明**：本任务属于 040 之后的补发批次。001–040 里对「测试里怎么造数据」给出了三种互相冲突的写法，现在统一成一种。本任务只改测试代码，不动业务代码。

## 预计完成时间

预计完成时间：约 1.5 小时。

估算依据：本任务不新增测试用例、不新增依赖、不改数据库，只是把已经存在的辅助函数搬到一个文件里、改几行 import、修一处笔误；代码量很小。时间主要花在三件事上：① 搞清楚 `pytest` 的 fixture（夹具）和普通函数的区别（这是本任务唯一的新概念，也是之前写错的原因）；② 逐个测试文件核对「删掉本地定义后默认值有没有变」；③ 跑全量测试确认没有回归。

## 任务目标

把项目里「造测试数据的辅助函数」统一成**一种写法**：

1. 所有造数据的辅助函数只在 `backend/tests/factories.py` 一处定义，其他测试文件不得再定义。
2. 测试文件统一用 `from factories import create_blogger, create_fund, ...` 导入后再调用。
3. 不把工厂函数当 pytest fixture 传参。

完成后，下面第三条命令**没有任何输出**，并且 `pytest -q` 全绿：

```bash
grep -rn "def create_blogger\|def create_fund\|def create_initial_position\|def create_operation" tests/
grep -rn "def test_.*create_fund\|def test_.*create_blogger" tests/
```

第一条只在 `tests/factories.py` 里出现定义；第二条必须为空。

---

## 范围说明

本任务只整理**测试代码**。

包含：

- `backend/tests/factories.py`
- `backend/tests/test_initial_positions.py`
- `backend/tests/test_operations.py`
- `backend/tests/test_position_snapshots.py`
- `backend/tests/test_nav_history.py`

不包含：

- 任何 `app/` 下的业务代码
- 数据库表结构
- 接口文档（`docs/api/` 下的 6 份文档）
- 已有的任务文档 001–042（发现它们和本任务口径冲突时，反馈，不要自己改）
- 新增测试用例（本任务不要求补新场景，除非迁移过程中发现某个测试原本就跑不起来）

---

## 前置条件

1. 任务 014、015 已完成，`pytest -q` 能跑起来，`client` 和 `clean_db` 两个 fixture 可用。
2. 任务 016、017、022、028、032 都已下发并执行过。
3. 你知道自己的 `backend` 目录在哪（本任务按 `/mnt/d/people/find_gold/backend` 写）。

---

## 为什么必须做这一步

现在项目里造测试数据的写法有**三种**，而且它们互相冲突：

| 编号 | 出处 | 写法 | 状态 |
| --- | --- | --- | --- |
| 1 | `022-delete-operation-and-tests.md` 步骤 7 | `from factories import create_blogger, create_fund` | **正确**，本任务要统一成这种 |
| 2 | `028-nav-history-csv-import-api.md` 步骤 5、6 | `def test_...(client, create_fund)` | **笔误**，`create_fund` 被当成 fixture 传参 |
| 3 | `032-position-snapshot-tests.md` 步骤 1 | 在 `test_position_snapshots.py` 里重新写了 `create_blogger` / `create_fund` / `create_initial_position` / `create_operation` | **违反** 016、017 的完成标准 |

逐条说明后果：

**关于第 2 种（028 的笔误）**：
`create_fund` 是 `tests/factories.py` 里的一个**普通函数**，不是 fixture。把它写在测试函数的参数里，pytest 会去找一个叫 `create_fund` 的 fixture，找不到，报错：

```text
fixture 'create_fund' not found
```

关键点是：**这个错误在 pytest 里计作 `error`，不是 `failed`**。原因在下面「常见坑 2」里讲。后果是：新手看到 `error` 会往环境方向排查（是不是没装 pytest？是不是路径不对？是不是数据库没起来？），而真正的原因只是参数列表里多写了一个词。同一份 028 文档里 `test_import_nav_history_csv_rejects_unknown_fund_code(client)` 又没带这个参数，这可以确认确实是笔误，不是某种新写法。

**关于第 3 种（032 的重复定义）**：
`016-blogger-module-api-tests.md` 完成标准第 8 条和 `017-fund-and-initial-position-api-tests.md` 完成标准第 5 条都明确要求：

```bash
grep -rn "def create_blogger\|def create_fund" tests/
```

全项目只有 `tests/factories.py` 一处定义。032 为了写快照测试，把这四个函数原样复制进了 `test_position_snapshots.py`，这两条完成标准就失效了。实际危害是：以后 `POST /api/v1/funds` 加一个必填字段，你得去改好几个文件里的 `create_fund`，漏改一处就是一连串莫名其妙的失败。

---

## 新概念（本任务的核心，请整节读完）

### 概念 1：factory function（工厂函数）

工厂函数就是「负责造一个东西并返回它」的普通函数。

我们项目里的 `create_blogger(client, name="测试博主")` 就是一个工厂函数：它发一次 `POST /api/v1/bloggers`，断言创建成功，然后把响应的 `data` 返回给你。

它**就是一个普通 Python 函数**，没有任何特殊身份。要调用它，必须先 import，然后像调用别的函数一样传参：

```python
from factories import create_blogger

def test_xxx(client):
    blogger = create_blogger(client, name="张三")
```

### 概念 2：fixture（夹具）

fixture 是 pytest 提供的机制，中文一般叫「夹具」或「固定装置」。

它的作用是：**在测试运行前准备好某个东西，用完自动收尾**。比如我们项目里的 `client`（Flask 测试客户端）和 `clean_db`（每个测试前清空测试库）。

fixture 长这样——注意那个 `@pytest.fixture`：

```python
import pytest

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
```

`@pytest.fixture` 是一个**装饰器（Decorator）**。装饰器的英文是 Decorator，作用是「给一个函数套上一层额外行为，而不用改函数内部的代码」。这里它做的事是：**把 `client` 这个函数登记到 pytest 的 fixture 名单里**。

登记之后，pytest 允许你这样用：

```python
def test_xxx(client):        # ← 不 import，不调用，只写名字
    response = client.get("/api/v1/bloggers")
```

pytest 看到参数名叫 `client`，去名单里一查，找到了，就**自动调用 `client()` 并把返回值塞进来**。这叫「按名字自动注入」。

**这是本任务最关键的一句话：**

> **只有被 `@pytest.fixture` 装饰过的函数，才能靠「把函数名写进测试参数」的方式自动拿到。普通函数不行。**

`create_fund` 没有 `@pytest.fixture`，所以 `def test_xxx(client, create_fund)` 必然报错。

两种写法对照：

| | fixture | 普通工厂函数 |
| --- | --- | --- |
| 定义处 | `conftest.py` 或测试文件里，带 `@pytest.fixture` | `tests/factories.py` |
| 怎么拿到 | 把函数名写进测试参数 | `from factories import ...` 后手动调用 |
| 调用时传参 | 不能传，pytest 自己调 | 由你传，例如 `create_fund(client, fund_code="F001")` |
| 例子 | `client`、`clean_db` | `create_blogger`、`create_fund` |

为什么工厂函数不做成 fixture？因为我们需要**给它传不同的参数**——同一个测试里要建两只基金，代码不同名也不同。fixture 是 pytest 调的，你没法在调用时传 `fund_code="SNAP000002"`。所以造数据的活交给普通函数更合适。

### fixture 放在哪里：`conftest.py`

这仍是 fixture 机制的一部分，不是独立的新概念。`conftest.py` 是 pytest 约定俗成的一个特殊文件名。

pytest 启动时会自动加载它，不需要任何 import。它的用途是放**多个测试文件共用的 fixture**。我们项目里 `client` 和 `clean_db` 就放在 `backend/tests/conftest.py`。

与之相对，`factories.py` 是**我们自己起的名字**，pytest 不认识它，所以必须显式 `import`。这就是两个文件用法不一样的原因。

---

## 统一后的口径（本任务以此为准）

1. 造数据的辅助函数（`create_blogger`、`create_fund`、`create_initial_position`、`create_operation`、`create_nav_history` 等）**只在 `backend/tests/factories.py` 定义**，其他测试文件不得再定义同名函数。
2. 测试文件统一 `from factories import ...`，然后手动调用。不要写成 `from tests.factories import ...`（`tests` 目录没有 `__init__.py`，那样写会报 `ModuleNotFoundError`）。
3. **不要把工厂函数当 fixture 传参**。测试函数的参数只能是真正的 fixture（`client`，以及你在 `conftest.py` 里自己注册的那些）。

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

### 步骤 1：先看清 `factories.py` 和 `conftest.py` 现在长什么样

**必要性：**  
016、017 文档里写的 `create_fund()` 签名，和你磁盘上真实的 `factories.py` 可能不一样（中间可能被后续任务改过）。本任务所有改动都以**磁盘上的实际内容**为准——如果实际签名和本文档示例不同，按实际文件调整，不要照抄本文档去覆盖你已经在用的版本。不先看就动手，很容易把能跑的工厂函数改坏。

执行：

```bash
cat tests/conftest.py
cat tests/factories.py
ls tests/
```

请重点确认三件事，并记下来（后面几步要用）：

1. `factories.py` 里现在有哪些函数，各自的参数名和默认值是什么。特别是 `create_fund()` 是 `(client, name=..., fund_code=...)` 还是别的。
2. `conftest.py` 里哪些函数带了 `@pytest.fixture`（这些才是可以在测试参数里写的名字）。
3. `tests/` 下有哪些 `test_*.py` 文件。

如果 `factories.py` 不存在，说明任务 016 没做完，先回去补 016，不要在别处另起一份。

---

### 步骤 2：列出所有重复的工厂函数定义

**必要性：**  
先拿到完整的「待处理清单」，再动手改。凭印象改一定会有漏网的，而漏一个就完不成标准里的 grep 检查。

执行：

```bash
grep -rn "def create_blogger\|def create_fund\|def create_initial_position\|def create_operation" tests/
```

预期现在能看到**不止一处**（至少 `factories.py` 和 `test_position_snapshots.py`，可能还有 `test_initial_positions.py`、`test_operations.py`）。把每一行的「文件路径 + 行号」记下来。

再查一遍被当成 fixture 传参的写法：

```bash
grep -rn "def test_.*create_fund\|def test_.*create_blogger" tests/
```

预期至少命中 `tests/test_nav_history.py` 里的两行（028 留下的笔误）。同样记下来。

---

### 步骤 3：把 `create_initial_position` 和 `create_operation` 补进 `factories.py`

**必要性：**  
统一口径要求这两个函数也只在一处定义。它们现在分散在 `test_initial_positions.py`（017 步骤 4 允许写在文件里）、`test_operations.py`（022 步骤 7）、`test_position_snapshots.py`（032 步骤 1）三处。先把「公共版本」放进 `factories.py`，后面三个文件才能改成 import。

修改文件（已存在，是修改不是新建）：

```text
backend/tests/factories.py
```

在文件末尾追加：

```python
def create_initial_position(
    client,
    blogger_id,
    fund_id,
    shares=12000,
    cost_amount=15600,
    record_date="2020-01-01"
):
    response = client.post(
        "/api/v1/initial-positions",
        json={
            "blogger_id": blogger_id,
            "fund_id": fund_id,
            "shares": shares,
            "cost_amount": cost_amount,
            "record_date": record_date
        }
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    return body["data"]


def create_operation(
    client,
    blogger_id,
    fund_id,
    operation_type="buy",
    operation_date="2020-01-02",
    shares=100,
    amount=1300,
    remark=None
):
    payload = {
        "blogger_id": blogger_id,
        "fund_id": fund_id,
        "operation_type": operation_type,
        "operation_date": operation_date,
        "amount": amount
    }

    if shares is not None:
        payload["shares"] = shares

    if remark is not None:
        payload["remark"] = remark

    response = client.post("/api/v1/operations", json=payload)
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    return body["data"]
```

说明：

- `create_operation` 里的 `shares=None` 表示「整个字段都不传」（测现金分红场景用），这和 `shares=0` 不是一回事——`0` 会被真的传出去。
- `operation_type` 给了默认值 `"buy"`。032 里的版本没有默认值（必传），022 里的版本有默认值。给默认值后两种调用方式都能跑，所以取有默认值的这一个。
- `record_date` 默认值取 `"2020-01-01"`（017 版本）。032 版本默认是 `"2026-01-01"`。如果步骤 6 迁移后有测试因为「操作日期早于初始持仓日期」报 400，把这里的默认值改成 `"2026-01-01"`，并在反馈里说明。
- 如果 `factories.py` 里**已经有**同名函数，不要重复添加，直接跳到下一步改调用方。

---

### 步骤 4：改造 `test_initial_positions.py`

**必要性：**  
这个文件里有一份本地的 `create_initial_position`（017 步骤 4 写的）。留着它，`grep` 就永远多一处定义，而且以后初始持仓接口加字段要改两处。

修改文件：

```text
backend/tests/test_initial_positions.py
```

做两处改动：

1. **删掉**文件里 `def create_initial_position(...)` 整段定义。
2. 把顶部的导入改成（在原有 `from factories import create_blogger, create_fund` 基础上补一个）：

```python
from factories import create_blogger, create_fund, create_initial_position
```

文件里所有 `create_initial_position(...)` 的调用**一行都不用改**——导入进来后，调用方式和本地定义时完全一样。

改完立刻验证这一处：

```bash
pytest tests/test_initial_positions.py -q
```

预期全部通过。如果报 `NameError: name 'create_initial_position' is not defined`，说明 import 拼错了。

---

### 步骤 5：改造 `test_operations.py`

**必要性：**  
同步骤 4。022 步骤 7 在文件里定义了 `create_operation`，现在统一搬走。

修改文件：

```text
backend/tests/test_operations.py
```

做两处改动：

1. **删掉**文件里 `def create_operation(...)` 整段定义。
2. 顶部导入改为：

```python
from factories import create_blogger, create_fund, create_operation
```

然后专项跑一次：

```bash
pytest tests/test_operations.py -q
```

预期全部通过。

这一组测试里有 18 个用例，是本项目目前最密的一组。如果这里出现 `failed`（注意不是 `error`），大概率是步骤 3 的默认值和你原来的本地版本不一致，回去对照 `git diff` 看改了什么。

---

### 步骤 6：改造 `test_position_snapshots.py`

**必要性：**  
这是三处里唯一一处**重复定义了 `create_blogger` 和 `create_fund`** 的文件，直接违反 016 完成标准第 8 条和 017 完成标准第 5 条，是本任务必须清掉的重点。

修改文件：

```text
backend/tests/test_position_snapshots.py
```

做两处改动：

1. **删掉**文件里 `def create_blogger(...)`、`def create_fund(...)`、`def create_initial_position(...)`、`def create_operation(...)` 四段定义。
2. 在文件顶部加上：

```python
from factories import (
    create_blogger,
    create_fund,
    create_initial_position,
    create_operation,
)
```

**注意 `get_snapshot()` 要保留**：它不是造数据的工厂函数，只是拼 URL 的小工具，只有本文件用，留在文件里即可。本任务只搬「造数据」的函数。

改完专项跑一次：

```bash
pytest tests/test_position_snapshots.py -q
```

预期全部通过。这里最容易踩的坑见「常见坑 3」：默认参数变了导致同名/同代码冲突。

---

### 步骤 7：修掉 `test_nav_history.py` 里把工厂函数当 fixture 的笔误

**必要性：**  
028 步骤 5、6 的两个测试写成了 `def test_...(client, create_fund)`。`create_fund` 不是 fixture，pytest 会报 `fixture 'create_fund' not found` 且计作 `error`，这两个测试从来就没真正跑过——也就是说净值 CSV 导入接口目前**没有测试在守护**。这是本任务最实际的一个收益。

修改文件：

```text
backend/tests/test_nav_history.py
```

做两处改动：

1. 在文件顶部加上导入：

```python
from factories import create_fund
```

2. 把这两个测试的参数列表里的 `, create_fund` 删掉：

```python
def test_import_nav_history_csv_success(client, create_fund):        # ← 改前
def test_import_nav_history_csv_success(client):                     # ← 改后

def test_import_nav_history_csv_rejects_invalid_row(client, create_fund):   # ← 改前
def test_import_nav_history_csv_rejects_invalid_row(client):                # ← 改后
```

函数体里 `create_fund(client, name=..., fund_code=...)` 的调用**保持不变**——它现在是普通函数调用，正常。

第三个测试 `test_import_nav_history_csv_rejects_unknown_fund_code(client)` 本来就没带这个参数，不用改。

改完专项跑一次：

```bash
pytest tests/test_nav_history.py -q
```

**这一步之前，这两个测试是 `error`；改完后它们会真正开始执行。** 有可能出现新的 `failed`——那说明净值导入接口有真实缺陷被暴露出来了（测试之前根本没跑，所以没人发现）。这属于正常且有价值的结果，请把它记下来反馈，不要靠放宽断言让它变绿。

---

### 步骤 8：跑全量测试并做三条自查

**必要性：**  
前面每一步都只跑了单个文件。工厂函数是全项目共用的，必须确认「所有测试放在一起跑」也没有问题——尤其是 `clean_db` 清空的表有没有覆盖到 `nav_history`、有没有测试因为迁移后行为变化而互相影响。

执行：

```bash
pytest -q
```

预期：**没有 failed，也没有 error**。测试总数应该和迁移前**一样**（本任务不新增、不删除用例）。

然后跑三条自查命令：

```bash
grep -rn "def create_blogger\|def create_fund\|def create_initial_position\|def create_operation" tests/
```

预期：若干行输出，**全部来自 `tests/factories.py`**。

```bash
grep -rn "def test_.*create_fund\|def test_.*create_blogger" tests/
```

预期：**没有任何输出**。

```bash
grep -rn "from factories import" tests/
```

预期：每个用到工厂函数的测试文件都有一行，且都是 `from factories import ...`，没有 `from tests.factories import ...`。

---

## 验证方式

### 验证 1：定义唯一性

```bash
grep -rn "def create_blogger\|def create_fund\|def create_initial_position\|def create_operation" tests/
```

预期输出的每一行，文件路径都是 `tests/factories.py`。

如果 `test_position_snapshots.py` 或其他测试文件里还有命中，说明步骤 4–6 有漏删，回去补。

---

### 验证 2：没有把工厂函数当 fixture 传参

```bash
grep -rn "def test_.*create_fund\|def test_.*create_blogger" tests/
```

预期为空（没有任何输出，退出码为 1 是正常的）。

这条是本任务的最终防线：只要有人再写出 `def test_xxx(client, create_fund)`，这条命令立刻能抓到。

---

### 验证 3：每个测试文件的工厂函数都有来源

```bash
for f in tests/test_*.py; do echo "--- $f"; grep -n "from factories import" "$f"; done
```

预期：用到 `create_*` 的文件都有对应 import，没用到的没有。

---

### 验证 4：全量测试

```bash
pytest -q
```

预期最后一行类似：

```text
44 passed in 3.21s
```

具体数字以你环境为准，重点是 **没有 failed，也没有 error**。

---

## 常见坑

### 1. `fixture 'create_fund' not found`（本任务最核心的坑）

报错原文大致是：

```text
E   fixture 'create_fund' not found
>   available fixtures: cache, capfd, ..., client, clean_db, ...
```

含义：pytest 在你写的参数名里找不到对应的 fixture。

原因只有一个：`create_fund` 是普通函数，不是 fixture。修法是二选一：

- 删掉测试参数里的 `, create_fund`，并在文件顶部 `from factories import create_fund`（**本任务采用这种**）；
- 或者真的把它做成 fixture（本项目不采用，理由见「新概念」概念 2 末段）。

顺带一提，报错信息里那行 `available fixtures: ...` 很有用——**那就是当前可用的 fixture 名单**。名单里有的才能写进测试参数，`client`、`clean_db` 在里面，`create_fund` 不在。

---

### 2. 看到 `errors` 就往环境方向排查

pytest 结尾的统计行有两种：

```text
2 failed, 40 passed          ← 断言没过，测试跑了
2 errors, 40 passed          ← 测试没跑起来
```

两种状态的区别：

| | `failed`（失败） | `error`（错误） |
| --- | --- | --- |
| 含义 | 测试**跑起来了**，但某条 `assert` 不成立 | 测试**根本没跑起来**，在准备阶段就出错了 |
| 输出符号 | `F` | `E` |
| 结尾统计 | `N failed` | `N errors` |
| 常见原因 | 接口返回的业务数据不对；断言写错了 | fixture 名字找不到；import 失败；测试文件语法错误；数据库连接不上 |
| 排查方向 | 看断言那一行，对比接口文档 | 看「为什么这个测试没被执行」，通常是签名、import、环境 |

看到 `errors` 时，**记住这条排查顺序**，先按它查：

1. 测试函数的参数列表里，有没有不是 fixture 的名字（坑 1）。
2. 文件顶部的 import 有没有写错（比如 `from tests.factories import ...`）。
3. 测试文件本身有没有语法错误：`python -m py_compile tests/test_nav_history.py`。
4. 最后才查数据库、虚拟环境、依赖。

`fixture 'create_fund' not found` 属于第 1 类：pytest 在**准备阶段**解析测试函数的参数列表，发现 `create_fund` 不在 fixture 名单里，就直接放弃这个测试——测试函数体一行都没执行，所以计作 `error` 而不是 `failed`，和数据库一点关系都没有。

---

### 3. 迁移后默认值变了，导致「名称重复」或「代码重复」

`factories.py` 里的 `create_blogger()` 默认名字是 `"测试博主"`、`create_fund()` 默认代码是 `"TEST001"`；而 032 里自己定义的默认值是 `"快照博主"` / `"SNAP000001"`。

删掉本地定义后，如果某个测试里有**两处**没传 `name` 或没传 `fund_code` 的调用，就会撞上 `BLOGGER_NAME_DUPLICATED` 或 `FUND_CODE_DUPLICATED`。

排查：

```bash
grep -n "create_blogger(client)\|create_fund(client)" tests/test_position_snapshots.py
```

修法：给这些调用补上显式的 `name=` / `fund_code=`，**不要**去改 `factories.py` 的默认值（那会影响 016、017 的测试）。

反过来也提醒一件事：`clean_db` 只在**每个测试开始前**清空一次。同一个测试函数里建两只基金用同一个代码，一样会撞车。

---

### 4. 写成 `from tests.factories import ...`

会报：

```text
ModuleNotFoundError: No module named 'tests'
```

原因：`backend/tests/` 目录下**没有** `__init__.py`，`tests` 不是一个 Python 包。pytest 会把 `tests` 目录本身加进模块搜索路径，所以正确写法是：

```python
from factories import create_blogger
```

检查命令：

```bash
grep -rn "from tests" tests/
```

预期没有输出。

---

### 5. 删定义时删多了，或删少了

删工厂函数时容易连带删掉后面的测试函数，或者漏掉某一段。

每一步改完都用 `git diff` 自查：

```bash
git diff tests/test_position_snapshots.py
```

预期看到的**只有 `-` 开头的删除行**（四段 `def create_*` 加上一段 import 新增）。如果 diff 里出现了 `def test_` 开头的删除行，说明删多了，用 `git checkout tests/test_position_snapshots.py` 还原重做。

---

### 6. 顺手去改业务代码或改 016、017 文档

迁移过程中如果发现「`create_operation` 在 022 和 032 里行为不一样」，那确实是个不一致，但**不要在本任务里顺手合并它们的业务语义**，也不要去改 016、017 的完成标准条文。把它们记进「完成后请反馈」，由协调人决定。

本任务的验收标准只有一条主线：定义唯一 + 导入正确 + 全量测试通过。

---

### 7. 想把所有 fixture 也搬进 `factories.py`

不要。`conftest.py` 和 `factories.py` 的分工是：

- `conftest.py`：放 fixture（`@pytest.fixture`），pytest 自动加载，不需要 import。
- `factories.py`：放普通工厂函数，需要 import。

把 fixture 搬进 `factories.py` 会失效——pytest 不会自动加载那个文件，`client` 就找不到了，所有测试一起 `error`。

---

## 完成标准

以下条件全部满足，任务 043 才算完成：

- [ ] `tests/factories.py` 是 `create_blogger`、`create_fund`、`create_initial_position`、`create_operation` 的**唯一**定义处。
- [ ] `grep -rn "def create_blogger\|def create_fund\|def create_initial_position\|def create_operation" tests/` 的输出全部来自 `tests/factories.py`。
- [ ] `grep -rn "def test_.*create_fund\|def test_.*create_blogger" tests/` 没有任何输出。
- [ ] `test_initial_positions.py`、`test_operations.py`、`test_position_snapshots.py` 都改为从 `factories` 导入，文件内没有本地定义。
- [ ] `test_nav_history.py` 的两个测试去掉了 `create_fund` 参数，并加上 `from factories import create_fund`。
- [ ] 没有出现 `from tests.factories import ...` 这种写法。
- [ ] `pytest -q` 全部通过，**没有 failed 也没有 error**。
- [ ] 测试总数与迁移前一致（本任务不新增、不删除用例）。
- [ ] 没有修改 `app/` 下任何业务代码，也没有修改 001–042 任何任务文档。

---

## 完成后请反馈

请把下面命令的输出发给后端协调人：

```bash
cat tests/factories.py
cat tests/conftest.py
grep -rn "def create_blogger\|def create_fund\|def create_initial_position\|def create_operation" tests/
grep -rn "def test_.*create_fund\|def test_.*create_blogger" tests/
pytest -q
```

另外请说明：

1. 迁移前后测试总数各是多少（确认没有用例丢失）。
2. 步骤 7 修完 028 的笔误后，`tests/test_nav_history.py` 的两个测试是**通过**还是暴露出了新的失败？如果是后者，把失败断言原文贴出来——那说明净值导入接口有真实问题，需要单独开任务修。
3. 步骤 3 里 `create_initial_position` 的 `record_date` 默认值最终用的是 `2020-01-01` 还是 `2026-01-01`，为什么。
4. 有没有发现 016、017、022、028、032 里还有别的写法不一致（不限于工厂函数）。

任务 043 验收通过后，进入任务 044：实现净值列表查询接口。
