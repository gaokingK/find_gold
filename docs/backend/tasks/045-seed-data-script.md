# 任务 045：开发库演示数据脚本（seed data）

> **批次说明**：本任务属于 040 之后的补发批次，编号从 041 起，与 041（CORS）、042（全局错误处理器）、043（统一测试工厂函数）并列。做之前不需要改任何已有代码。

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：只新增一个数据库写入脚本 `backend/scripts/seed_data.py`（约 180 行），不写接口、不改表结构、不加依赖。工作量两处：把五张表的固定数据按外键顺序写进脚本（约 30 分钟），跑通「重复执行 + MySQL 行数核对 + 四组接口请求的期望值逐值核对 + 测试库守卫验证」（约 70 分钟）。接口期望值那一组最花时间——快照、收益、缺净值对照组的每个数字都要手算比对。数据库操作和 SQL 写法在 007、019、025 里都练过，本次只是换成 `INSERT`；两个新东西是「seed data 的定位」和 `INSERT ... ON DUPLICATE KEY UPDATE`。合计定 2 小时。

---

## 任务目标

新建 `backend/scripts/seed_data.py`，往**开发库 `fund_db`** 写入一批**固定的**演示数据：3 个博主、4 只基金、5 条初始持仓、8 条操作记录、119 条净值。

写完之后：`python -m scripts.seed_data` 成功结束；再执行一次仍然成功、不报唯一约束错误；这批数据的**主键 ID 固定**，不随执行次数变化；`034`–`038`、`040` 六份文档的验证命令可以直接引用这些固定 ID；`fund_test_db` 一行都没被写入；`pytest -q` 仍然全部通过。

---

## 范围说明

只做一个**往开发库写演示数据的脚本**。不包含：修改任何已有代码或任务文档；修改 `tests/conftest.py`、`tests/factories.py`；往 `fund_test_db` 写数据；改表结构；新增接口；数据库迁移工具；删除或清空数据的「反向脚本」；前端改动。

**seed 与 factory 的分工**：seed（本任务）写死在 `scripts/seed_data.py`，进开发库 `fund_db`，长期留在库里给开发、联调、验收、演示用；factory（工厂函数，在 `tests/factories.py`）按用例需要在测试库 `fund_test_db` 里临时造数据，每个测试前被 `clean_db` 夹具 TRUNCATE 清空。测试要用数据就调工厂函数自己造，不要依赖 seed。

---

## 前置条件

1. 任务 028 已完成：`nav_history` 表能写入数据。
2. 任务 007、019、025 已完成：五张表都已建好。
3. `python -m scripts.check_db` 能连上 MySQL。
4. 环境变量已设置（`DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`）。数据库密码只通过环境变量传入，不要写进任何文件。
5. `pytest -q` 当前全部通过。

---

## 为什么必须做这一步

`034`–`038`、`040` 的「验证方式」里反复写着「如果没有 ID 为 1 的博主，可以换成实际存在的博主 ID」。后果是这些接口的验收标准实际上失效了：验收入要现场手工凑数据，每次凑的都不一样，同一个 bug 今天能复现明天复现不了；而「缺净值返回 `null`」「同一基金多条初始持仓只取最早一条」「超额卖出份额为负」「同一天多笔操作的计算顺序」这几条都需要**特定形状**的数据，手工凑几乎不会刚好凑出来，一直处于「代码写了但没人验证过」的状态。本任务把演示数据固化成可重复执行的脚本：ID、日期、金额全是常量，跑一次和跑十次数据库状态完全一样，这几条规则就有了可复现、可核对的验收依据。

---

## 新概念说明

### 概念 1：seed data（种子数据）

seed data 中文叫**种子数据**，也有人叫「演示数据」「初始化数据」，指**一批写死在脚本里、用于开发和演示的示例数据**。三个特点：固定不变（ID、日期、金额都是常量）；可重复执行（跑第二次不报错，数据库回到同一状态）；面向人（开发、联调、验收、演示看界面用）。它和 007 写的 `scripts/init_db.py` 是同一类脚本，区别是 `init_db.py` 建**表结构**，`seed_data.py` 填**表数据**。

### 概念 2：`INSERT ... ON DUPLICATE KEY UPDATE`

MySQL 扩展的 `INSERT` 语句，中文叫「有重复就更新」，业界常叫 **Upsert**（Update + Insert 的合成词）。作用是**插入一行；如果这行违反唯一约束，就改成更新这行，而不是报错。**

```sql
INSERT INTO funds (id, name, fund_code)
VALUES (101, '演示成长混合A', 'DEMO0001')
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    fund_code = VALUES(fund_code)
```

第一次执行没有 `id = 101` → 正常插入；第二次 `id = 101` 已存在 → 不报 `Duplicate entry`，改成更新 `name`、`fund_code`。`VALUES(name)` 指「这条 INSERT 原本想写进去的那个 `name` 值」，同一个值不用写第二遍。

**为什么必须用它**：seed 脚本肯定会被重复执行，用裸 `INSERT` 第二次就报 `pymysql.err.IntegrityError: (1062, "Duplicate entry '101' for key 'funds.PRIMARY'")`，这条报错容易让人误以为「上次没跑干净」而去执行 `DELETE`、`TRUNCATE`，反而删掉别人手工录入的数据。

**更新列表里不要写主键。** 上面故意没有 `id = VALUES(id)`：万一唯一索引先命中（例如已有同名博主但 ID 不同），带 `id` 的更新会把那行数据的主键改掉，产生误伤。只更新业务字段更安全。

---

