# 任务 028：实现净值 CSV 导入接口

## 预计完成时间

预计完成时间：约 1 小时。

估算依据：本任务把任务 027 的解析结果接入 Flask 上传接口，完成基金代码映射和批量入库；解析和校验逻辑已经写好，所以本任务重点是文件上传、接口封装和事务提交。

## 任务目标

实现：

```http
POST /api/v1/nav-history/import
```

使用者可以上传 CSV 文件，批量导入净值。

导入规则：

1. CSV 全部成功才入库。
2. 有一行解析失败就不写库。
3. 有一行基金代码不存在就不写库。
4. 同一 `fund_id + nav_date` 已有净值时更新旧值。
5. 返回导入成功的处理数量。

## 范围说明

本任务只实现 CSV 导入接口。

不包含：

- 净值查询接口
- 净值删除接口
- Excel `.xlsx` 导入
- 部分成功导入
- 异步导入
- 自动净值同步

## 前置条件

1. 任务 026 已完成，净值手动录入接口可用。
2. 任务 027 已完成，CSV 解析和校验工具可用。
3. 数据库里至少存在一个基金。
4. `pytest -q` 全部通过。

## 新概念：multipart/form-data

`multipart/form-data` 是浏览器上传文件时常用的 HTTP 请求格式。

JSON 适合传结构化数据，不适合传文件。  
CSV 导入接口使用文件上传，请求体不是 JSON，而是表单数据。

Flask 中用：

```python
request.files.get("file")
```

读取上传的文件。

## 执行目录

```bash
cd /mnt/d/people/find_gold/backend
source .venv/bin/activate
```

## 具体步骤

### 步骤 1：确认净值路由文件已存在

**必要性：**  
CSV 导入接口属于净值模块，应该写在同一个路由文件里。

确认文件存在：

```bash
ls -l app/routes/nav_history.py
```

确认顶部已经导入：

```python
from flask import Blueprint, request
```

以及：

```python
from app.utils.nav_csv import parse_nav_history_csv
```

如果还没有导入 `parse_nav_history_csv`，请先加上。

---

### 步骤 2：添加基金代码映射函数

**必要性：**  
CSV 里使用的是 `fund_code`，数据库里需要 `fund_id`。必须先把代码映射成 ID。

在 `backend/app/routes/nav_history.py` 中添加：

```python
def map_fund_codes_to_ids(cursor, fund_codes):
    unique_codes = sorted(set(fund_codes))

    if not unique_codes:
        return {}, []

    placeholders = ",".join(["%s"] * len(unique_codes))
    sql = f"""
        SELECT id, fund_code
        FROM funds
        WHERE fund_code IN ({placeholders})
    """
    cursor.execute(sql, unique_codes)
    rows = cursor.fetchall()

    code_to_id = {
        row["fund_code"]: row["id"]
        for row in rows
    }

    missing_codes = [
        code
        for code in unique_codes
        if code not in code_to_id
    ]

    return code_to_id, missing_codes
```

说明：

- `placeholders` 是根据基金代码数量生成的 `%s, %s, ...`。
- 这里可以拼接 SQL 片段，因为拼接的是占位符数量，不是用户输入。
- 真正的基金代码仍然通过参数化 SQL 传入，不是直接拼进 SQL。

---

### 步骤 3：添加 CSV 导入路由

**必要性：**  
这是本任务的核心接口，负责接收文件、调用解析器、映射基金代码、批量写库。

在 `backend/app/routes/nav_history.py` 末尾添加：

```python
@nav_history_bp.post("/api/v1/nav-history/import")
def import_nav_history_csv():
    file = request.files.get("file")

    rows, parse_errors = parse_nav_history_csv(file)

    if parse_errors:
        return error(
            code="VALIDATION_ERROR",
            message="CSV 解析或校验失败",
            details=parse_errors,
            http_status=400
        )

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            fund_codes = [row["fund_code"] for row in rows]
            code_to_id, missing_codes = map_fund_codes_to_ids(
                cursor,
                fund_codes
            )

            if missing_codes:
                return error(
                    code="VALIDATION_ERROR",
                    message="CSV 中存在不存在的基金代码",
                    details=[
                        {
                            "field": "fund_code",
                            "message": f"基金代码 {code} 不存在"
                        }
                        for code in missing_codes
                    ],
                    http_status=400
                )

            processed_count = 0

            for row in rows:
                fund_id = code_to_id[row["fund_code"]]
                nav_date = row["nav_date"]
                nav = row["nav"]

                existing_id = find_nav_history_id(
                    cursor,
                    fund_id,
                    nav_date
                )

                if existing_id is None:
                    cursor.execute(
                        """
                        INSERT INTO nav_history (
                            fund_id,
                            nav_date,
                            nav
                        )
                        VALUES (%s, %s, %s)
                        """,
                        (
                            fund_id,
                            nav_date,
                            nav
                        )
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE nav_history
                        SET nav = %s
                        WHERE id = %s
                        """,
                        (
                            nav,
                            existing_id
                        )
                    )

                processed_count += 1

            conn.commit()
    finally:
        conn.close()

    return success(
        data={
            "total_rows": len(rows),
            "processed_rows": processed_count
        }
    )
```

说明：

- 所有行都在一个事务里处理，最后只调用一次 `conn.commit()`。
- 如果任何 SQL 出错，函数不会走到 `commit()`，数据库不会写入这批数据。
- `processed_count` 表示处理成功的行数。因为重复提交会更新旧值，所以不叫新增数量。

---

### 步骤 4：重启 Flask 服务

