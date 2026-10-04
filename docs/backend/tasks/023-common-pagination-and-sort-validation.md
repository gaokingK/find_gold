# 任务 023：统一分页与排序校验工具

## 预计完成时间

预计完成时间：约 2 小时。

估算依据：本任务把博主、基金、初始持仓、操作记录四个模块里重复的 `page`、`page_size`、`sort_by`、`order` 校验逻辑抽到一个公共函数里。四个模块接入方式不完全一样：基金和初始持仓没有排序参数，博主模块原来是「遇到第一个错误就返回」的写法，要先改成「收集全部错误再返回」。已有测试覆盖，重构风险可控，但博主模块那部分比单纯替换代码多花时间。

## 任务目标

创建一份统一的列表参数校验工具，并在现有四个列表模块中接入。

完成后可以：

1. `page`、`page_size`、`sort_by`、`order` 的校验规则只维护一处。
2. 四个模块的列表接口对外行为基本不变（唯一允许的变化：博主模块的错误 `message` 统一成「参数校验失败」，且一次请求可以返回多个错误）。
3. 修改分页上限或排序规则时，只需要改一个文件。
4. `pytest -q` 全部通过。

## 范围说明

本任务只抽公共的分页与排序校验工具。

不包含：

- 修改接口文档
- 修改数据库表结构
- 新增净值模块
- 调整业务筛选条件，例如 `blogger_id`、`fund_id`、`operation_type`
- 修改 `parse_positive_int()`
- 重构 repository / service 分层
- **给基金和初始持仓列表接口新增 `sort_by` / `order` 参数**（这两个接口的接口文档里没有排序参数，加了就是改契约，要走单独任务）

## 前置条件

1. 任务 022 已完成，操作记录接口和测试都通过。
2. `pytest -q` 当前全部通过。
3. 博主、基金、初始持仓、操作记录四个模块都有列表接口。

## 新概念：DRY

DRY 的英文是 Don't Repeat Yourself，中文意思是「不要重复自己」。

它的意思是：同一段规则不应该复制到多个地方。  
如果同一段校验逻辑在四个文件里重复出现，以后改规则就要改四次，漏一次就会出现行为不一致。

本任务不是加新功能，而是把已经存在的重复逻辑合并。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：先确认当前测试通过

**必要性：**  
本任务是重构。重构前必须先确认当前测试是绿的，否则你无法判断后面的问题是你改出来的，还是本来就存在。

执行：

```bash
pytest -q
```

预期全部通过。

---

### 步骤 2：创建公共列表参数工具

**必要性：**  
四个模块都需要校验分页。统一放在一个文件里，以后只需要维护一份规则。

新建文件：

```text
backend/app/utils/list_params.py
```

内容：

```python
from flask import request


MAX_PAGE_SIZE = 100


def parse_list_query_params(
    default_sort_by=None,
    allowed_sort_fields=None,
    default_order="desc"
):
    details = []
    params = {}

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
    except (TypeError, ValueError):
        details.append(
            {
                "field": "page",
                "message": "page 和 page_size 必须是整数"
            }
        )
        page = 0
        page_size = 0

    if page <= 0:
        details.append(
            {
                "field": "page",
                "message": "page 必须大于 0"
            }
        )

    if page_size <= 0 or page_size > MAX_PAGE_SIZE:
        details.append(
            {
                "field": "page_size",
                "message": f"page_size 必须在 1 到 {MAX_PAGE_SIZE} 之间"
            }
        )

    params["page"] = page
    params["page_size"] = page_size

    if allowed_sort_fields is None:
        return params, details

    sort_by = request.args.get("sort_by", default_sort_by)
    order = request.args.get("order", default_order)

    if sort_by in allowed_sort_fields:
        sort_column = allowed_sort_fields[sort_by]
    else:
        sort_column = None
        allowed_text = "、".join(allowed_sort_fields.keys())
        details.append(
            {
                "field": "sort_by",
                "message": f"sort_by 只允许 {allowed_text}"
            }
        )

    if order not in ("asc", "desc"):
        details.append(
            {
                "field": "order",
                "message": "order 只允许 asc 或 desc"
            }
        )

    params["sort_by"] = sort_by
    params["sort_column"] = sort_column
    params["order"] = order

    return params, details
```

