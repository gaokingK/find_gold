# 接口契约口径审阅报告

| 项目 | 内容 |
| --- | --- |
| 审阅对象 | `docs/api/` 下 6 份接口文档 + `docs/requirements/v1-basic-management.md` |
| 审阅人 | 许清楚（产品经理） |
| 日期 | 2026-10-09 |
| 审阅类型 | 契约口径审阅（只看文档，不看代码） |
| 结论 | **不可直接下发**，需先补齐第二节 18 条口径 |

---

## 一、结论先行

**1. 这 6 份文档不能当"前后端唯一契约"，只能当"正常路径说明书"。**
边界条件大面积空白：分页越界、非法排序值、日期默认值与越界、小数位、四舍五入模式、Decimal 落库精度、全局异常兜底（非法 JSON / 404 路由 / 405 / 500），全部没写。新手照着写，每个接口都会自己发明一套口径，验收时一次性爆出几十个不一致，且每一条都要来回扯皮。

**2. 最大风险是两处硬冲突，不是缺字段。**
① **多条初始持仓**：快照文档说"取最早一条作为起点"，收益文档说"统计 `return_date` 当天或之前的所有初始持仓"——同一博主同一天，两个接口会给出不同的份额和成本。② **平均成本法只写了五个字**，没有公式，也没定义同一天多笔操作的计算顺序（先卖后买和先买后卖结果不同）。这两处不补，前端两个页面上的数字必然对不上，而且没人能判定哪个是对的。

**3. "缺净值返回 null" 这条口径只在基金级写清了，博主级和全局级有缺口、有循环引用。**
`v1-returns.md` 2.1 说"没有任何持仓数据 → 总市值返回 `0`"，但没写"有持仓且**全部**基金都缺净值"这一格；`v1-dashboards.md` 说"空值口径沿用 `v1-returns.md`"，而占比类字段（`cost_ratio` / `market_value_ratio`）的 null 规则只在 dashboards 里存在——两边互相引用，谁都不是权威。必须出一张统一的 null 真值表，写进 returns，dashboards 引用它。

**4. 缺 4 个页面级接口，其中净值查询是硬缺。**
`v1-nav-history.md` 只有写入、没有读取，导入后无法核对；HistoryView 需要的"按日期区间的收益/持仓序列"完全不存在；SettingsView 在 6 份文档里一个接口都没有；ImportView 只有净值导入，操作记录没有导入入口。

**5. 有两条必须最先定，否则第一天联调就卡死：时区和全局异常 JSON。**
所有"不能晚于今天"、`observe_days`、`created_at` 都依赖时区定义；Flask 默认对 404 / 405 / 500 / 非法 JSON 返回 HTML 错误页，前端 axios 会直接崩。这两条不在 6 份文档的任何一份里。

---

## 二、阻塞开发的缺口

> 每条格式：涉及接口 / 缺什么 / 不写会导致后端怎么瞎猜 / 建议口径。

### 2.1 时区与"今天"的定义

- **涉及接口**：全部。「不能晚于今天」出现在 operations、nav-history、snapshots、returns、dashboards 五处；`observe_days` 出现在 bloggers。
- **缺什么**：没定义"今天"按哪个时区算，也没定义返回的时间戳是本地时间还是 UTC。
- **瞎猜后果**：服务器跑在 UTC 容器里时，北京时间 08:00 之前提交的"今天"操作会被判为未来日期而拒绝；`created_at` 差 8 小时，前端显示的时间对不上。
- **建议口径**：一律以服务器本地时区（Asia/Shanghai）的当天日期为准，不使用 UTC；所有返回的 `created_at` / `updated_at` 为服务器本地时间，格式 `YYYY-MM-DD HH:mm:ss`，不带时区偏移。`observe_days = DATEDIFF(今天, observe_start_date)`，不含当天，观察开始日当天为 `0`。

### 2.2 全局异常响应的 JSON 兜底

- **涉及接口**：全部。
- **缺什么**：请求体是非法 JSON 时、路径不存在时、方法不允许时、未捕获异常时，返回什么结构。
- **瞎猜后果**：Flask 默认返回 HTML 错误页，前端 `response.data` 拿到的是 HTML 字符串，解析崩溃；新手不会主动注册全局 errorhandler。
- **建议口径**：注册全局错误处理器，四类场景统一返回 JSON（结构同 1.4，`details` 固定为 `[]`）：

  | 场景 | HTTP | code |
  | --- | --- | --- |
  | 请求体不是合法 JSON | 400 | `INVALID_JSON` |
  | 请求路径不存在 | 404 | `ENDPOINT_NOT_FOUND` |
  | 请求方法不被允许 | 405 | `METHOD_NOT_ALLOWED` |
  | 未捕获异常 | 500 | `INTERNAL_ERROR` |

### 2.3 CORS

- **涉及接口**：全部。
- **缺什么**：6 份文档一份都没提跨域。
- **瞎猜后果**：前端 localhost:5173 请求后端 127.0.0.1:5000 全部被浏览器拦掉，新手会以为是接口写错了，排查半天。
- **建议口径**：后端启用 `flask-cors`，允许来源 `http://localhost:5173`，允许方法 `GET/POST/PUT/DELETE/OPTIONS`，允许请求头 `Content-Type`，不发送凭据。

### 2.4 错误码取值域不封闭，且没有统一的 HTTP 映射

- **涉及接口**：全部。
- **缺什么**：`v1-basic-management.md` 1.6 列了 8 个错误码，没写每个码对应哪个 HTTP 状态码；`v1-operations.md` 自己加了 `OPERATION_NOT_FOUND`；`v1-nav-history.md` 只列 3 个，但 CSV 导入的"文件为空""不是 CSV""超 1000 行"没有码可用；全局新增的 4 个码没人登记。
- **瞎猜后果**：同名博主冲突返回 400 还是 409，新手随便挑；CSV 文件类错误只能挤进 `VALIDATION_ERROR`，前端靠 `message` 文案区分，一改文案就崩。
- **建议口径**：在基础文档建一张全项目唯一的错误码总表（见 5.1），其他模块一律引用，不再自建。

### 2.5 `details` 元素结构与多字段校验行为

- **涉及接口**：全部。
- **缺什么**：`v1-basic-management.md` 定义 `details[]` 元素是 `{field, message}`；`v1-nav-history.md` 的 CSV 错误用了 `{row, field, message}`。`row` 从 1 开始还是从 0 开始、含不含表头，没写。多字段同时出错时返回第一条还是全部，没写。
- **瞎猜后果**：前端 TypeScript 类型定义要么缺 `row` 要么强行可空；批量导入 1000 行全错时返回一个巨大的 JSON；用户改一个字段提交一次才看到下一个错。
- **建议口径**：`details[]` 元素为 `{field: string（必填）, message: string（必填）, row?: int（仅批量导入，行号从 1 开始且不含表头）}`；多字段同时失败时**一次性返回全部错误**，不短路；批量导入时 `details` 最多返回前 50 条并额外返回 `error_count`。

