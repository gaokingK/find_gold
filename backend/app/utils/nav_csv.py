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