说明：

- `allowed_sort_fields` 是排序白名单，格式仍然是「参数名 -> SQL 字段名」。
- `sort_column` 是映射后的 SQL 字段名，调用方可以直接放进 `ORDER BY`。
- **这个函数不返回错误响应，只返回 `details` 列表。** 原因见步骤 3。
- **`allowed_sort_fields` 不传时，函数只校验分页，完全不读 `sort_by` 和 `order`。** 原因见步骤 5。
- `MAX_PAGE_SIZE = 100` 保持现有行为不变。
- 错误提示用 f-string 拼 `MAX_PAGE_SIZE` 和白名单字段，以后改上限或加排序字段，提示文案会自动跟着变，不会出现「代码是 200、提示还写着 100」。

注意这个文件**不导入** `app.utils.responses`。它不负责构造响应，只负责产出校验结果。

---

### 步骤 3：理解调用方式

**必要性：**  
公共工具只负责通用参数，不负责模块自己的筛选条件，也不负责决定什么时候返回错误。这样职责边界清晰，后面不容易改乱。

本项目的校验约定是：**一次请求里所有参数错误要一次性收集齐，放进同一个 `details` 里返回，不能遇到第一个错误就返回。** 前端填一次表单，应该一次看到全部问题。

所以公共函数返回的是 `details` 列表，由调用方合并进自己的 `details`，**在函数末尾统一判断一次**：

```python
def parse_operation_list_params():
    details = []

    # ... 模块自己的筛选条件校验，往 details 里 append ...

    common_params, common_details = parse_list_query_params(
        default_sort_by="created_at",
        allowed_sort_fields=ALLOWED_OPERATION_SORT_FIELDS,
        default_order="desc"
    )
    details.extend(common_details)

    if details:
        return None, error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=details,
            http_status=400
        )

    return {
        # ... 模块自己的字段 ...
        "page": common_params["page"],
        # ...
    }, None
```

**不要**写成这样：

```python
    common_params, common_error = parse_list_query_params(...)

    if common_error is not None:
        return None, common_error          # 错误：把前面收集的 details 丢掉了
```

这么写的话，`?blogger_id=abc&page=0` 只会返回 `page` 的错误，`blogger_id` 的错误被吞掉，用户改完 `page` 再请求一次才看到第二个错误。

模块自己的筛选参数，例如 `blogger_id`、`fund_id`、`operation_type`，仍然留在各自模块的解析函数里。

---

### 步骤 4：接入操作记录模块

**必要性：**  
操作记录模块是最近写的，重复分页校验最明显，而且它本来就是「收集全部错误再返回」的写法，先改它作为模板。

修改文件：

```text
backend/app/routes/operations.py
```

在文件顶部增加：

```python
from app.utils.list_params import parse_list_query_params
```

在 `parse_operation_list_params()` 中，把这一段：

```python
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
    except (TypeError, ValueError):
        details.append(
            {
                "field": "page",
                "message": "page 和 page_size 必须是整数"
            }
        )
        page = 0
        page_size = 0

    if page <= 0:
        details.append(
            {
                "field": "page",
                "message": "page 必须大于 0"
            }
        )

    if page_size <= 0 or page_size > 100:
        details.append(
            {
                "field": "page_size",
                "message": "page_size 必须在 1 到 100 之间"
            }
        )

    sort_by = request.args.get("sort_by", "created_at")
    order = request.args.get("order", "desc")

    if sort_by not in ALLOWED_OPERATION_SORT_FIELDS:
        details.append(
            {
                "field": "sort_by",
                "message": "排序字段只允许 operation_date、amount、created_at"
            }
        )

    if order not in ("asc", "desc"):
        details.append(
            {
                "field": "order",
                "message": "order 只允许 asc 或 desc"
            }
        )
```

替换为：

```python
    common_params, common_details = parse_list_query_params(
        default_sort_by="created_at",
        allowed_sort_fields=ALLOWED_OPERATION_SORT_FIELDS,
        default_order="desc"
    )
    details.extend(common_details)
```