## 固定数据清单

所有数据的**日期窗口是 2026-09-01 到 2026-09-30**，验证时的查询日期统一是 **2026-09-30**（下文叫「演示基准日」）。

| 表 | 行数 | 说明 |
| --- | --- | --- |
| `bloggers` | 3 | ID `1`、`2`、`3` |
| `funds` | 4 | ID `101`、`102`、`103`、`104` |
| `initial_positions` | 5 | ID `1`–`5` |
| `operations` | 8 | ID `1`–`8` |
| `nav_history` | 119 | 基金 `101`/`102`/`103` 各 30 天，基金 `104` 只有 29 天 |

### 3 个博主

| ID | name | sector | observe_start_date | 覆盖的场景 |
| --- | --- | --- | --- | --- |
| 1 | 演示博主-稳健哥 | 权益 | 2026-01-05 | 主力演示博主：数据最全 |
| 2 | 演示博主-进取姐 | 医药 | 2026-09-18 | 边界博主：负份额 + 缺净值 |
| 3 | 演示博主-新兵弟 | 债券 | 2026-09-30 | 空数据博主：没有任何持仓和操作 |

这三个 ID 是**显式写进脚本的**，不靠 `AUTO_INCREMENT` 生成——否则跑两遍 ID 就可能不一样，「引用固定 ID」就做不到了。

### 4 只基金

| ID | name | fund_code |
| --- | --- | --- |
| 101 | 演示成长混合A | DEMO0001 |
| 102 | 演示价值混合A | DEMO0002 |
| 103 | 演示医药混合A | DEMO0003 |
| 104 | 演示债券混合A | DEMO0004 |

刻意用虚构名称和 `DEMO` 前缀，避免和真实基金混淆。

### 5 条初始持仓

| ID | blogger_id | fund_id | shares | cost_amount | record_date |
| --- | --- | --- | --- | --- | --- |
| 1 | 1 | 101 | 1000.0000 | 10000.00 | 2026-09-01 |
| 2 | 1 | 101 | 500.0000 | 6000.00 | 2026-09-15 |
| 3 | 1 | 102 | 2000.0000 | 30000.00 | 2026-09-01 |
| 4 | 2 | 103 | 500.0000 | 10000.00 | 2026-09-08 |
| 5 | 2 | 104 | 1000.0000 | 12000.00 | 2026-09-08 |

**ID `1` 和 ID `2` 是重点**：同一博主（1）+ 同一基金（101）+ 两条不同 `record_date`。系统口径规定（任务 030 的 `_pick_first_initial_position()`）**只取 `record_date` 最早的那一条参与计算，其余完全不累加**。所以博主 1 的基金 101 起点是 1000 份 / 10000.00 元，不是 1500 份 / 16000.00 元，两者成本差 6000 元，一查就知道对不对。

### 8 条操作记录

| ID | blogger_id | fund_id | operation_type | operation_date | shares | amount | remark |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 101 | buy | 2026-09-10 | 200.0000 | 2600.00 | 演示：同日先买 |
| 2 | 1 | 101 | sell | 2026-09-10 | 300.0000 | 3450.00 | 演示：同日后卖 |
| 3 | 1 | 101 | dividend_cash | 2026-09-20 | 0.0000 | 500.00 | 演示：现金分红 |
| 4 | 1 | 102 | buy | 2026-09-12 | 500.0000 | 7500.00 | 演示：加仓 |
| 5 | 1 | 102 | sell | 2026-09-26 | 800.0000 | 12800.00 | 演示：减仓 |
| 6 | 2 | 103 | sell | 2026-09-19 | 800.0000 | 16800.00 | 演示：超额卖出 |
| 7 | 2 | 103 | sell | 2026-09-26 | 200.0000 | 4200.00 | 演示：负份额后再卖 |
| 8 | 2 | 104 | dividend_cash | 2026-09-15 | 0.0000 | 300.00 | 演示：债券分红 |

三种操作类型都有，另外埋了三个点：

1. **同一天多笔操作（ID `1` + ID `2`）**：同为 2026-09-10、基金 101，顺序规定为「按 `operation_id` 升序」即先买后卖。正确顺序最终**份额 900、成本 9450.00**；顺序反了份额仍是 900 但成本是 **9600.00**。看到 9600 就说明排序写错了。
2. **超额卖出导致负份额（ID `6`）**：期初 500 份卖出 800 份，剩余 **-300**。第一版不校验超额卖出，接口必须返回 `-300.0000`，不能返回 `0`。
3. **负份额后再卖（ID `7`）**：卖出前份额是 -300，走到任务 030 的 `else` 分支——**成本保持不变，只继续减少份额**，最终份额 -500、成本 -6000.00。

### 净值：119 条，其中一只故意缺一天

净值不手写 119 行常量，用**固定首值 + 固定步长**按天推算，不含随机值也不含当前日期。

| fund_id | 起始日期 | 结束日期 | 首日净值 | 每天步长 | 天数 | 2026-09-30 净值 |
| --- | --- | --- | --- | --- | --- | --- |
| 101 | 2026-09-01 | 2026-09-30 | 10.9600 | +0.0100 | 30 | 11.2500 |
| 102 | 2026-09-01 | 2026-09-30 | 15.0500 | +0.0500 | 30 | 16.5000 |
| 103 | 2026-09-01 | 2026-09-30 | 15.2000 | +0.2000 | 30 | 21.0000 |
| 104 | 2026-09-01 | **2026-09-29** | 12.0200 | +0.0100 | **29** | **缺失** |