### 2.6 数值精度、四舍五入模式、JSON 序列化

- **涉及接口**：全部（跨 6 份文档，只有 returns 写了）。
- **缺什么**：① 只有 `v1-returns.md` 写了"金额 2 位、份额 4 位、收益率 6 位"，净值 `nav` 的小数位**没有任何文档定义**；② 没写四舍五入模式，Python `Decimal.quantize()` 默认是 `ROUND_HALF_EVEN`（银行家舍入），与文档写的"四舍五入"不符；③ 没说明 JSON number 序列化**不保留尾随零**——`27940.00` 序列化后是 `27940`。
- **瞎猜后果**：净值精度不定，市值精度跟着飘；`0.5` 边界上前后端算出的数不一样；前端拿不到 `27940.00`，会回头要求后端改字符串，扯皮一轮。
- **建议口径**：见 5.1 的「1.11 数值精度与序列化」。核心三条：一律 `Decimal` 不用 `float`；四舍五入模式固定 `ROUND_HALF_UP`；**小数位约束的是后端计算精度，不是 JSON 字面量位数，前端自行格式化展示**。

### 2.7 数据库列精度、字符串长度上限、trim

- **涉及接口**：bloggers / funds / initial-positions / operations / nav-history。
- **缺什么**：只说"落库时使用 DECIMAL"，没给位数；`bloggers.name`、`sector`、`funds.name`、`fund_code` 的长度上限全都没定义（只有 `operations.remark` 写了 255）；字符串入参要不要 trim 没写。
- **瞎猜后果**：新手定义 `DECIMAL(10,2)`，成本累加到大额时溢出；`name` 定义 `VARCHAR(20)`，长基金名被静默截断；`" 基金小星 "` 和 `"基金小星"` 被当成两个博主。
- **建议口径**：见 5.1 的「1.11 / 1.12」。

### 2.8 分页越界：`page` 超过最大页码

- **涉及接口**：`GET /bloggers`、`GET /funds`、`GET /initial-positions`、`GET /operations`。
- **缺什么**：四份文档都只写了 `page` 最小值 1、`page_size` 上限 100，**没写 `page` 超过总页数时返回什么**。
- **瞎猜后果**：三种实现都会出现——返回空列表、自动截断到最后一页、返回 400 报错。前端"最后一页删除最后一条"的场景直接崩。
- **建议口径**：返回 HTTP 200，`items` 为空数组，`total` 为真实总数，`page` 和 `page_size` 回显请求值。**不报错，不截断。**

### 2.9 非法排序字段、非法枚举筛选值、默认排序

- **涉及接口**：`GET /bloggers`（有 `sort_by`/`order` 但没写非法值行为、没写默认排序）、`GET /initial-positions`（没写默认排序）、`GET /funds`（没提排序参数）。
- **缺什么**：`v1-operations.md` 明确写了"白名单校验，非白名单返回 400，不允许拼接进 SQL"，`v1-basic-management.md` **没写**。`GET /bloggers` 支持 4 个 `sort_by` 值但没给默认值。`status` 传 `deleted` 会怎样没写。
- **瞎猜后果**：最坏情况是新手直接把 `sort_by` 拼进 SQL —— **SQL 注入**；好一点的是静默忽略，前端排序按钮点了没反应。
- **建议口径**：所有 `sort_by` / `order` / 枚举筛选参数一律白名单校验，非法值返回 400 / `VALIDATION_ERROR`；禁止拼接进 SQL；每个列表接口必须在文档里写出默认排序。

### 2.10 筛选类参数指向不存在的外键：空列表还是 404

- **涉及接口**：`GET /initial-positions?blogger_id=999`、`GET /operations?blogger_id=999`。
- **缺什么**：`v1-operations.md` 写了"筛选条件指向不存在的博主或基金时，返回空列表，不返回 404"；`v1-basic-management.md` 的 `GET /initial-positions` **没写**。
- **瞎猜后果**：同一个项目里，一个列表返回空、另一个返回 404，前端要写两套错误处理。
- **建议口径**：**筛选类参数一律返回空列表（HTTP 200）；写入类参数（`POST`/`PUT`/路径参数）一律返回 404。** 这条要写进全局约定，不是写进单个接口。

### 2.11 唯一性比较规则，以及编辑时是否排除自身

- **涉及接口**：`POST/PUT /bloggers`、`POST/PUT /funds`、`PUT /initial-positions`。
- **缺什么**：① 唯一性比较要不要 trim、区不区分大小写，没写（MySQL 默认 `utf8mb4_general_ci` 是**不区分**大小写）；② **编辑接口做唯一校验时是否排除当前记录自己，没写**。
- **瞎猜后果**：第 ② 条是必现 bug：用户只改板块不改名称点保存，后端查到"自己"这条记录，返回 `BLOGGER_NAME_DUPLICATED`，编辑功能直接不可用。
- **建议口径**：先 `strip()` 再比较，不区分大小写；编辑接口唯一校验必须**排除当前记录主键**（`WHERE name = ? AND blogger_id != ?`）。

### 2.12 `observe_start_date` 晚于今天，以及派生字段的排序映射

- **涉及接口**：`POST/PUT /bloggers`、`GET /bloggers`（`sort_by=observe_days`、`status` 筛选）。
- **缺什么**：① 观察开始日能不能是未来日期，没写；② `observe_days` 和 `status` 是不落库的派生字段，但列表支持按它们排序和筛选，**没给 SQL 表达式映射**。
- **瞎猜后果**：未来日期导致 `observe_days` 为负、`status` 落在两个分支之外，前端显示"-5 天"；派生字段排序新手会先查出来在 Python 里排 —— 那样分页就是错的。
- **建议口径**：`observe_start_date` 不能晚于今天，返回 400；派生字段排序统一用 `DATEDIFF(CURDATE(), observe_start_date)`，映射表见 5.1。

### 2.13 平均成本法的公式

- **涉及接口**：`POST /operations`（卖出）、持仓快照、收益。
- **缺什么**：`v1-position-snapshots.md` 业务规则 4 只有一句"卖出使用平均成本法"，**没有公式**。卖出前份额为 0 时、为负时怎么算，没写。
- **瞎猜后果**：新手会写出"卖出成本 = 卖出份额 × 最后一次买入单价""按卖出金额等比例扣成本""份额为 0 时除零崩溃"等各种版本。这是整个系统最核心的数字，不能靠猜。
- **建议口径**：见 5.2 的「4.1」，含份额为 0 和负数两条边界。

