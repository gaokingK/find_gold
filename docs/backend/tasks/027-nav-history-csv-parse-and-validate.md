# 任务 027：净值 CSV 解析与校验

## 预计完成时间

预计完成时间：约 1.5 小时。

估算依据：本任务只处理 CSV 文件的读取、解析和校验，不写数据库。需要理解文件流、CSV 表头、编码、逐行错误和重复行检测。

## 任务目标

创建一个净值 CSV 解析工具。

完成后可以：

1. 读取上传的 CSV 文件内容。
2. 支持 UTF-8 BOM 和常见 GBK 编码。
3. 校验 CSV 表头。
4. 逐行校验 `fund_code`、`nav_date`、`nav`。
5. 识别 CSV 内部重复的 `fund_code + nav_date`。
6. 返回干净的待入库行和错误列表。
7. 用 pytest 验证解析逻辑。

## 范围说明

本任务只做 CSV 解析和校验。

不包含：

- 写数据库
- Flask 上传接口
- 根据 `fund_code` 查询数据库
- 更新已有净值
- 自动净值同步
- Excel `.xlsx` 文件解析

## 前置条件

1. 任务 024 已完成，CSV 导入口径已确认。
2. 任务 026 已完成，净值路由文件已存在。
3. `pytest -q` 全部通过。

## 新概念：CSV 与 BOM

CSV 的英文是 Comma-Separated Values，中文意思是逗号分隔值。

它是一种纯文本表格格式，例如：

```csv
fund_code,nav_date,nav
000001,2026-09-30,1.2345
```

BOM 的英文是 Byte Order Mark，中文意思是字节顺序标记。  
有些 Windows 程序导出 UTF-8 文件时会在开头加 BOM。Python 读取时如果处理不好，第一个表头可能变成：

```text
\tufefffund_code
```

所以本任务使用 `utf-8-sig` 读取文件。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：创建 CSV 解析工具文件

**必要性：**  
CSV 解析逻辑不应该直接塞在 Flask 路由里。单独放一个文件，后续测试和维护更方便。

新建文件：

```text
backend/app/utils/nav_csv.py
```

先写入基础结构：

```python
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation


MAX_NAV_CSV_ROWS = 1000


def parse_nav_history_csv(file):
    errors = []

    if file is None:
        return None, [
            {
                "field": "file",
                "message": "请选择 CSV 文件"
            }
        ]

    raw = file.read()

    if not raw:
        return None, [
            {
                "field": "file",
                "message": "CSV 文件不能为空"
            }
        ]

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("gbk")
        except UnicodeDecodeError:
            return None, [
                {
                    "field": "file",
                    "message": "CSV 文件编码必须是 UTF-8 或 GBK"
                }
            ]

    reader = csv.DictReader(io.StringIO(text, newline=""))

    required_columns = {"fund_code", "nav_date", "nav"}
    actual_columns = set(reader.fieldnames or [])

    if not required_columns.issubset(actual_columns):
        missing = sorted(required_columns - actual_columns)
        return None, [
            {
                "field": "file",
                "message": f"CSV 缺少必需列：{', '.join(missing)}"
            }
        ]

    rows = []
    seen_keys = set()

    for row in reader:
        row_number = reader.line_num
        row_errors = []
        fund_code = (row.get("fund_code") or "").strip()
        raw_nav_date = (row.get("nav_date") or "").strip()
        raw_nav = (row.get("nav") or "").strip()

        if not fund_code:
            row_errors.append(
                {
                    "row": row_number,
                    "field": "fund_code",
                    "message": "基金代码不能为空"
                }
            )

        parsed_nav_date = None

        if not raw_nav_date:
            row_errors.append(
                {
                    "row": row_number,
                    "field": "nav_date",
                    "message": "净值日期不能为空"
                }
            )
        else:
            try:
                parsed_nav_date = datetime.strptime(
                    raw_nav_date,
                    "%Y-%m-%d"
                ).date()
            except ValueError:
                row_errors.append(
                    {
                        "row": row_number,
                        "field": "nav_date",
                        "message": "净值日期格式必须是 YYYY-MM-DD"
                    }
                )

        parsed_nav = None

        if not raw_nav:
            row_errors.append(
                {
                    "row": row_number,
                    "field": "nav",
                    "message": "净值不能为空"
                }
            )
        else:
            try:
                parsed_nav = Decimal(raw_nav)
            except InvalidOperation:
                row_errors.append(
                    {
                        "row": row_number,
                        "field": "nav",
                        "message": "净值必须是数字"
                    }
                )
            else:
                if not parsed_nav.is_finite() or parsed_nav <= 0:
                    row_errors.append(
                        {
                            "row": row_number,
                            "field": "nav",
                            "message": "净值必须大于 0"
                        }
                    )
                    parsed_nav = None

        if (
            fund_code
            and parsed_nav_date is not None
        ):
            key = (fund_code, parsed_nav_date.isoformat())

            if key in seen_keys:
                row_errors.append(
                    {
                        "row": row_number,
                        "field": "fund_code",
                        "message": f"CSV 内部存在重复的基金代码和净值日期：{fund_code} {parsed_nav_date.isoformat()}"
                    }
                )
            else:
                seen_keys.add(key)

        if row_errors:
            errors.extend(row_errors)
            continue

        rows.append(
            {
                "fund_code": fund_code,
                "nav_date": parsed_nav_date,
                "nav": parsed_nav
            }
        )

        if len(rows) > MAX_NAV_CSV_ROWS:
            errors.append(
                {
                    "field": "file",
                    "message": f"CSV 行数不能超过 {MAX_NAV_CSV_ROWS}"
                }
            )
            break

    if errors:
        return None, errors

    if not rows:
        return None, [
            {
                "field": "file",
                "message": "CSV 中没有有效数据"
            }
        ]

    return rows, errors
```