基金 `104` 故意少生成 2026-09-30 这一天。对应规则（任务 033 的 `get_nav_on_date_map()`）：**指定日期当天没有净值，市值、收益金额、收益率都返回 `null`，不用前一天净值兜底。** 博主 2 正好持有基金 104，所以查 2026-09-30 时它整行都是 `null`、总市值也是 `null`；查 2026-09-29 净值 12.3000、正常算出数值。

### 场景覆盖对照表

| 要求覆盖的口径 | 对应的数据 |
| --- | --- |
| 三种操作类型 | operations ID `1`/`4`（buy）、`2`/`5`/`6`/`7`（sell）、`3`/`8`（dividend_cash） |
| 同一天多笔操作按 ID 升序 | operations ID `1` + `2` |
| 超额卖出份额为负 | operations ID `6`、`7` |
| 多条初始持仓只取最早一条 | initial_positions ID `1` + `2` |
| 缺净值返回 null | fund 104 缺 2026-09-30 净值，博主 2 持有它 |
| 平均成本法 | operations ID `1`+`2`：12600 / 1200 = 10.5 |
| 空数据 | 博主 3 没有任何持仓和操作 |

---

## 关于 observe_days 和 status 会随时间变化

`observe_days`（观察天数）和 `status` 是**派生字段**：项目规定它们不落库，由后端拿 `observe_start_date` 和**当天日期**实时算（见 `docs/api/v1-basic-management.md`）。这意味着「观察天数 < 30」和「0 天」这两个状态用固定日期**无法永久保持**——到了某个日期博主会自动从 `observing` 变 `active`。

这个矛盾**不需要解决**，按下面四条处理：

1. **seed 脚本的目标不是锁住 `status`，而是锁住 ID、持仓、操作、净值这四类数据。** 它们都是固定值、永久稳定，也正是收益和快照计算真正依赖的输入。锁住它们就达到了本任务的目的。
2. **`status` 会随时间推移自然变化，这是设计使然，不是 bug。** 失效日期如下。**不要试图用 `date.today()` 去修**——那会让数据本身每天都不一样，本末倒置。

   | 博主 | observe_start_date | 演示基准日 2026-09-30 | 何时自动变 active |
   | --- | --- | --- | --- |
   | 1 稳健哥 | 2026-01-05 | 268 天 → `active` | **永远不会变**，恒为 `active` |
   | 2 进取姐 | 2026-09-18 | 12 天 → `observing` | 从 2026-10-18 起变 `active` |
   | 3 新兵弟 | 2026-09-30 | 0 天 → `observing` | 从 2026-10-30 起变 `active` |

3. **验证 `status` 时不断言固定值**，改成「先用 SQL `SELECT DATEDIFF(CURDATE(), observe_start_date)` 算出当天应有的值，再和接口返回的比对」（见验证 4）。这样不管哪天跑都能核对。
4. **需要复现某个历史日期的场景时，只改脚本顶部的 `SEED_BASE_DATE` 这一个日期常量**再重跑。注意改它会把整批数据的日期整体平移，改之前先和协调人确认。

---

## 执行目录

所有命令默认在以下目录执行，每次新开终端都要先激活虚拟环境：

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

---

## 具体步骤

> 步骤 2 到步骤 4 是**同一个文件 `backend/scripts/seed_data.py` 的三个片段**，按顺序追加写入即可，步骤 4 写完就是完整文件。

### 步骤 1：确认环境指向开发库，并记下测试库行数

**必要性：**
本脚本只允许写开发库。先把环境变量摆正，同时记下测试库现有行数——步骤 8 要用它做「没被污染」的对比，不记下来事后就无从核对了。

```bash
mysql -u root -p -e "SELECT COUNT(*) AS before_count FROM fund_test_db.bloggers;"
mysql -u root -p -e "SELECT COUNT(*) AS before_count FROM fund_test_db.nav_history;"

export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=你的数据库密码
export DB_NAME=fund_db

python -c "from app.config import DB_CONFIG; print(DB_CONFIG['database'])"

python -m scripts.check_db
mysql -u root -p -e "SHOW TABLES FROM fund_db;"
```

第一条 `python -c` 预期输出 `fund_db`；`SHOW TABLES` 预期能看到 `bloggers`、`funds`、`initial_positions`、`nav_history`、`operations`。少了 `nav_history` 或 `operations` 就回到任务 025 / 019，先执行 `python -m scripts.init_db` 补齐。

---

### 步骤 2：新建脚本，写入固定的演示数据常量

**必要性：**
这一步定义「要写什么」。把数据集中放在文件顶部的常量里，后面改数值、加行数都不用动 SQL 和执行流程，别人也能一眼看清这套演示数据的全貌，不必去 SQL 语句里找。

新建 `backend/scripts/seed_data.py`，先写入：