### 2.14 同一天多笔操作的计算顺序

- **涉及接口**：持仓快照、收益（所有涉及成本计算的接口）。
- **缺什么**：同一 `operation_date` 有先买后卖、或先卖后买两笔时，按什么顺序计算，没写。
- **瞎猜后果**：数据库返回顺序不保证稳定，同一份数据在不同查询时刻给出不同的成本。这种 bug 极难复现。
- **建议口径**：同一天内按 `operation_id` 升序依次计算（即录入顺序），买入卖出不做类型优先级重排。

### 2.15 多条初始持仓时，`operation_date` 下界取哪一条

- **涉及接口**：`POST /operations`、持仓快照、收益。
- **缺什么**：`v1-operations.md` 说"`operation_date` 不能早于该博主该基金的初始持仓记录日期"，但唯一约束只保证"同博主+同基金+同日期"唯一，**同一博主同一基金可以有多条不同日期的初始持仓**。有多条时取哪条做下界，没写。
- **瞎猜后果**：取最早一条、取最晚一条、取任意一条，三种实现都合法，导致不同环境下同一条操作有的能录有的不能录。
- **建议口径**：取 **`record_date` 最早的一条**，与持仓快照的起点口径保持一致。

### 2.16 快照 `items` 的集合定义、排序、以及"无初始持仓"时的字段值

- **涉及接口**：`GET /bloggers/{blogger_id}/position-snapshots`。
- **缺什么**：① `items` 到底包含哪些基金（有初始持仓的？有操作的？并集？）没写；② 排序没写；③ 没有初始持仓时 `initial_record_date` 为 `null` 写了，但 `initial_shares` / `initial_cost_amount` 是 `0` 还是 `null` 没写；④ 份额被卖到 0 的基金要不要从 `items` 里剔除，没写；⑤ `snapshot_date` 早于初始持仓 `record_date` 时怎么办，没写。
- **瞎猜后果**：新手大概率会把"没有初始持仓"统一返回 `null`，前端做加法时炸；把卖光的基金剔除，前端看不到"已清仓"记录。
- **建议口径**：见 5.4 的补充业务规则 8–15。

### 2.17 CSV 导入的失败策略只写了一半

- **涉及接口**：`POST /api/v1/nav-history/import`。
- **缺什么**：写了"只要有一行错误，整批导入失败"，但：① **没写是否事务回滚**，新手可能边校验边写，导致前 500 行落库、第 501 行报错，数据脏了；② 响应字段 `total_rows` / `processed_rows` 在全失败模式下永远相等，`processed_rows` 语义是废的（文档内部矛盾）；③ 超 1000 行、非 CSV 文件、文件过大、缺列、多余列、空行、编码失败、净值超 4 位小数，全部没定义行为。
- **瞎猜后果**：导入一次脏一批数据，而且没有删除接口（文档明确不做），只能改数据库。
- **建议口径**：见 5.3 的「CSV 导入的失败策略（补充）」，共 14 条。

### 2.18 现金分红是否计入收益，以及成本 ≤ 0 时的完整返回

- **涉及接口**：`v1-returns.md` 全部三个接口、dashboards。
- **缺什么**：① 现金分红拿走的是现金，但收益公式 `profit = 市值 - 成本` 里完全没有它，分红的钱"消失"了——文档没说明这是故意的还是漏了；② "成本 ≤ 0 时收益率返回 `null`"写了，但同一场景下 `market_value` 和 `profit_amount` 返回什么**没写**。
- **瞎猜后果**：第 ① 条会让验收时有人问"分红 120 元去哪了"；第 ② 条新手会把整行都返回 `null`，前端连市值都看不到。
- **建议口径**：见 5.5 的「2.4 null 真值表」和「2.5 现金分红的收益归属」。

---

## 三、接口之间的口径冲突

**冲突 1（硬，必须解决）：多条初始持仓的计算口径，快照和收益不一致。**
`v1-position-snapshots.md` 业务规则 3：同一 `blogger_id + fund_id` 有多条初始持仓时**取最早一条作为起点**（暗示其余忽略）。
`v1-returns.md` 业务规则 1：只统计 `return_date` **当天或之前**的初始持仓和操作记录（即所有符合条件的初始持仓都要算）。
→ 同一博主同一天，快照接口的 `shares`/`cost_amount` 与收益接口的 `shares`/`cost_amount` 会不一致。
**判据**：`v1-dashboards.md` 明确要求"必须复用同一套计算逻辑（`calculate_position_snapshots()` + ...），不要另写一套收益算法"。因此以快照为准。
**怎么改**：改成"只取 `record_date` 最早的一条，其余初始持仓完全不参与计算（不累加份额、不累加成本）"，并在 returns 文档里显式声明这条覆盖原业务规则 1 的"初始持仓"部分。条款原文见 5.5 的 2.6。

**冲突 2（硬）：超额卖出导致的负成本，与"成本 ≤ 0 收益率返回 null"之间没有衔接。**
`v1-operations.md` 业务规则 8 说超额卖出会让"成本出现 0 或负数"；`v1-position-snapshots.md` 规则 6 说"成本也可以为 0 或负数"；但 `v1-returns.md` 只说"成本小于等于 0 时收益率返回 null"，**没说 `cost_amount` 本身照实返回负数还是截断到 0**。
**怎么改**：照实返回负数，不截断、不抛异常；只有 `return_rate` 为 `null`。写进 null 真值表。

**冲突 3（硬）："无持仓返回 0" 与 "缺净值返回 null" 之间少一格。**
`v1-returns.md` 2.1 表格里，"没有任何持仓数据 → 总成本/总市值/收益金额返回 `0`，收益率 `null`"，而"任意一个基金缺当天净值 → 总市值/总收益/总收益率返回 `null`"。
但"**有持仓，且所有基金都缺净值**"这一格没有定义。`v1-returns.md` 的空数据示例里 `total_market_value: 0.00` 会被新手误读成"缺净值也返回 0"，与已确认口径（缺净值必须 `null`）直接冲突。
**怎么改**：补 null 真值表，明确 `0` 只出现在"根本没有任何持仓"这一格。

