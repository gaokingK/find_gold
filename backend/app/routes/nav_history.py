from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request

from app.db import get_connection
from app.utils.nav_csv import parse_nav_history_csv
from app.utils.responses import error, success



nav_history_bp = Blueprint("nav_history", __name__)


def parse_positive_int(value):
    if isinstance(value, bool):
        return None

    try:
        result = int(value)
    except (TypeError, ValueError):
        return None

    if result <= 0:
        return None

    return result


def parse_decimal(value):
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        value = str(value)

    if not isinstance(value, str) or value.strip() == "": 
        return None

    try:
        result = Decimal(value.strip())
    except InvalidOperation:
        return None

    if not result.is_finite():
        return None

    return result


def parse_nav_payload():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None, error(
            code="VALIDATION_ERROR",
            message="请求体必须是 JSON对象",
            details=[],
            http_status=400
        )

    fund_id = parse_positive_int(data.get("fund_id"))
    raw_nav_date = data.get("nav_date")
    nav = parse_decimal(data.get("nav"))
    details = []

    if fund_id is None:
        details.append(
            {
                "field": "fund_id",
                "message": "基金ID必须为正整数"
            }
        )

    parsed_nav_date = None

    if not isinstance(raw_nav_date, str):
        details.append(
            {
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
            details.append(
                {
                    "field": "nav_date",
                    "message": "净值日期格式化必须是 YYYY-MM-DD"
                }
            )

    if parsed_nav_date is not None and parsed_nav_date > date.today():
        details.append(
            {
                "field": "nav_date",
                "message": "净值日期不能晚于今天"
            }
        )

    if nav is None:
        details.append(
            {
                "field": "nav",
                "message": "净值必须是数字"
            }
        )
    elif nav <= 0:
        details.append(
            {
                "field": "nav",
                "message": "净值必须大于0"
            }
        )

    if details:
        return None, error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=details,
            http_status=400
        )

    return {
        "fund_id": fund_id,
        "nav_date": parsed_nav_date,
        "nav": nav
    }, None


def serialize_nav_history(row):
    nav_date = row["nav_date"]
    created_at = row["created_at"]
    updated_at = row["updated_at"]

    return {
        "nav_id": row["id"],
        "fund_id": row["fund_id"],
        "fund_name": row["fund_name"],
        "fund_code": row["fund_code"],
        "nav_date": nav_date.strftime("%Y-%m-%d"),
        "nav": float(row["nav"]),
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": updated_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


def check_fund_exists(cursor, fund_id):
    cursor.execute(
        "SELECT id FROM funds WHERE id = %s",
        (fund_id,)
    )
    return cursor.fetchone() is not None


def find_nav_history_id(cursor, fund_id, nav_date):
    cursor.execute(
        """
        SELECT id
        FROM nav_history
        WHERE fund_id = %s
            AND nav_date = %s
        """,
        (fund_id, nav_date)
    )
    row = cursor.fetchone()

    if row is None:
        return None

    return row["id"]


def fetch_nav_history_by_id(cursor, nav_history_id):
    cursor.execute(
        """
        SELECT
            n.id,
            n.fund_id,
            f.name AS fund_name,
            f.fund_code,
            n.nav_date,
            n.nav,
            n.created_at,
            n.updated_at
        FROM nav_history n
        JOIN funds f ON f.id = n.fund_id
        WHERE n.id = %s
        """,
        (nav_history_id,)
    )
    row = cursor.fetchone()

    if row is None:
        return None

    return serialize_nav_history(row)


@nav_history_bp.post("/api/v1/nav-history")
def upsert_nav_history():
    payload, error_response = parse_nav_payload()

    if error_response is not None:
        return error_response

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            if not check_fund_exists(cursor, payload["fund_id"]):
                return error(
                    code="FUND_NOT_FOUND",
                    message="基金不存在",
                    details=[],
                    http_status=404
                )

            existing_id = find_nav_history_id(
                cursor,
                payload["fund_id"],
                payload["nav_date"]
            )

            if existing_id is None:
                cursor.execute(
                    """
                    INSERT INTO nav_history(
                        fund_id,
                        nav_date,
                        nav
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        payload["fund_id"],
                        payload["nav_date"],
                        payload["nav"]
                    )
                )
                nav_history_id = cursor.lastrowid
            else:
                cursor.execute(
                    """
                    UPDATE nav_history
                    SET nav = %s
                    WHERE id = %s
                    """,
                    (
                        payload["nav"],
                        existing_id
                    )
                )
                nav_history_id = existing_id

            conn.commit()
            data = fetch_nav_history_by_id(cursor, nav_history_id)
    finally:
        conn.close()

    return success(data=data)


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
        code_to_id
        for code in unique_codes
        if code not in code_to_id
    ]

    return code_to_id, missing_codes


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