关键点：**这里不要 `return`。** 原来的代码是把错误 `append` 到 `details` 里继续往下走，函数末尾才统一 `if details: return None, error(...)`。替换后必须保持这个结构，只是把「自己校验」换成「合并公共函数的校验结果」。

`details.extend(common_details)` 这一行放在哪里都可以，但**必须在函数末尾那个 `if details:` 之前**。

然后在函数最后的返回字典里加入：

```python
    return {
        "blogger_id": blogger_id,
        "fund_id": fund_id,
        "operation_type": operation_type,
        "date_from": date_from,
        "date_to": date_to,
        "keyword": keyword,
        "page": common_params["page"],
        "page_size": common_params["page_size"],
        "sort_by": common_params["sort_by"],
        "sort_column": common_params["sort_column"],
        "order": common_params["order"],
    }, None
```

同时把 `list_operations()` 里原来的：

```python
    sort_column = ALLOWED_OPERATION_SORT_FIELDS[params["sort_by"]]
```

改成：

```python
    sort_column = params["sort_column"]
```

---

### 步骤 5：接入博主、基金、初始持仓模块

**必要性：**  
只改一个模块没有解决重复问题。四个模块必须都接入公共工具，才算完成本任务。

修改以下文件：

```text
backend/app/routes/bloggers.py
backend/app/routes/funds.py
backend/app/routes/initial_positions.py
```

**先看清楚：这三个模块和操作记录不一样，接入方式不同。**

| 模块 | 有分页 | 有排序参数 | 默认排序 | 接入方式 |
| --- | --- | --- | --- | --- |
| 博主（008） | 有 | 有 `sort_by` / `order` | `created_at` / `desc` | 传 `allowed_sort_fields` |
| 基金（011） | 有 | **没有** | SQL 里固定 `ORDER BY id ASC` | **不传** `allowed_sort_fields` |
| 初始持仓（012） | 有 | **没有** | SQL 里固定 `ORDER BY ip.id DESC` | **不传** `allowed_sort_fields` |
| 操作记录（021） | 有 | 有 `sort_by` / `order` | `created_at` / `desc` | 传 `allowed_sort_fields` |

基金和初始持仓的列表接口**从来没有 `sort_by` 和 `order` 参数**，`docs/api/v1-basic-management.md` 里也没写。它们的排序是写死在 SQL 里的。

所以这两个模块调用公共函数时**不要传 `allowed_sort_fields`**：

```python
    common_params, common_details = parse_list_query_params()
    details.extend(common_details)
```

如果传了白名单，就等于给这两个接口凭空加了排序功能，还会让 `?sort_by=xxx` 从「静默忽略」变成「返回 400」。那是改接口行为，不是重构，而且和接口文档不一致。要加排序功能，先改 `docs/api/v1-basic-management.md`，走单独任务。

它们的 SQL 里的 `ORDER BY id ASC` / `ORDER BY ip.id DESC` **保持原样不动**，不要改成 `params["sort_column"]`。

对博主和操作记录模块，才使用 `params["sort_column"]`。

#### 博主模块要特别注意的两处行为变化

博主模块（008）的 `parse_common_params()` 是「遇到第一个错误就 `return`」的写法，和公共函数的「收集全部」不一样。接入后会有两处变化，这是**预期的、允许的**：

1. **错误提示文案变了。** 原来是 `"分页参数不合法"` / `"page 参数不合法"` / `"page_size 参数不合法"` / `"sort_by 参数不合法"` 这几个不同的 `message`，接入后统一成 `"参数校验失败"`，具体问题在 `details` 里。任务 016 的测试只断言 `body["code"] == "VALIDATION_ERROR"`，不断言 `message`，所以测试不会挂。
2. **一次请求可以返回多个错误。** 原来 `?page=0&sort_by=password` 只返回 `page` 一个错误，接入后 `details` 里会有两条。这是往项目统一约定靠，不是回归。

还有一处**必须保留**的差异：博主模块原来写的是

```python
    order = request.args.get("order", "desc").lower()
```