**冲突 4（硬）：null 口径的层级没分层，且 returns 与 dashboards 循环引用。**
`v1-dashboards.md` 1.3-3 说"某只基金缺净值时，**只有它自己**的市值等返回 null，其他有净值的基金照实返回"；`v1-returns.md` 2.1 说"任意一个基金缺当天净值 → **总**市值、总收益金额、总收益率返回 null"。
两者其实是"基金级 vs 汇总级"的区别，但**两份文档都没有显式分层**，新手只会二选一。
更麻烦的是：`v1-dashboards.md` 1.3 开头写"收益和空值口径沿用 `v1-returns.md`"，而 `cost_ratio` / `market_value_ratio` 的 null 规则**只存在于 dashboards**——互相引用，谁都不是权威。
**怎么改**：在 returns 建 null 真值表（基金级/博主级/全局级三层），dashboards 显式写明"本文档 1.3 是对该真值表在本接口的展开，冲突时以 returns 的真值表为准"。

**冲突 5：409 的存在性，全局约定与模块约定打架。**
`v1-basic-management.md` 1.5 定义了 409（业务冲突），1.6 定义了三个 `*_DUPLICATED` 错误码但没标 HTTP 码；`v1-operations.md` 1.2 明确"本模块没有 409"。
模块级覆盖全局级是合理的，但**全局文档里没有登记这条覆盖**，新手按全局表给操作记录配 409 完全合理。
**怎么改**：在全局错误码总表里标注每个码的适用模块（见 5.1）。

**冲突 6：净值到底有没有查询接口，无法从文档判定。**
`v1-nav-history.md` 明确"第一版没有净值删除接口和净值编辑接口"，**没说没有查询接口**；而接口总览里确实只有两个 POST。
这种"声明了 A 和 B 不做、没声明 C 不做但也没定义 C"的写法，让"没有 GET"到底是遗漏还是故意变成悬案。
**怎么改**：要么补上 GET 接口（建议，见 5.3），要么在文档里明确写"第一版不提供净值查询接口"。

**冲突 7：金额单位只在一份文档里声明。**
`v1-operations.md` 写"`amount` 金额，单位元"；`initial_positions.cost_amount`、`nav`、`market_value`、`total_cost_amount` 等全都没写单位。
**怎么改**：全局约定里统一声明"所有金额单位为元"。

**冲突 8（轻）：`shares` 字段的示例小数位有三种写法。**
`v1-operations.md` 示例 `1000.0`、`v1-position-snapshots.md` 示例 `1000`、`v1-dashboards.md` 示例 `1000.0000`。同一个字段三种写法，前端会问"到底几位"。
**怎么改**：统一到份额 4 位；示例全部改成 4 位；并声明 JSON 序列化不保留尾随零（见 5.1 的 1.11）。

---

## 四、缺少的接口

> 依据：`frontend/src/views/` 下有 OverviewView、BloggerDetailView、ImportView、HistoryView、SettingsView 五个页面。

**1. `GET /api/v1/nav-history` 净值列表查询 —— 硬缺。**
净值模块只有写入（单条 upsert + CSV 导入），没有任何读取接口。后果：ImportView 导入 1000 行后无法核对、无法展示；录错了也不知道（且没有编辑/删除接口）；用户不知道某只基金哪些日期已有净值。这是最该补的一个。接口草稿见 5.3。

**2. HistoryView 需要的"时间序列"接口 —— 完全缺失。**
HistoryView 要展示历史走势，但：`v1-position-snapshots.md` 明确"第一版不提供持仓快照历史持久化"，`v1-returns.md` 三个接口全部只支持**单日**查询（一个 `return_date`），没有任何按日期区间返回序列的接口。
**两个选择，必须现在定一个并写进文档**：
- 补 `GET /api/v1/bloggers/{blogger_id}/return-series?date_from=&date_to=`（按天返回成本/市值/收益率序列，缺净值的那天为 `null`）；或
- 明确"第一版 HistoryView 只展示操作记录历史"，复用 `GET /api/v1/operations`（有 `date_from`/`date_to`）和 `GET /api/v1/dashboards/recent-operations`。
不要让新手自己决定。

**3. SettingsView —— 6 份文档里一个接口都没有。**
至少缺两个：
- `GET /api/v1/meta/sectors`：博主板块的可选值列表。`GET /bloggers?sector=` 要求**精确筛选**，但没有任何接口能告诉前端有哪些板块，下拉框只能硬编码或从现有博主聚合。
- 数据导出 / 数据清空 / 默认查询日期之类的设置项，需要明确第一版是否做；不做就在文档里写死"SettingsView 第一版为纯前端页面，无后端接口"。

**4. ImportView：只有净值导入，操作记录没有批量导入。**
`v1-nav-history.md` 有 CSV 导入，`v1-operations.md` 只有单条 `POST`。如果 ImportView 打算支持操作记录导入（这是最需要导入的数据类型），需要补 `POST /api/v1/operations/import`，口径可以直接复用净值导入的 14 条失败策略（列：`blogger_name` 或 `blogger_id`、`fund_code` 或 `fund_id`、`operation_type`、`operation_date`、`shares`、`amount`、`remark`）。

**5. 已声明不做、但要在任务文档里写清楚的缺口（不是 bug）。**
- 净值无删除/编辑接口 → 净值录错第一版无法修正。
- 操作记录无编辑接口 → 只能删除重录。
- 初始持仓无删除接口 → 只能编辑。
这三条要在下发给新手的任务文档里显式列为"已知限制"，避免他自己"好心"加上去。

---

## 五、建议补写的条款清单

> 以下每一节都可以整段复制进对应文档。小节编号按现有文档的顺序接排，落位已标注。

### 5.1 补进 `docs/api/v1-basic-management.md`

**落位：第 1 章「全局约定」，在 1.6 之后新增 1.7–1.15。**