```python
"""开发库 fund_db 的演示数据（seed data）写入脚本。

只写开发库 fund_db。测试库 fund_test_db 的数据由 tests/factories.py 生成，
本脚本不会也不应该连到测试库。

执行方式（在 backend 目录）：

    export DB_NAME=fund_db
    python -m scripts.seed_data
"""
from datetime import date, timedelta
from decimal import Decimal

from app.config import DB_CONFIG
from app.db import get_connection


DEV_DB_NAME = "fund_db"

# 演示基准日：所有演示数据围绕这一天设计，手工验证也用这一天查询。
# 写成固定日期，不读取系统当前日期，否则数据会随真实时间漂移。
SEED_BASE_DATE = date(2026, 9, 30)
NAV_START_DATE = date(2026, 9, 1)
NAV_END_DATE = SEED_BASE_DATE


BLOGGERS = [
    # 远早于基准日：观察天数恒 >= 30，status 恒为 active
    {"id": 1, "name": "演示博主-稳健哥", "sector": "权益",
     "observe_start_date": date(2026, 1, 5)},
    # 基准日前 12 天：演示 observe_days < 30 的 observing 状态
    {"id": 2, "name": "演示博主-进取姐", "sector": "医药",
     "observe_start_date": SEED_BASE_DATE - timedelta(days=12)},
    # 基准日当天：演示 observe_days == 0
    {"id": 3, "name": "演示博主-新兵弟", "sector": "债券",
     "observe_start_date": SEED_BASE_DATE},
]

FUNDS = [
    {"id": 101, "name": "演示成长混合A", "fund_code": "DEMO0001"},
    {"id": 102, "name": "演示价值混合A", "fund_code": "DEMO0002"},
    {"id": 103, "name": "演示医药混合A", "fund_code": "DEMO0003"},
    {"id": 104, "name": "演示债券混合A", "fund_code": "DEMO0004"},
]

INITIAL_POSITIONS = [
    # ID 1 和 ID 2 是「同一博主 1 + 同一基金 101 + 两条不同 record_date」，
    # 系统口径只取最早的一条，所以 ID 2 不参与累加。
    {"id": 1, "blogger_id": 1, "fund_id": 101, "shares": Decimal("1000.0000"),
     "cost_amount": Decimal("10000.00"), "record_date": date(2026, 9, 1)},
    {"id": 2, "blogger_id": 1, "fund_id": 101, "shares": Decimal("500.0000"),
     "cost_amount": Decimal("6000.00"), "record_date": date(2026, 9, 15)},
    {"id": 3, "blogger_id": 1, "fund_id": 102, "shares": Decimal("2000.0000"),
     "cost_amount": Decimal("30000.00"), "record_date": date(2026, 9, 1)},
    {"id": 4, "blogger_id": 2, "fund_id": 103, "shares": Decimal("500.0000"),
     "cost_amount": Decimal("10000.00"), "record_date": date(2026, 9, 8)},
    {"id": 5, "blogger_id": 2, "fund_id": 104, "shares": Decimal("1000.0000"),
     "cost_amount": Decimal("12000.00"), "record_date": date(2026, 9, 8)},
]

OPERATIONS = [
    # ID 1 和 ID 2 同为 2026-09-10、基金 101。计算顺序按 operation_id 升序：先买后卖。
    {"id": 1, "blogger_id": 1, "fund_id": 101, "operation_type": "buy",
     "operation_date": date(2026, 9, 10), "shares": Decimal("200.0000"),
     "amount": Decimal("2600.00"), "remark": "演示：同日先买"},
    {"id": 2, "blogger_id": 1, "fund_id": 101, "operation_type": "sell",
     "operation_date": date(2026, 9, 10), "shares": Decimal("300.0000"),
     "amount": Decimal("3450.00"), "remark": "演示：同日后卖"},
    {"id": 3, "blogger_id": 1, "fund_id": 101, "operation_type": "dividend_cash",
     "operation_date": date(2026, 9, 20), "shares": Decimal("0.0000"),
     "amount": Decimal("500.00"), "remark": "演示：现金分红"},
    {"id": 4, "blogger_id": 1, "fund_id": 102, "operation_type": "buy",
     "operation_date": date(2026, 9, 12), "shares": Decimal("500.0000"),
     "amount": Decimal("7500.00"), "remark": "演示：加仓"},
    {"id": 5, "blogger_id": 1, "fund_id": 102, "operation_type": "sell",
     "operation_date": date(2026, 9, 26), "shares": Decimal("800.0000"),
     "amount": Decimal("12800.00"), "remark": "演示：减仓"},
    # 期初 500 份卖出 800 份，剩余份额变负。第一版不校验超额卖出，照实返回。
    {"id": 6, "blogger_id": 2, "fund_id": 103, "operation_type": "sell",
     "operation_date": date(2026, 9, 19), "shares": Decimal("800.0000"),
     "amount": Decimal("16800.00"), "remark": "演示：超额卖出"},
    # 上一笔后份额已是负数，走到「卖出前没有正份额」分支：成本不变，只减份额。
    {"id": 7, "blogger_id": 2, "fund_id": 103, "operation_type": "sell",
     "operation_date": date(2026, 9, 26), "shares": Decimal("200.0000"),
     "amount": Decimal("4200.00"), "remark": "演示：负份额后再卖"},
    {"id": 8, "blogger_id": 2, "fund_id": 104, "operation_type": "dividend_cash",
     "operation_date": date(2026, 9, 15), "shares": Decimal("0.0000"),
     "amount": Decimal("300.00"), "remark": "演示：债券分红"},
]

NAV_SERIES = [
    {"fund_id": 101, "first_nav": Decimal("10.9600"),
     "step": Decimal("0.0100"), "end_date": NAV_END_DATE},
    {"fund_id": 102, "first_nav": Decimal("15.0500"),
     "step": Decimal("0.0500"), "end_date": NAV_END_DATE},
    {"fund_id": 103, "first_nav": Decimal("15.2000"),
     "step": Decimal("0.2000"), "end_date": NAV_END_DATE},
    # 基金 104 故意只生成到 2026-09-29，用来验证「缺净值返回 null」。
    {"fund_id": 104, "first_nav": Decimal("12.0200"),
     "step": Decimal("0.0100"), "end_date": date(2026, 9, 29)},
]
```