---

### 步骤 2：理解返回结构

**必要性：**  
这个函数有两种返回结果：解析成功，或者解析失败。调用方需要能清楚区分。

成功时：

```python
(rows, [])
```

`rows` 的每一项：

```python
{
    "fund_code": "000001",
    "nav_date": datetime.date(2026, 9, 30),
    "nav": Decimal("1.2345")
}
```

失败时：

```python
(None, errors)
```

`errors` 的每一项：

```python
{
    "row": 2,
    "field": "nav_date",
    "message": "净值日期格式必须是 YYYY-MM-DD"
}
```

---

### 步骤 3：创建净值测试文件

**必要性：**  
CSV 解析逻辑很容错，必须在写数据库前用测试验证。

新建文件：

```text
backend/tests/test_nav_csv.py
```

顶部导入：

```python
from io import BytesIO

from app.utils.nav_csv import parse_nav_history_csv
```

---

### 步骤 4：编写成功解析测试

**必要性：**  
先确认最基本的合法 CSV 能被正确解析。

添加：

```python
def test_parse_nav_history_csv_success():
    content = b"fund_code,nav_date,nav\n000001,2026-09-30,1.2345\n"

    rows, errors = parse_nav_history_csv(BytesIO(content))

    assert errors == []
    assert len(rows) == 1
    assert rows[0]["fund_code"] == "000001"
    assert rows[0]["nav_date"].isoformat() == "2026-09-30"
    assert str(rows[0]["nav"]) == "1.2345"
```

---

### 步骤 5：编写 UTF-8 BOM 测试

**必要性：**  
Windows 导出的 UTF-8 CSV 可能带 BOM。这个测试可以防止表头被误读。

添加：

```python
def test_parse_nav_history_csv_supports_utf8_bom():
    content = b"\xef\xbb\xbffund_code,nav_date,nav\n000001,2026-09-30,1.2345\n"

    rows, errors = parse_nav_history_csv(BytesIO(content))

    assert errors == []
    assert rows[0]["fund_code"] == "000001"
```

---

### 步骤 6：编写错误行测试

**必要性：**  
非法日期、非法净值、空基金代码都必须被识别。

添加：

```python
def test_parse_nav_history_csv_reports_row_errors():
    content = (
        b"fund_code,nav_date,nav\n"
        b"000001,2026/09/30,1.2345\n"
        b",2026-09-30,1.2345\n"
        b"000002,2026-09-30,0\n"
    )

    rows, errors = parse_nav_history_csv(BytesIO(content))

    assert rows is None
    assert len(errors) >= 3
```

---

### 步骤 7：编写重复行测试

**必要性：**  
同一基金同一天在 CSV 内部重复会让导入结果不明确。必须拒绝。

添加：

```python
def test_parse_nav_history_csv_rejects_duplicate_key():
    content = (
        b"fund_code,nav_date,nav\n"
        b"000001,2026-09-30,1.2345\n"
        b"000001,2026-09-30,1.3000\n"
    )

    rows, errors = parse_nav_history_csv(BytesIO(content))

    assert rows is None
    assert any("重复" in error["message"] for error in errors)
```

---

### 步骤 8：运行测试

**必要性：**  
必须实际运行，确认解析逻辑符合预期。

执行：

```bash
pytest -q tests/test_nav_csv.py
```

预期全部通过。

再执行完整测试：

```bash
pytest -q
```

预期全部通过。

## 验证方式

### 1. 自动化测试

```bash
pytest -q tests/test_nav_csv.py
```

预期全部通过。

### 2. 完整测试

```bash
pytest -q
```

预期全部通过。

### 3. 确认没有写数据库

```bash
grep -n "INSERT INTO nav_history" app/utils/nav_csv.py
```

预期没有输出。

## 常见坑

### 1. 忘记处理 BOM

如果测试发现表头是：

```text
\ufefffund_code
```

说明没有使用 `utf-8-sig` 解码。

### 2. 用 float 解析净值

不要用：

```python
float(raw_nav)
```

本任务使用 `Decimal`，避免精度问题。

### 3. 忽略空行

CSV 文件末尾可能有空行。  
如果它被当成一行数据，会产生奇怪的错误。当前实现按字段内容判断，空行通常会被报为缺字段；如果后续发现干扰，可以再增加「跳过完全空行」的规则。

### 4. 允许 CSV 内部重复

同一 `fund_code + nav_date` 在文件里重复时，不能决定哪一行是正确值。  
必须报错。

### 5. 在本任务里写数据库

本任务只解析和校验，不写数据库。  
写库是任务 028 的工作。

### 6. 忘记限制行数

导入文件可能很大。  
第一版限制最多 1000 行，避免一次导入过多数据导致接口超时。

## 完成标准

以下条件全部满足，任务 027 才算完成：

1. `backend/app/utils/nav_csv.py` 已创建。
2. `parse_nav_history_csv()` 已实现。
3. 支持 UTF-8 BOM 和 GBK。
4. 校验 `fund_code`、`nav_date`、`nav`。
5. 识别 CSV 内部重复的 `fund_code + nav_date`。
6. `backend/tests/test_nav_csv.py` 已创建。
7. `pytest -q` 全部通过。
8. 本任务没有写数据库。

## 完成后请反馈

1. 新增的文件列表。
2. `pytest -q tests/test_nav_csv.py` 的完整输出。
3. `pytest -q` 的完整输出。
4. 测试函数数量。
5. 遇到的问题和未完成项。