```markdown
### 1.7 时区与日期基准

1. 所有"今天"一律指**服务器本地时区（Asia/Shanghai）的当天日期**，不使用 UTC。
2. 所有返回的 `created_at` / `updated_at` 使用服务器本地时间，格式 `YYYY-MM-DD HH:mm:ss`，不带时区偏移。
3. `observe_days = DATEDIFF(今天, observe_start_date)`，即两个日期相差的自然日数，不含当天。观察开始日当天 `observe_days` 为 `0`。
4. 文档中出现的"不能晚于今天"一律按本条判定。

---

### 1.8 全局异常响应

以下场景由全局错误处理器统一返回 JSON，**不允许返回 Flask 默认的 HTML 错误页**：

| 场景 | HTTP 状态码 | code |
| --- | --- | --- |
| 请求体不是合法 JSON | 400 | `INVALID_JSON` |
| 请求路径不存在 | 404 | `ENDPOINT_NOT_FOUND` |
| 请求方法不被允许 | 405 | `METHOD_NOT_ALLOWED` |
| 未捕获异常 | 500 | `INTERNAL_ERROR` |

响应体结构与 1.4 一致，`details` 固定为 `[]`。

---

### 1.9 错误码总表（全项目唯一）

| 错误码 | HTTP 状态码 | 说明 | 适用模块 |
| --- | --- | --- | --- |
| `VALIDATION_ERROR` | 400 | 参数校验失败（含 CSV 文件类错误） | 全部 |
| `INVALID_JSON` | 400 | 请求体不是合法 JSON | 全局 |
| `BLOGGER_NOT_FOUND` | 404 | 博主不存在 | 基础管理、操作记录、持仓快照、收益 |
| `FUND_NOT_FOUND` | 404 | 基金不存在；在收益模块中同时表示"该博主未持有该基金" | 基础管理、操作记录、净值、收益 |
| `INITIAL_POSITION_NOT_FOUND` | 404 | 初始持仓不存在 | 基础管理 |
| `OPERATION_NOT_FOUND` | 404 | 操作记录不存在 | 操作记录 |
| `BLOGGER_NAME_DUPLICATED` | 409 | 博主名称重复 | 基础管理 |
| `FUND_CODE_DUPLICATED` | 409 | 基金代码重复 | 基础管理 |
| `INITIAL_POSITION_DUPLICATED` | 409 | 同一博主、同一基金、同一记录日期的初始持仓已存在 | 基础管理 |
| `ENDPOINT_NOT_FOUND` | 404 | 请求路径不存在 | 全局 |
| `METHOD_NOT_ALLOWED` | 405 | 请求方法不被允许 | 全局 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 | 全部 |

1. 各模块文档中的"本模块错误码"表只能从本表引用，不得新增本表之外的错误码。
2. 操作记录模块不使用 409（同一博主、同一基金、同一天允许多笔操作）。
3. `FUND_NOT_FOUND` 在收益模块被复用为"该博主未持有该基金"，两种语义共用同一错误码，靠 `message` 区分。

---

### 1.10 通用查询参数规则

所有带分页的列表接口（`/bloggers`、`/funds`、`/initial-positions`、`/operations`、`/nav-history`）统一遵守：

1. `page` 默认 `1`，必须 ≥ 1。
2. `page_size` 默认 `20`，范围 1–100。
3. **`page` 超过最大页码时，返回 HTTP 200，`items` 为空数组，`total` 为真实总数，`page` 和 `page_size` 回显请求值。** 不报错，不自动截断到最后一页。
4. `sort_by` 和 `order` 使用**白名单校验**；不在白名单内一律返回 HTTP 400 / `VALIDATION_ERROR`，**禁止拼接进 SQL**。
5. 枚举类筛选参数（`status`、`operation_type` 等）取值不在允许范围内时，同样返回 400 / `VALIDATION_ERROR`，不得静默忽略。
6. 每个列表接口必须在文档中写明**默认排序**。
7. **筛选类参数**（query string 里的可选筛选项）指向不存在的资源时，返回空列表，HTTP 200，不返回 404。**写入类参数**（请求体字段、路径参数）指向不存在的资源时，返回 404。

---

### 1.11 数值精度与序列化

1. 后端所有金额、份额、净值、比率的计算一律使用 `Decimal`，**禁止使用 `float`**。
2. 四舍五入模式统一为 `ROUND_HALF_UP`（`decimal.ROUND_HALF_UP`），不使用 Python 默认的 `ROUND_HALF_EVEN`。
3. 四舍五入精度：

   | 类别 | 小数位 | 涉及字段 |
   | --- | --- | --- |
   | 金额 | 2 | `cost_amount`、`amount`、`market_value`、`profit_amount`、`total_cost_amount`、`total_market_value`、`buy_amount`、`sell_amount`、`dividend_cash_amount`、`initial_cost_amount` |
   | 份额 | 4 | `shares`、`initial_shares`、`buy_shares`、`sell_shares` |
   | 净值 | 4 | `nav` |
   | 比率 | 6 | `return_rate`、`cost_ratio`、`market_value_ratio` |

4. **JSON 序列化不保留尾随零**：`27940.00` 序列化后是 `27940`，`0.090909` 保持 `0.090909`。上表约束的是**后端计算与四舍五入的精度**，不是 JSON 字面量的位数。前端负责展示格式化（金额补 2 位小数、比率转成百分比）。
5. 数据库列精度：金额 `DECIMAL(20,4)`、份额 `DECIMAL(20,4)`、净值 `DECIMAL(12,4)`、比率 `DECIMAL(20,8)`。返回值按上表在返回前二次四舍五入。
6. 所有金额单位为**元**。

---

### 1.12 文本字段规则

1. 所有字符串入参在校验和落库前先 `strip()` 去首尾空格；去空格后为空的，按"不能为空"返回 `VALIDATION_ERROR`。
2. 唯一性比较基于 `strip()` 后的值。
3. MySQL 使用默认 `utf8mb4_general_ci` 排序规则，**唯一性比较不区分大小写**：`ABC` 与 `abc` 视为重复。
4. 字段长度上限：`bloggers.name` 64、`bloggers.sector` 32、`funds.name` 64、`funds.fund_code` 32、`operations.remark` 255。超出返回 `VALIDATION_ERROR`。

---

### 1.13 CORS

第一版前端运行在 `http://localhost:5173`，后端运行在 `http://127.0.0.1:5000`，属于跨源。后端必须启用 `flask-cors`：

- 允许来源：`http://localhost:5173`
- 允许方法：`GET`、`POST`、`PUT`、`DELETE`、`OPTIONS`
- 允许请求头：`Content-Type`
- 不发送凭据（`supports_credentials=False`）

---

### 1.14 `code` 字段类型

- 成功时 `code` 是**数字** `0`。
- 失败时 `code` 是**字符串**错误码。
- 前端判断成功用 `code === 0`；TypeScript 类型定义为 `number | string`。

---

### 1.15 `details` 元素结构

| 字段 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| field | string | 是 | 出错的字段名 |
| message | string | 是 | 用户可读提示 |
| row | int | 否 | 行号，从 1 开始且**不含表头**；仅批量导入接口返回 |

1. 多个字段同时校验失败时，**一次性返回全部错误**，不要短路到第一条。
2. 批量导入时 `details` 最多返回前 50 条错误，并在响应中额外返回 `error_count`（错误总行数）。
```

**落位：3.1「查询博主列表」业务规则，在现有 6 条之后追加。**

```markdown
7. 默认排序：`created_at` 降序。`sort_by` 与排序表达式的映射固定为：

   | sort_by | 排序表达式 |
   | --- | --- |
   | name | `bloggers.name` |
   | observe_start_date | `bloggers.observe_start_date` |
   | observe_days | `DATEDIFF(CURDATE(), observe_start_date)` |
   | created_at | `bloggers.created_at` |