金额和份额一律写成 `Decimal("...")` 字符串形式，不用 `float`（累加会引入二进制精度误差，乘步长时误差还会随天数放大）；每条数据都带显式 `id`；`NAV_SERIES` 每只基金只有「首值 + 步长 + 结束日期」三个参数，净值由步骤 3 的函数推算。

---

### 步骤 3：追加净值生成函数和五张表的插入语句

**必要性：**
这是脚本真正写数据库的部分。净值用「固定首值 + 固定步长」推算而不是手写 119 行，改一个数不用翻半天；五张表各一条 `INSERT ... ON DUPLICATE KEY UPDATE`，重复执行时不报唯一约束错误。

继续追加：

```python
def build_nav_rows(config):
    """按固定首值 + 固定步长生成一段连续日期的净值记录。

    同样的入参每次算出来的结果完全一致，不含随机值，也不读取系统当前日期。
    """
    rows = []
    current_date = NAV_START_DATE
    index = 0

    while current_date <= config["end_date"]:
        rows.append({
            "fund_id": config["fund_id"],
            "nav_date": current_date,
            "nav": config["first_nav"] + config["step"] * index,
        })
        current_date += timedelta(days=1)
        index += 1

    return rows


INSERT_BLOGGER_SQL = """
    INSERT INTO bloggers (id, name, sector, observe_start_date)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE sector = VALUES(sector),
        observe_start_date = VALUES(observe_start_date)
"""

INSERT_FUND_SQL = """
    INSERT INTO funds (id, name, fund_code) VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE name = VALUES(name)
"""

INSERT_INITIAL_POSITION_SQL = """
    INSERT INTO initial_positions
        (id, blogger_id, fund_id, shares, cost_amount, record_date)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE shares = VALUES(shares),
        cost_amount = VALUES(cost_amount)
"""

INSERT_OPERATION_SQL = """
    INSERT INTO operations
        (id, blogger_id, fund_id, operation_type, operation_date, shares, amount, remark)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE operation_type = VALUES(operation_type),
        operation_date = VALUES(operation_date), shares = VALUES(shares),
        amount = VALUES(amount), remark = VALUES(remark)
"""

INSERT_NAV_SQL = """
    INSERT INTO nav_history (fund_id, nav_date, nav) VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE nav = VALUES(nav)
"""


def insert_rows(cursor, sql, rows, keys, label):
    """按 keys 指定的顺序，把 rows 逐行写进数据库。"""
    for row in rows:
        cursor.execute(sql, tuple(row[key] for key in keys))

    print(f"{label}: {len(rows)} 行已写入")
```

`Decimal` 加减乘会保持小数位数，算出来的 `nav` 天然是 4 位小数，正好对齐 `DECIMAL(18, 4)` 列。五条 SQL 的更新列表都**不含主键 `id`**。`initial_positions` 表**没有** `remark` 字段，`operations` 表才有，写错会报 `Unknown column`，照 007、019 的建表 SQL 核对。MySQL 8.0.20 及以上可能对 `VALUES()` 给出过时警告，可以忽略；只有明确报错时才反馈确认后改写。

---

### 步骤 4：追加数据库守卫和 `main()`

**必要性：**
脚本要能被别人随手执行，必须自带最后一道保险：**脚本内部再确认一次当前数据库**。光靠人每次记得 `export DB_NAME=fund_db` 不够——只要有人在终端跑过一次 `pytest`，环境变量还留着 `fund_test_db`，下一次执行就会把演示数据写进测试库，然后被测试夹具在几秒后 TRUNCATE 掉，白跑一趟还没证据。

继续追加：

```python
def assert_development_database():
    current = DB_CONFIG.get("database")

    if current != DEV_DB_NAME:
        raise RuntimeError(
            f"seed 脚本只允许写入 {DEV_DB_NAME}，"
            f"当前配置是 {current}，已中止执行。"
            f"请执行 export DB_NAME={DEV_DB_NAME} 后重试"
        )


def main():
    assert_development_database()

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS current_db")
            current_db = cursor.fetchone()["current_db"]

            if current_db != DEV_DB_NAME:
                raise RuntimeError(
                    f"拒绝写入数据库 {current_db}，只允许写入 {DEV_DB_NAME}"
                )

            # 插入顺序必须遵守外键：先父表，后子表
            insert_rows(cursor, INSERT_BLOGGER_SQL, BLOGGERS,
                        ("id", "name", "sector", "observe_start_date"), "bloggers")
            insert_rows(cursor, INSERT_FUND_SQL, FUNDS,
                        ("id", "name", "fund_code"), "funds")
            insert_rows(cursor, INSERT_INITIAL_POSITION_SQL, INITIAL_POSITIONS,
                        ("id", "blogger_id", "fund_id", "shares", "cost_amount",
                         "record_date"), "initial_positions")
            insert_rows(cursor, INSERT_OPERATION_SQL, OPERATIONS,
                        ("id", "blogger_id", "fund_id", "operation_type",
                         "operation_date", "shares", "amount", "remark"),
                        "operations")
            nav_total = 0
            for config in NAV_SERIES:
                rows = build_nav_rows(config)
                insert_rows(cursor, INSERT_NAV_SQL, rows, ("fund_id", "nav_date", "nav"),
                            f"nav_history fund_id={config['fund_id']}")
                nav_total += len(rows)
            print(f"nav_history: 合计 {nav_total} 行已写入")

        conn.commit()
    finally:
        conn.close()

    print(f"seed data 写入完成，目标数据库：{DEV_DB_NAME}")
    print(f"演示基准日：{SEED_BASE_DATE}")


if __name__ == "__main__":
    main()
```