注意那个 `.lower()`。公共函数里没有 `.lower()`，所以接入后 `?order=DESC` 会从「正常工作」变成「返回 400」。

按本任务「接口行为不变」的要求，**不要**在公共函数里加 `.lower()`（那会反过来改变操作记录模块的行为），也不要默默让 `?order=DESC` 报错。把这件事**作为发现的问题反馈**，由下发任务的人决定统一成哪种口径，本任务先按现状记录，不自行拍板。

#### 通用步骤

对每个模块做同样处理：

1. 顶部导入公共函数。
2. 找到各自的列表参数解析函数。
3. 删除 `page`、`page_size` 的重复校验；博主和操作记录再删 `sort_by`、`order` 的重复校验。
4. 调用 `parse_list_query_params()`，把返回的 `common_details` 合并进本模块的 `details`。
5. 保留模块自己的筛选条件。
6. 在函数末尾统一判断 `if details:` 再返回错误，**中途不要 `return`**。
7. 把公共参数合并回各自的 `params`。
8. 博主和操作记录的查询 SQL 使用 `params["sort_column"]`；基金和初始持仓的 `ORDER BY` 不动。

博主模块原来是「遇错即返回」，没有 `details` 列表。接入时要先把它改成先建一个 `details = []`、各处 `append`、末尾统一返回的结构，再合并 `common_details`。

---

### 步骤 6：运行全部测试

**必要性：**  
本任务不改业务行为。测试全部通过，才能证明重构没有破坏接口。

执行：

```bash
pytest -q
```

预期全部通过。

如果某个模块测试失败，优先检查：

1. 是否漏改某个模块。
2. 是否把模块自己的筛选条件误删了。
3. 是否还在使用旧的 `params["sort_by"]` 自己映射 SQL 字段。
4. 是否给基金或初始持仓传了 `allowed_sort_fields`，凭空加了排序参数。
5. 是否在合并 `common_details` 之后中途 `return`，把前面收集的 `details` 丢掉了。

## 验证方式

### 1. 自动化测试

```bash
pytest -q
```

预期全部通过。

### 2. 确认重复逻辑已经收敛

执行：

```bash
grep -R "page_size 必须" -n app/routes
```

预期 `app/routes` 下没有输出，或者只剩注释，不再是重复校验代码。

执行：

```bash
grep -Rn "page_size 必须在 1 到" app/utils/list_params.py
```

预期只看到一处，而且上限是拼进去的 `{MAX_PAGE_SIZE}`，不是写死的 `100`。

### 3. 确认没有中途 return

执行：

```bash
grep -n "common_details\|common_params" app/routes/*.py
```

四个模块都应该有 `details.extend(common_details)`，**不应该**出现 `return None, common_details` 或 `if common_details is not None: return` 这种写法。

### 4. 确认一次返回多个错误

```bash
curl -i "http://127.0.0.1:5000/api/v1/operations?blogger_id=abc&page=0&order=middle"
```

预期 HTTP `400`，并且 `details` 里**同时**有 `blogger_id`、`page`、`order` 三条，不是只有一条。

这是本任务最容易做错的一点，一定要实际请求验证。

### 5. 手工验证分页规则

```bash
curl -i "http://127.0.0.1:5000/api/v1/operations?page=0"
curl -i "http://127.0.0.1:5000/api/v1/operations?page_size=101"
curl -i "http://127.0.0.1:5000/api/v1/operations?sort_by=password"
curl -i "http://127.0.0.1:5000/api/v1/operations?order=middle"
```

预期都返回 `VALIDATION_ERROR`，HTTP 状态码是 `400`。  
其中 `sort_by=password` 的提示里应该列出允许的字段名。

### 6. 确认基金和初始持仓没有被加上排序

```bash
curl -i "http://127.0.0.1:5000/api/v1/funds?sort_by=password"
curl -i "http://127.0.0.1:5000/api/v1/initial-positions?sort_by=password"
```

预期都返回 HTTP `200`（参数被忽略），**不是** `400`。  
如果返回 `400`，说明给这两个模块传了 `allowed_sort_fields`，接口行为被改了。

## 常见坑

### 1. 合并公共校验后中途 return