8. 同一排序值内按 `blogger_id` 降序，保证分页稳定。
9. `keyword` 为空字符串时视为不筛选。`LIKE` 匹配前对 `%` 和 `_` 做转义。
10. `status` 取值不在 `observing` / `active` 内时，返回 400 / `VALIDATION_ERROR`。
11. `page` 超过最大页码时按 1.10 第 3 条处理。
```

**落位：3.2「新增博主」和 3.4「编辑博主」业务规则。**

```markdown
<!-- 3.2 新增博主，追加 -->
6. `observe_start_date` 不能晚于今天，否则返回 400 / `VALIDATION_ERROR`，`message` 为「观察开始日不能晚于今天」。理由：观察天数为负数时 `status` 无法给出可解释的取值。
7. 名称唯一性校验按 1.12 执行（先 `strip()`，不区分大小写）。

<!-- 3.4 编辑博主，追加 -->
4. **唯一性校验必须排除当前记录自己**：按 `name = ? AND blogger_id != ?` 查询。不排除会导致"只改板块或观察开始日、不改名称"时错误返回 `BLOGGER_NAME_DUPLICATED`。
```

**落位：4.1「查询基金列表」业务规则。**

```markdown
4. 基金列表第一版**不支持** `sort_by` 和 `order` 参数；传了返回 400 / `VALIDATION_ERROR`，不做静默忽略。
5. `keyword` 为空字符串时视为不筛选。`LIKE` 匹配前对 `%` 和 `_` 做转义。
```

**落位：4.3「编辑基金」业务规则。**

```markdown
4. **唯一性校验必须排除当前记录自己**：按 `fund_code = ? AND fund_id != ?` 查询。
```

**落位：5.1「查询初始持仓列表」业务规则。**

```markdown
4. 默认排序：`record_date` 降序，同一天内按 `initial_position_id` 降序。
5. 传入不存在的 `blogger_id` 或 `fund_id` 时，返回空列表 + `total = 0`，HTTP 200，不返回 404（见 1.10 第 7 条）。
6. `shares` 保留 4 位小数，`cost_amount` 保留 2 位小数（见 1.11）。
```

**落位：5.3「编辑初始持仓」业务规则，在现有 5 条之后追加。**

```markdown
6. **唯一性校验必须排除当前记录自己**：按 `blogger_id = ? AND fund_id = ? AND record_date = ? AND initial_position_id != ?` 查询。
7. 未修改任何业务字段时，正常返回更新后的数据，不返回错误。
```

---

### 5.2 补进 `docs/api/v1-operations.md`

**落位：第 3 节之后、第 4 节之前，新增独立的「4. 平均成本法与计算顺序」，原 4/5/6 节顺延。**

```markdown
## 4. 平均成本法与计算顺序

### 4.1 卖出成本的计算

卖出时用卖出前的平均单位成本折算本次卖出份额对应的成本：

```
卖出前平均单位成本 = 卖出前累计成本 / 卖出前累计份额
本次卖出成本       = 本次卖出份额 × 卖出前平均单位成本
卖出后累计份额     = 卖出前累计份额 - 本次卖出份额
卖出后累计成本     = 卖出前累计成本 - 本次卖出成本
```

边界：

1. **卖出前累计份额 ≤ 0 时**（含 0 和负数），本次卖出成本记为 `0`，累计成本保持不变，只减少份额，不抛除零异常。理由：份额 ≤ 0 时"平均单位成本"没有经济含义，按公式继续计算会把无意义的数字放大。**（2026-10-28 裁决：本条取代原"份额为 0"和"份额为负仍按公式计算"两条。负份额后再卖的成本以任务 030 已实现、045 已锁定的口径为准——成本不变、只减份额。）**
2. 卖出后累计成本出现 `0` 或负数时**照实返回**，不截断、不抛异常。后续收益率计算按 `v1-returns.md` 的 null 真值表处理。

### 4.2 同一天多笔操作的计算顺序

同一 `operation_date` 内有多笔操作时，**按 `operation_id` 升序依次计算**（即录入顺序）。买入和卖出不做类型优先级重排。

理由：平均成本法对同日操作的先后顺序敏感；不固定顺序会导致同一份数据在不同查询时刻给出不同的成本。

### 4.3 操作日期下界取哪条初始持仓

当同一 `blogger_id + fund_id` 存在多条初始持仓时，`operation_date` 的下界取 **`record_date` 最早的一条**，与持仓快照的计算起点口径一致（见 `v1-position-snapshots.md` 业务规则 3）。

### 4.4 现金分红对成本的影响

现金分红（`dividend_cash`）**不改变份额，也不改变成本**。`dividend_cash_amount` 只在持仓快照和操作统计中累加体现，不参与平均成本计算。
```

**落位：第 4 节「新增操作记录」业务规则，在现有 9 条之后追加。**

```markdown
10. `amount` 单位是**元**。
11. `shares` 保留 4 位小数，`amount` 保留 2 位小数，四舍五入模式 `ROUND_HALF_UP`（见 `v1-basic-management.md` 1.11）。
12. `remark` 不传或传 `null` 时存储为 `NULL`，响应中返回 `null`（不是空字符串）；传空字符串时按空字符串存储，响应中返回 `""`。
13. `dividend_cash` 不传 `shares` 时后端补 `0`，响应中返回 `0`。
14. `operation_date` 不设下界（有初始持仓时下界为初始持仓最早 `record_date`，无初始持仓时不限制）。
15. 同一 `fund_id + nav_date` 的净值与本接口无关，本接口不校验净值是否存在。
```

**落位：第 5 节「查询操作记录列表」业务规则，在现有 7 条之后追加。**

```markdown
8. `page` 超过最大页码时返回空 `items` + 真实 `total`，HTTP 200，不报错（见 `v1-basic-management.md` 1.10 第 3 条）。
9. 传入不存在的 `blogger_id` / `fund_id` 时返回空列表，HTTP 200，不返回 404。
10. `keyword` 为空字符串时视为不筛选。`LIKE` 匹配前对 `%` 和 `_` 做转义。
11. `shares` 返回 4 位小数，`amount` 返回 2 位小数。
```

---

### 5.3 补进 `docs/api/v1-nav-history.md`

**落位：第 2 节「接口总览」，新增第 3 行。**

```markdown
| 3 | 查询净值列表 | GET | `/api/v1/nav-history` |
```

**落位：第 5 节之前，新增「5. 查询净值列表」整节（原 5/6 节顺延为 6/7）。**

```markdown
## 5. 查询净值列表

### 接口名称

查询净值列表 / `list_nav_history`

### 请求方法与路径

```http
GET /api/v1/nav-history
```

### 功能说明

分页查询已录入的净值记录，用于导入后核对和历史净值查看。

### 请求参数