两道检查和任务 015 里 `conftest.py` 的守卫完全一样：第一道查 **Python 配置里的库名**，第二道 `SELECT DATABASE()` 向 MySQL 再确认**实际连上的库名**。`RuntimeError` 会让脚本立刻停住并打印原因，不会继续写数据。

**插入顺序必须是 `bloggers` / `funds` → `initial_positions` / `operations` / `nav_history`**，后面三张表都有指向前两张表的外键，顺序反了会报错误码 1452（见常见坑第 1 条）。

---

### 步骤 5：语法检查并执行三次

**必要性：**
先确认没有语法错误再去连数据库——语法错误会在执行到一半才暴露，那时可能已经写入了部分数据。连跑三次是「可重复执行」这个核心验收点的直接证明。

```bash
python -m py_compile scripts/seed_data.py
```

预期没有输出，退出码 `0`。然后连跑三次：

```bash
python -m scripts.seed_data
python -m scripts.seed_data
python -m scripts.seed_data && echo "第三次执行成功"
```

预期三次输出**完全相同**（行数一样），不出现 `Duplicate entry`。第一次的输出依次是 `bloggers: 3 行已写入`、`funds: 4 行已写入`、`initial_positions: 5 行已写入`、`operations: 8 行已写入`、四条 `nav_history fund_id=101/102/103/104: 30/30/30/29 行已写入`、`nav_history: 合计 119 行已写入`、`seed data 写入完成，目标数据库：fund_db`、`演示基准日：2026-09-30`。

---

### 步骤 6：在 MySQL 中核对行数和缺失的净值

**必要性：**
脚本自己打印的行数是它「想写多少」，不等于数据库里「实际有多少」。必须查一次库，确认没有因为 SQL 写错而静默少写，也确认基金 104 缺净值这天是真的没有。

进 `mysql -u root -p fund_db` 后执行：

```sql
SELECT COUNT(*) FROM bloggers WHERE id IN (1, 2, 3);            -- 3
SELECT COUNT(*) FROM funds WHERE id IN (101, 102, 103, 104);     -- 4
SELECT COUNT(*) FROM initial_positions WHERE id IN (1,2,3,4,5);  -- 5
SELECT COUNT(*) FROM operations WHERE id IN (1,2,3,4,5,6,7,8);   -- 8
SELECT COUNT(*) FROM nav_history WHERE fund_id = 104 AND nav_date BETWEEN '2026-09-01' AND '2026-09-29';  -- 29
SELECT COUNT(*) FROM nav_history WHERE fund_id = 104 AND nav_date = '2026-09-30';  -- 0
SELECT fund_id, nav FROM nav_history WHERE nav_date = '2026-09-30' ORDER BY fund_id;
```

最后一条预期看到 `101` → `11.2500`、`102` → `16.5000`、`103` → `21.0000`，**没有 `104`**。如果 `fund_db` 里本来就有别的数据，行数会比这里的数字大，此时核对**加了 `WHERE id IN (...)` 过滤之后的行数**，不要看整表行数。

---

### 步骤 7：启动服务，用接口核对固定数据