这是本任务最容易犯的错，而且测试可能发现不了。

```python
    common_params, common_details = parse_list_query_params(...)

    if common_details:
        return None, error(..., details=common_details, ...)   # 错误
```

这么写，`?blogger_id=abc&page=0` 只会返回 `page` 的错误，`blogger_id` 的错误被吞掉了。  
正确做法是 `details.extend(common_details)`，让函数末尾那个 `if details:` 统一处理。

### 2. 给基金和初始持仓加上排序参数

基金（011）和初始持仓（012）的列表接口**没有** `sort_by` 和 `order`，`docs/api/v1-basic-management.md` 里也没写。  
调用公共函数时不要传 `allowed_sort_fields`，SQL 里的 `ORDER BY` 保持原样。

### 3. 把模块自己的筛选条件也抽进公共函数

`blogger_id`、`fund_id`、`operation_type`、日期区间是模块自己的业务参数，不要抽进 `parse_list_query_params()`。  
公共函数只管所有列表接口都一样的参数。

### 4. 忘记返回 `sort_column`

如果公共函数只返回 `sort_by`，调用方还要再查一次白名单，重构就不完整。  
应直接返回 `sort_column`。

### 5. 排序字段非法时拿 `sort_column` 去拼 SQL

`sort_by` 不在白名单时，`sort_column` 是 `None`。  
此时 `details` 非空，调用方会在末尾返回 `400`，根本走不到 SQL。但如果你自己改了流程，务必确认 `None` 不会被拼进 `ORDER BY`。

### 6. 只改一个模块

只改操作记录不算完成。  
博主、基金、初始持仓、操作记录四个模块都要接入。

### 7. 改变原有默认排序

本任务的目标是统一校验，不是改变接口行为。  
不要顺手把基金列表从升序改成降序。

### 8. 把提示文案里的上限写死

不要写 `"page_size 必须在 1 到 100 之间"`。  
用 f-string 拼 `MAX_PAGE_SIZE`，否则以后改上限会出现「代码是 200、提示还写 100」。  
同理，`sort_by` 的提示应该由白名单自动拼出来，不要手写字段名。

### 9. 修改 `page_size` 上限

保持 `MAX_PAGE_SIZE = 100`。  
如果想改成 200，先反馈，不要在这个任务里顺便改。

### 10. 删除测试

不要为了让测试通过而删除测试。  
如果测试失败，说明重构有回归问题。

## 完成标准

以下条件全部满足，任务 023 才算完成：

1. `backend/app/utils/list_params.py` 已创建，且**不导入** `app.utils.responses`。
2. `parse_list_query_params()` 存在，返回 `(params, details)`，不返回错误响应。
3. `allowed_sort_fields` 不传时，函数只校验分页，不读 `sort_by` 和 `order`。
4. 博主、基金、初始持仓、操作记录四个模块都接入公共函数。
5. 基金和初始持仓**没有**被加上 `sort_by` / `order` 参数，`?sort_by=xxx` 仍然返回 `200`。
6. 四个模块都用 `details.extend(common_details)` 合并，没有中途 `return`。
7. `?blogger_id=abc&page=0&order=middle` 能一次返回三条 `details`。
8. 模块自己的筛选条件保留在各自模块里。
9. `page_size` 上限仍是 `100`，且提示文案由 `MAX_PAGE_SIZE` 拼出。
10. `pytest -q` 全部通过。
11. 除了博主模块 `message` 文案统一成「参数校验失败」、以及一次可返回多个错误这两点之外，接口行为没有变化。

## 完成后请反馈

1. 新增和修改的文件列表。
2. `pytest -q` 的完整输出。
3. 四个模块是否都已接入公共函数。
4. 基金和初始持仓 `?sort_by=xxx` 的实际响应状态码。
5. `?blogger_id=abc&page=0&order=middle` 的完整响应 JSON（用来证明多个错误一次返回）。
6. 默认排序是否保持不变。
7. 博主模块 `order=DESC` 大写的问题现在是什么表现，建议怎么统一。
8. 有没有发现接口文档或现有实现说不通的地方。
9. 遇到的问题和未完成项。