全部通过 query string 传递，全部可选。

| 字段 | 类型 | 是否必填 | 默认值 | 示例值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| fund_id | int | 否 | 无 | `1` | 按基金筛选，必须为正整数 |
| nav_date | string | 否 | 无 | `2026-09-30` | 按单个净值日期精确筛选 |
| date_from | string | 否 | 无 | `2026-09-01` | 起始净值日期，含当天 |
| date_to | string | 否 | 无 | `2026-09-30` | 结束净值日期，含当天 |
| page | int | 否 | `1` | `1` | 页码，必须 ≥ 1 |
| page_size | int | 否 | `20` | `20` | 每页条数，范围 1–100 |

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| data.items | array | 净值数组，元素结构见第 3 节 |
| data.page | int | 当前页码 |
| data.page_size | int | 每页条数 |
| data.total | int | 符合筛选条件的总条数 |

### 成功响应示例

HTTP 状态码 `200`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "nav_id": 1,
        "fund_id": 1,
        "fund_name": "华夏成长混合",
        "fund_code": "000001",
        "nav_date": "2026-09-30",
        "nav": 1.2345,
        "created_at": "2026-09-30 10:00:00",
        "updated_at": "2026-09-30 10:00:00"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

### 错误响应示例

日期区间颠倒，HTTP `400`：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "details": [
    {
      "field": "date_from",
      "message": "date_from 不能晚于 date_to"
    }
  ]
}
```

### 业务规则

1. 默认排序：`nav_date` 降序，同一天内按 `fund_id` 升序。
2. `nav_date` 与 `date_from` / `date_to` 同时传时，以 `nav_date` 为准，`date_from` / `date_to` 忽略。
3. `date_from` 不能晚于 `date_to`。
4. 传入不存在的 `fund_id` 时返回空列表，HTTP 200，不返回 404。
5. `page` 超过最大页码时按 `v1-basic-management.md` 1.10 第 3 条处理。
6. `nav` 返回 4 位小数。

### 关联接口

- 录入或更新净值：`POST /api/v1/nav-history`
- 批量导入净值：`POST /api/v1/nav-history/import`
```

**落位：原第 5 节「批量导入净值」业务规则，整段替换为以下内容。**

```markdown
### 业务规则

1. CSV 必须**恰好**包含 `fund_code`、`nav_date`、`nav` 三列（列顺序不限）。缺列返回 `VALIDATION_ERROR`；多余的列**忽略**，不报错。
2. 后端根据 `strip()` 后的 `fund_code` 查找 `fund_id`；找不到时整批导入失败。
3. **整批失败、整批回滚。** 只要任意一行校验失败，整个导入在同一个数据库事务内回滚，**一行都不落库**，不存在"部分成功"。
4. 因此 `processed_rows` 在成功时恒等于 `total_rows`；失败时返回 4xx，不返回 `data`。`processed_rows` 含义为"实际写入或更新的行数，含被更新的旧记录"。
5. **校验顺序**：编码与表头 → 文件大小 → 行数上限 → 逐行格式校验 → 基金代码存在性 → 写入。前一步不通过不进入下一步。
6. 行数限制：最多 1000 行数据行（不含表头）。超过返回 `VALIDATION_ERROR`，`details[0].field = "file"`，`message = "CSV 数据行不能超过 1000 行"`。
7. 文件大小上限 5 MB。超过返回 `VALIDATION_ERROR`，`details[0].field = "file"`，`message = "文件大小不能超过 5 MB"`。
8. 文件类型：只接受 `.csv` 扩展名。上传其他类型返回 `VALIDATION_ERROR`，`details[0].field = "file"`，`message = "只支持上传 .csv 文件"`。
9. 空行（所有字段 `strip()` 后均为空）跳过，不计入 `total_rows`。
10. 每个单元格在校验前先 `strip()`。
11. `nav` 输入超过 4 位小数时**四舍五入到 4 位**（`ROUND_HALF_UP`），不报错。
12. `nav_date` 不能晚于今天；同一 `fund_id + nav_date` 已有净值时更新旧值（`created_at` 保留、`updated_at` 更新）。
13. CSV 内部不允许重复的 `fund_code + nav_date`。
14. `details` 最多返回前 50 条错误，并额外返回 `error_count`（错误总行数）。
15. 编码：优先按 UTF-8 BOM 解析，失败则回退 GBK；两者都失败返回 `VALIDATION_ERROR`，`details[0].field = "file"`，`message = "CSV 编码无法识别，请使用 UTF-8 或 GBK"`。
16. 第一版不提供净值删除接口和净值编辑接口；录错的净值无法通过接口修正，这是已知限制。
```

---

### 5.4 补进 `docs/api/v1-position-snapshots.md`

**落位：第 4 节「业务规则」，在现有 7 条之后追加。**

```markdown
8. **`items` 的集合定义**：`items` = 「该博主有初始持仓的基金」∪「该博主在快照日期之前有操作记录的基金」，取并集去重后**按 `fund_id` 升序**排列。
9. **没有初始持仓的基金**：`initial_record_date` 返回 `null`，`initial_shares` 和 `initial_cost_amount` 返回 `0`（累加起点），**不返回 `null`**。前端据此区分"未录初始持仓"与"份额为 0"。
10. **份额为 `0` 的基金必须保留在 `items` 里**（全部卖完的情况），`shares` 返回 `0`，不剔除、不隐藏。
11. **快照日期早于初始持仓 `record_date` 的基金，不纳入 `items`**（持仓起点未到）。
12. 快照日期早于博主观察开始日时不做限制，照实计算。
13. `snapshot_date` 不设下界；传历史日期时返回空 `items`，HTTP 200。
14. 现金分红（`dividend_cash`）只累加进 `dividend_cash_amount`，**不影响 `shares` 和 `cost_amount`**。
15. 份额可以为负、成本可以为 `0` 或负数，一律照实返回，不截断、不抛异常。
16. `shares` 返回 4 位小数，金额类字段返回 2 位小数（见 `v1-basic-management.md` 1.11）。
17. 同一 `fund_id` 的多条初始持仓只取 `record_date` 最早的一条参与计算，其余不累加（见业务规则 3）。
```

---

### 5.5 补进 `docs/api/v1-returns.md`

**落位：第 2 章「收益计算口径」，在 2.3 之后新增 2.4–2.7。**