**必要性：**
行数对了不等于业务口径对了。前面埋的每一处设计（同日两笔的先后顺序、负份额、缺净值、多条初始持仓只取最早一条）只有接口返回值才看得出来。这一步是这批演示数据真正的价值所在。

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
python run.py
```

另开一个终端，在 `backend` 目录执行下面四组请求。

#### 请求 1：博主 1 的持仓快照

```bash
curl -s "http://127.0.0.1:5000/api/v1/bloggers/1/position-snapshots?snapshot_date=2026-09-30"
```

预期 HTTP `200`，`data.items` 有两条：

| fund_id | initial_record_date | initial_shares | initial_cost_amount | buy_shares | buy_amount | sell_shares | sell_amount | dividend_cash_amount | shares | cost_amount |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 101 | 2026-09-01 | 1000.0 | 10000.0 | 200.0 | 2600.0 | 300.0 | 3450.0 | 500.0 | 900.0 | 9450.0 |
| 102 | 2026-09-01 | 2000.0 | 30000.0 | 500.0 | 7500.0 | 800.0 | 12800.0 | 0.0 | 1700.0 | 25500.0 |

基金 101 的 `initial_shares` 是 `1000.0`（不是 `1500.0`）证明 2026-09-15 那条**没有参与累加**；`cost_amount` 是 `9450.0`（不是 `9600.0`）证明同日两笔是**按 ID 升序**处理的；`dividend_cash_amount` 是 `500.0` 证明现金分红被单独统计。

#### 请求 2：博主 1 的收益

```bash
curl -s "http://127.0.0.1:5000/api/v1/bloggers/1/returns?return_date=2026-09-30"
```

汇总：`total_cost_amount` = 34950.0、`total_market_value` = 38175.0、`profit_amount` = 3225.0、`return_rate` = 0.092275。`data.items` 两条：

| fund_id | shares | cost_amount | nav | market_value | profit_amount | return_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 101 | 900.0 | 9450.0 | 11.25 | 10125.0 | 675.0 | 0.071429 |
| 102 | 1700.0 | 25500.0 | 16.5 | 28050.0 | 2550.0 | 0.1 |

#### 请求 3：博主 2 的收益（负份额 + 缺净值），并和前一天对照

```bash
curl -s "http://127.0.0.1:5000/api/v1/bloggers/2/returns?return_date=2026-09-30"
curl -s "http://127.0.0.1:5000/api/v1/bloggers/2/returns?return_date=2026-09-29"
```

查 2026-09-30，汇总：`total_cost_amount` = 6000.0（成本不依赖净值，照算）、`total_market_value` / `profit_amount` / `return_rate` 都是 `null`（只要有一只基金缺净值，总市值就是 `null`）。`data.items` 两条：

| fund_id | shares | cost_amount | nav | nav_date | market_value | profit_amount | return_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 103 | **-500.0** | -6000.0 | 21.0 | 2026-09-30 | -10500.0 | -4500.0 | `null` |
| 104 | 1000.0 | 12000.0 | `null` | `null` | `null` | `null` | `null` |

基金 103 的 `shares` 是 **-500.0**（不是 `0`），超额卖出后负数照实返回；它的 `return_rate` 是 `null`，因为成本 -6000 小于等于 0；基金 104 整行都是 `null`，缺净值时**没有拿 09-29 的净值兜底**。查 2026-09-29 做对照：`total_cost_amount` = 6000.0、`total_market_value` = 1900.0、`profit_amount` = -4100.0、`return_rate` = -0.683333，基金 104 的 `nav` = 12.3、`market_value` = 12300.0。同一位博主换一天就从「全是 null」变成「全是数字」。

#### 请求 4：近期操作统计

```bash
curl -s "http://127.0.0.1:5000/api/v1/dashboards/recent-operations?start_date=2026-09-01&end_date=2026-09-30&limit=20"
```

预期 HTTP `200`，`data.summary` 里：`operation_count` = 8、`buy_count` = 2、`buy_shares` = 700.0、`buy_amount` = 10100.0、`sell_count` = 4、`sell_shares` = 2100.0、`sell_amount` = 37700.0、`dividend_cash_count` = 2、`dividend_cash_amount` = 800.0；`data.items` 的长度也是 `8`。字段名以 `docs/api/v1-dashboards.md` 为准；实际返回的字段名与本表不一致时**不要改代码**，把差异记进反馈。

---

### 步骤 8：确认测试库没被写入，并跑一次全量测试

**必要性：**
这是本任务的安全红线。seed 脚本写进 `fund_test_db` 有两个后果：污染别人的测试数据；白写——夹具每次都 TRUNCATE，写进去的数据活不过第一个测试。必须实际核对数字。

停止服务，在 `backend` 目录执行下面三段：

```bash
mysql -u root -p -e "SELECT COUNT(*) AS after_count FROM fund_test_db.bloggers;"
mysql -u root -p -e "SELECT COUNT(*) AS after_count FROM fund_test_db.nav_history;"

export DB_NAME=fund_test_db
python -m scripts.seed_data