**必要性：**  
修改路由后必须重新加载服务，确认没有语法错误。

```bash
python run.py
```

---

### 步骤 5：添加导入成功测试

**必要性：**  
导入接口涉及文件上传和数据库写入，必须有自动化测试守住。

新建或修改文件：

```text
backend/tests/test_nav_history.py
```

顶部导入：

```python
from io import BytesIO
```

添加辅助函数：

```python
def create_csv_file(content: str):
    return {
        "file": (
            BytesIO(content.encode("utf-8")),
            "nav_history.csv"
        )
    }
```

添加测试：

```python
def test_import_nav_history_csv_success(client, create_fund):
    fund = create_fund(
        client,
        name="净值导入基金",
        fund_code="NAV000001"
    )

    csv_content = (
        "fund_code,nav_date,nav\n"
        f"{fund['fund_code']},2026-09-29,1.2000\n"
        f"{fund['fund_code']},2026-09-30,1.2345\n"
    )

    response = client.post(
        "/api/v1/nav-history/import",
        data=create_csv_file(csv_content),
        content_type="multipart/form-data"
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["total_rows"] == 2
    assert body["data"]["processed_rows"] == 2
```

注意：  
这里假设 `tests/factories.py` 中的 `create_fund()` 支持传入 `name` 和 `fund_code`。如果当前签名不同，请按项目里的实际工厂函数调整，但不要为了测试改动业务代码。

---

### 步骤 6：添加导入失败测试

**必要性：**  
必须确认有错误行时不会写库。

添加：

```python
def test_import_nav_history_csv_rejects_invalid_row(client, create_fund):
    fund = create_fund(
        client,
        name="净值导入失败基金",
        fund_code="NAV000002"
    )

    csv_content = (
        "fund_code,nav_date,nav\n"
        f"{fund['fund_code']},2026-09-29,1.2000\n"
        f"{fund['fund_code']},2026-09-30,0\n"
    )

    response = client.post(
        "/api/v1/nav-history/import",
        data=create_csv_file(csv_content),
        content_type="multipart/form-data"
    )
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"
```

再添加：

```python
def test_import_nav_history_csv_rejects_unknown_fund_code(client):
    csv_content = (
        "fund_code,nav_date,nav\n"
        "NOT_EXIST,2026-09-30,1.2345\n"
    )

    response = client.post(
        "/api/v1/nav-history/import",
        data=create_csv_file(csv_content),
        content_type="multipart/form-data"
    )
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"
```

---

### 步骤 7：运行全部测试

**必要性：**  
确认新测试通过，且没有影响已有功能。

执行：

```bash
pytest -q
```

预期全部通过。

## 验证方式

### 1. 准备 CSV 文件

创建一个本地文件：

```text
/tmp/nav_history.csv
```

内容：

```csv
fund_code,nav_date,nav
NAV000001,2026-09-29,1.2000
NAV000001,2026-09-30,1.2345
```

请把 `NAV000001` 换成数据库里真实存在的基金代码。

### 2. 调用导入接口

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/nav-history/import" \
  -F "file=@/tmp/nav_history.csv"
```

预期返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "total_rows": 2,
    "processed_rows": 2
  }
}
```

### 3. 再次导入同一天净值

把文件里 `2026-09-30` 的净值改成：

```text
1.3000
```

再次执行：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/nav-history/import" \
  -F "file=@/tmp/nav_history.csv"
```

预期返回成功，并且 `2026-09-30` 的旧净值被更新。

### 4. 导入包含错误行的 CSV

创建文件：

```text
/tmp/nav_history_bad.csv
```

内容：

```csv
fund_code,nav_date,nav
000001,2026-09-29,1.2000
000001,2026-09-30,0
```

执行：

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/nav-history/import" \
  -F "file=@/tmp/nav_history_bad.csv"
```

预期返回 `400`，并且第一行没有入库。

## 常见坑

### 1. 用 JSON 发送文件

CSV 导入接口不是 JSON 请求。  
不要写：

```bash
curl -H "Content-Type: application/json" \
  -d '{"file":"..."}'
```

应该使用：

```bash
curl -F "file=@/tmp/nav_history.csv"
```

### 2. 在测试里没有设置 `content_type`

Flask 测试上传文件时需要：

```python
content_type="multipart/form-data"
```

否则文件可能不会被识别。

### 3. 部分成功入库

本设计要求全部成功才入库。  
不要在一个循环里边校验边插入。

### 4. 每行提交一次事务

不要每插入一行就 `conn.commit()`。  
应该处理完所有行后统一提交。

### 5. 忘记处理不存在的基金代码

CSV 里的 `fund_code` 可能在数据库里不存在。  
必须先映射，发现缺失就返回错误，不写库。

### 6. 导入接口返回 201

本项目的约定是成功响应统一返回 HTTP `200`。  
不要返回 `201`。

## 完成标准

以下条件全部满足，任务 028 才算完成：

1. `POST /api/v1/nav-history/import` 可以接收 CSV 文件。
2. CSV 全部成功才入库。
3. 有错误行时不写库。
4. 基金代码不存在时不写库。
5. 同一 `fund_id + nav_date` 已有净值时更新旧值。
6. 返回 `total_rows` 和 `processed_rows`。
7. `pytest -q` 全部通过。
8. 所有响应都是统一 JSON 结构。

## 完成后请反馈

1. 新增和修改的文件列表。
2. 成功导入的 curl 验证结果。
3. 错误行导入的 curl 验证结果。
4. 重复导入更新旧值的验证结果。
5. `pytest -q` 的完整输出。
6. 遇到的问题和未完成项。