```markdown
### 2.4 null 真值表（收益类接口统一）

设：A = 无持仓数据；B = 有持仓、有当天净值；C = 有持仓、缺当天净值。

| 层级 | 场景 | cost_amount | nav | market_value | profit_amount | return_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 基金级 | B | 数值 | 数值 | 数值 | 数值 | 数值 |
| 基金级 | C | 数值 | `null` | `null` | `null` | `null` |
| 基金级 | B 但成本 ≤ 0 | 数值（可为 0 或负） | 数值 | 数值 | 市值 − 成本 | `null` |
| 博主级 | 名下所有基金都是 B | 数值 | — | 数值 | 数值 | 数值 |
| 博主级 | 名下**任意**基金是 C | 数值 | — | `null` | `null` | `null` |
| 博主级 | 总成本 ≤ 0 | 数值 | — | 数值 | 数值 | `null` |
| 博主级 | A（无持仓） | `0` | — | `0` | `0` | `null` |
| 全局级 | 全部基金都是 B | 数值 | — | 数值 | 数值 | 数值 |
| 全局级 | **任意**基金是 C | 数值 | — | `null` | `null` | `null` |
| 全局级 | A（无任何持仓） | `0` | — | `0` | `0` | `null` |

要点：

1. **`0` 只出现在"根本没有任何持仓"这一格。** 只要有持仓且缺净值，一律 `null`，绝不返回 `0`。前端需要能区分"亏到 0"和"没数据"。
2. 成本 ≤ 0 时，`market_value` 和 `profit_amount` **照实返回数值**（`profit_amount = market_value − cost_amount`），只有 `return_rate` 是 `null`。
3. 成本可以是负数（超额卖出导致），照实返回，不截断到 0。
4. `return_rate` 为 `null` 有三种互不覆盖的原因：无持仓、缺净值、成本 ≤ 0。后端不额外返回原因字段，前端按上表判断。
5. `v1-dashboards.md` 的 null 规则是对本表在博主级和全局级的展开，冲突时以本表为准。

### 2.5 现金分红的收益归属

**第一版：现金分红不计入收益金额。** `profit_amount = market_value − cost_amount`；`dividend_cash_amount` 只在持仓快照和近期操作统计中体现，不参与收益率计算。

理由：现金分红拿到的是现金，已脱离持仓；要计入必须引入"已实现收益 + 未实现浮动收益"双口径，第一版不做。前端如需展示分红，单独取 `dividend_cash_amount`。

### 2.6 多初始持仓的计算口径（与持仓快照对齐）

同一 `blogger_id + fund_id` 存在多条初始持仓时，**只取 `record_date` 最早的一条作为计算起点，其余初始持仓完全不参与计算（不累加份额、不累加成本）**。

本条**覆盖**本文档第 4 节业务规则 1「只统计 `return_date` 当天或之前的初始持仓和操作记录」中的"初始持仓"部分；操作记录仍按 `operation_date <= return_date` 全量统计。

本条与 `v1-position-snapshots.md` 业务规则 3 完全一致，两个接口对同一博主同一日期必须给出**相同**的 `shares` 和 `cost_amount`。

### 2.7 其他

1. `return_date` 不设下界；传历史日期时返回空 `items` 和零值汇总，HTTP 200。
2. `return_date` 不传时默认今天。**周末和节假日没有净值，默认查询会返回 `null` 市值**，这是预期行为，不是故障。前端在 `market_value` 为 `null` 时应提示"该日期无净值数据"并引导用户选择其他日期。
3. 所有金额单位为**元**。
4. 单基金接口 `GET /bloggers/{blogger_id}/funds/{fund_id}/return` 中，"基金不存在"与"该博主未持有该基金"共用 `FUND_NOT_FOUND`，HTTP 404，靠 `message` 区分。
5. 成本小于等于 `0` 时返回 `null` 收益率，不返回 `0`，不抛异常。
```

---

### 5.6 补进 `docs/api/v1-dashboards.md`

**落位：第 1 章「全局约定」，在 1.3 之后新增 1.4。**

```markdown
### 1.4 null 口径的分层说明

`null` 规则按三个层级执行，逐层向上"污染"：

1. **基金级**：缺净值的基金，自己的 `nav` / `nav_date` / `market_value` / `profit_amount` / `return_rate` / `market_value_ratio` 为 `null`；有净值的基金照实返回自己的数值。
2. **博主级**：某博主名下**任意**一只基金缺净值，该博主的合计 `total_market_value` / `profit_amount` / `return_rate` 为 `null`。
3. **全局级**：**任意**一只基金缺净值，`data.total_market_value` / `profit_amount` / `return_rate` 为 `null`，且 `/dashboards/funds` 中**所有**基金的 `market_value_ratio` 为 `null`（占比的分母不完整）。

成本类字段（`cost_amount`、`total_cost_amount`、`cost_ratio`）不依赖净值，任何情况下都照实返回。

本文档 1.3 的"收益和空值口径沿用 `docs/api/v1-returns.md`"指沿用其**计算方式和 null 真值表**（`v1-returns.md` 2.4）；本文档 1.3 与第 3/4 节业务规则是对该真值表在本接口的展开，两者冲突时以 `v1-returns.md` 2.4 为准。
```

**落位：第 5 节「近期操作统计」业务规则，在现有 9 条之后追加。**

```markdown
10. 只传 `start_date` 不传 `end_date` 时，`end_date` 默认今天；若 `start_date` 晚于今天，返回 400 / `VALIDATION_ERROR`（违反"开始日期不能晚于结束日期"）。
11. 只传 `end_date` 不传 `start_date` 时，`start_date = end_date - 6`。
12. 两个都不传时，`end_date = 今天`，`start_date = 今天 - 6`，共 7 天（含今天）。
13. `limit` 超出 1–100 时返回 400 / `VALIDATION_ERROR`。
14. `items` 为空时返回空数组 `[]`，不返回 `null`。
15. `summary` 统计的是日期范围内的**全量**操作记录，不受 `limit` 影响，因此 `items` 的条数可以小于 `summary.operation_count`。
16. `start_date` 也不得晚于今天（与 `end_date` 同一约束）。
```

---

## 附：下发任务文档前的动作清单

1. 先把 5.1 的 1.7–1.15（时区、全局异常、错误码总表、通用查询参数、精度、文本规则、CORS、code 类型、details 结构）**一次性补进基础文档**——这 9 条影响全部 6 个模块，不补会让后续所有任务文档都要重复说明。
2. 优先解决第三节冲突 1（多初始持仓）和冲突 3/4（null 真值表）。这两处不定，快照、收益、看板三个模块的任务文档没法写验收标准。
3. 补 `GET /api/v1/nav-history`，并在任务文档里明确 HistoryView 第一版走哪条路（补序列接口 vs 只展示操作记录历史）。
4. 明确 SettingsView 第一版无后端接口，或补 `GET /api/v1/meta/sectors`。
5. 在任务文档里显式列出三条已知限制：净值无删除/编辑、操作记录无编辑、初始持仓无删除。