export DB_NAME=fund_db
pytest -q
```

前两个数字必须和步骤 1 记下来的 `before_count` **完全一样**。中间那段预期报错退出，信息类似 `RuntimeError: seed 脚本只允许写入 fund_db，当前配置是 fund_test_db，已中止执行。请执行 export DB_NAME=fund_db 后重试`——看到这个报错说明守卫有效，是**预期结果**，不是失败。`pytest -q` 预期全部通过；`pytest` 只连 `fund_test_db`，这一步同时确认本任务没有破坏已有功能。

---

## 验证方式

1. **可重复执行**：连跑三次 `python -m scripts.seed_data`，三次都不报错、输出行数一致。
2. **MySQL 行数**：按步骤 6 的 SQL 逐条核对（3 / 4 / 5 / 8 / 29 / 0）。
3. **接口期望值**：按步骤 7 的四组请求比对，重点四个数——`initial_shares = 1000`（不是 1500）、`cost_amount = 9450`（不是 9600）、`shares = -500`（不是 0）、基金 104 整行 `null`（不是 0）。
4. **观察天数与状态按当天核算**：`observe_days` 和 `status` 随时间变化，不写死期望值，改成和 MySQL 算出来的结果比。先执行 `SELECT id, observe_start_date, DATEDIFF(CURDATE(), observe_start_date) AS expect_days, CASE WHEN DATEDIFF(CURDATE(), observe_start_date) >= 30 THEN 'active' ELSE 'observing' END AS expect_status FROM bloggers WHERE id IN (1, 2, 3) ORDER BY id;`，再请求 `curl -s "http://127.0.0.1:5000/api/v1/bloggers?page=1&page_size=20"`，预期 `observe_days` 与 `expect_days` 一致、`status` 与 `expect_status` 一致。另外 `?status=active` 的结果里博主 1 **永远**出现，`?status=observing` 里**永远不**出现——这是这批数据里唯一一个永久固定的状态断言。
5. **测试库未被污染**：步骤 1 与步骤 8 的 `fund_test_db` 行数一致；`export DB_NAME=fund_test_db` 时脚本抛 `RuntimeError`。
6. **已有测试**：`pytest -q` 全部通过，没有 failed 也没有 error。

---

## 常见坑

### 1. 外键顺序错误，报 1452

```text
pymysql.err.IntegrityError: (1452, 'Cannot add or update a child row: a foreign key constraint fails')
```

先插了 `initial_positions` / `operations` / `nav_history`，而它们引用的 `bloggers`、`funds` 还没插进去。正确顺序：**父表 `bloggers`、`funds` 在最前，三张子表在后面。** 整套语句在同一个事务里，出错后不会留下半截数据，改对顺序重跑即可。

### 2. 用了相对日期，数据每天都不一样

写成 `date.today()`、`date.today() - timedelta(days=7)`、`datetime.now().date()` 都错。过几天再跑验证就不是文档里那两个数了；更麻烦的是「收益日期不能晚于今天」这条校验（任务 034）会让未来日期直接返回 400，于是今天能过的命令下周突然报错，排查方向完全是错的。本任务所有日期都是常量或从 `SEED_BASE_DATE` 推算，自查 `grep -n "today\|now()" scripts/seed_data.py` 预期没有任何输出。

### 3. 重复执行报 1062 唯一键冲突

`pymysql.err.IntegrityError: (1062, "Duplicate entry '101' for key 'funds.PRIMARY'")` 是用了裸 `INSERT` 忘了 `ON DUPLICATE KEY UPDATE`。补上即可，**不要用 `DELETE` 或 `TRUNCATE` 当解决办法**——那会把别人手工录入的数据一起清掉。

### 4. 误把 seed 跑进了测试库

现象：脚本报成功了，但过一会儿跑 `pytest -q` 或别人跑测试之后，演示数据全没了——`clean_db` 夹具在每个测试前 TRUNCATE 全部相关表。三重保险都保留：`assert_development_database()`、`main()` 里的 `SELECT DATABASE()` 复查、执行前确认 `DB_CONFIG['database']` 输出 `fund_db`。

### 5. 把超额卖出那笔「修正」成合法值

看到 ID `6`（期初 500 份、卖出 800 份）很容易觉得「不合理，改成卖 300 份」。**不要改。** 它验证的是系统规定：**第一版不校验超额卖出，剩余份额可以为负，接口照实返回。** 改完 `shares` 变正数，负数场景就再也测不到了。ID `7` 同理，覆盖「卖出前没有正份额」那个分支。

### 6. 让数据库自己分配主键，或用 `python scripts/seed_data.py` 运行

去掉 `INSERT` 里的 `id` 让 `AUTO_INCREMENT` 分配，第二次执行时 `ON DUPLICATE KEY UPDATE` 没有主键可以命中，会追加一批同内容不同 ID 的数据，「引用固定 ID」也落空——每张表都必须显式带上 `id`。用 `python scripts/seed_data.py` 运行会报 `ModuleNotFoundError: No module named 'app'`，正确命令是在 `backend` 目录执行 `python -m scripts.seed_data`——`-m` 会把当前目录加进模块搜索路径。

---

## 完成标准

以下条件全部满足，任务 045 才算完成：

1. `backend/scripts/seed_data.py` 存在。
2. 脚本里**没有** `date.today()`、`datetime.now()`、`random` 任何一项。
3. `python -m scripts.seed_data` 连续执行三次都不报错，输出一致。
4. `bloggers` 3 行、`funds` 4 行、`initial_positions` 5 行、`operations` 8 行、`nav_history` 119 行（按 ID / 日期范围过滤后计数）。
5. `nav_history` 里 `fund_id = 104` 且 `nav_date = '2026-09-30'` 的记录数是 `0`。
6. 所有数据都带固定主键 ID（`bloggers` 为 1/2/3，`funds` 为 101/102/103/104）。
7. 插入顺序遵守外键：父表在前，子表在后。
8. 步骤 7 的四组接口请求全部返回 HTTP `200`，数值与本任务列出的期望值一致（缺净值场景必须是 `null`，负份额场景必须是负数）。
9. 观察天数验证按「验证方式」第 4 条通过；博主 1 恒为 `active`。
10. `fund_test_db` 的行数在跑脚本前后没有变化。
11. `export DB_NAME=fund_test_db` 时脚本抛 `RuntimeError` 并中止。
12. `pytest -q` 全部通过，没有 failed 也没有 error。

---

## 完成后请反馈

请把下面命令的完整输出发给后端协调人：

```bash
python -m scripts.seed_data
python -m scripts.seed_data
cat scripts/seed_data.py
curl -s "http://127.0.0.1:5000/api/v1/bloggers/1/position-snapshots?snapshot_date=2026-09-30"
curl -s "http://127.0.0.1:5000/api/v1/bloggers/1/returns?return_date=2026-09-30"
curl -s "http://127.0.0.1:5000/api/v1/bloggers/2/returns?return_date=2026-09-30"
curl -s "http://127.0.0.1:5000/api/v1/bloggers/2/returns?return_date=2026-09-29"
curl -s "http://127.0.0.1:5000/api/v1/dashboards/recent-operations?start_date=2026-09-01&end_date=2026-09-30&limit=20"
pytest -q
```

另外请说明三件事：跑脚本前后 `fund_test_db.bloggers`、`fund_test_db.nav_history` 的行数分别是多少；`SELECT id, name, observe_start_date, DATEDIFF(CURDATE(), observe_start_date) FROM bloggers WHERE id IN (1,2,3);` 的实际输出（用来记录你执行当天这三个博主真实的观察天数）；实际返回的字段名如果和本文档表格里的名字不一致，逐条列出差异，**不要自行修改接口文档或代码**。

本任务验收通过后，由协调人统一把 `034`、`035`、`036`、`037`、`038`、`040` 六份文档里的「把 ID 换成实际存在的 ID」改成引用本任务的固定 ID（`blogger_id` 用 `1`/`2`/`3`，`fund_id` 用 `101`/`102`/`103`/`104`，日期用 `2026-09-30`），并把本文档的期望值补进去。**这一步由协调人做，你不需要改那几份文档。** 注意：046–049 的自动化测试用工厂函数在测试库自造数据，**不依赖本脚本**；本脚本服务于 034–040 的手工验证与固定 ID 替换，不要把它当成 046–049 的前置。
