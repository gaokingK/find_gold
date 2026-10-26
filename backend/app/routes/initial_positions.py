from datetime import datetime 

from flask import Blueprint, request

from app.db import get_connection
from app.utils.responses import error, success 
from app.utils.list_params import parse_list_query_params

initial_positions_bp = Blueprint("initial_positions", __name__)


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

def parse_non_negative_number(value):
    if isinstance(value, bool):
        return None

    if not isinstance(value, (int, float)):
        return None

    if value < 0:
        return None

    return float(value)

def serialize_initial_position(row):
    record_date = row["record_date"]

    return {
        "initial_position_id": row["id"],
        "blogger_id": row["blogger_id"],
        "blogger_name": row["blogger_name"],
        "fund_id": row["fund_id"],
        "fund_name": row["fund_name"],
        "fund_code": row["fund_code"],
        "shares": float(row["shares"]),
        "cost_amount": float(row["cost_amount"]),
        "record_date": record_date.strftime("%Y-%m-%d"),
    }

def fetch_initial_position(cursor, initial_position_id):
    cursor.execute(
        """
        SELECT
            ip.id,
            ip.blogger_id,
            b.name AS blogger_name,
            ip.fund_id,
            f.name AS fund_name,
            f.fund_code,
            ip.shares,
            ip.cost_amount,
            ip.record_date
        FROM initial_positions ip
        JOIN bloggers b ON b.id = ip.blogger_id
        JOIN funds f ON f.id = ip.fund_id
        WHERE ip.id = %s
        """,
        (initial_position_id,)
    )
    row = cursor.fetchone()

    if row is None:
        return None

    return serialize_initial_position(row)

def parse_list_params():
    details = []
    blogger_id = None
    fund_id = None

    raw_blogger_id = request.args.get("blogger_id")
    raw_fund_id = request.args.get("fund_id")

    if raw_blogger_id not in (None, ""):
        blogger_id = parse_positive_int(raw_blogger_id)

        if blogger_id is None:
            details.append(
                {
                    "field": "blogger_id",
                    "message": "博主ID必须为正整数"
                }
            )

    if raw_fund_id not in (None, ""):
        fund_id = parse_positive_int(raw_fund_id)

        if fund_id is None:
            details.append(
                {
                    "field": "fund_id",
                    "message": "基金ID必须为正整数"
                }
            )

    common_params, common_details = parse_list_query_params(
        default_sort_by=None,
        allowed_sort_fields=None,
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
        "blogger_id": blogger_id,
        "fund_id": fund_id,
        "page": common_params["page"],
        "page_size": common_params["page_size"],
        "offset": common_params["offset"]
    }, None

def parse_position_payload():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None, error(
            code="VALIDATION_ERROR",
            message="请求体必须是JSON对象",
            details=[],
            http_status=400
        )

    blogger_id = parse_positive_int(data.get("blogger_id"))
    fund_id = parse_positive_int(data.get("fund_id"))
    shares = parse_non_negative_number(data.get("shares"))
    cost_amount = parse_non_negative_number(data.get("cost_amount"))
    record_date = data.get("record_date")
    details = []

    if blogger_id is None:
        details.append(
            {
                "field": "blogger_id",
                "message": "博主ID必须为正整数"
            }
        )

    if fund_id is None:
        details.append(
            {
                "field": "fund_id",
                "message": "基金ID必须为正整数"
            }
        )

    if shares is None:
        details.append(
            {
                "field": "shares",
                "message": "份额必须大于等于0的数字"
            }
        )

    if cost_amount is None:
        details.append(
            {
                "field": "cost_amount",
                "message": "成本金额必须是大于等于0的数字"
            }
        )

    parsed_record_date = None

    if not isinstance(record_date, str):
        details.append(
            {
                "field": "record_date",
                "message": "记录日期不能为空"
            }
        )
    else:
        try:
            parsed_record_date = datetime.strptime(
                record_date,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            details.append(
                {
                    "field": "record_date",
                    "message": "记录日期格式必须是 YYYY-MM-DD"
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
        "blogger_id": blogger_id,
        "fund_id": fund_id,
        "shares": shares,
        "cost_amount": cost_amount,
        "record_date": parsed_record_date
    }, None

def check_blogger_exists(cursor, blogger_id):
    cursor.execute(
        "SELECT id FROM bloggers WHERE id = %s",
        (blogger_id,)
    )
    return cursor.fetchone() is not None

def check_fund_exists(cursor, fund_id):
    cursor.execute(
        "SELECT id FROM funds WHERE id = %s",
        (fund_id,)
    )
    return cursor.fetchone() is not None

@initial_positions_bp.get("/api/v1/initial-positions")
def list_initial_positions():
    params, error_response = parse_list_params()

    if error_response is not None:
        return error_response

    conditions = []
    values = []

    if params["blogger_id"] is not None:
        conditions.append("ip.blogger_id = %s")
        values.append(params["blogger_id"])

    if params["fund_id"] is not None:
        conditions.append("ip.fund_id = %s")
        values.append(params["fund_id"])

    where_sql = " AND ".join(conditions) if conditions else "1 = 1"
    offset = params["offset"]
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            count_sql = f"""
                SELECT COUNT(*) AS total
                FROM initial_positions ip
                WHERE {where_sql}
            """
            cursor.execute(count_sql, values)
            total_row = cursor.fetchone()
            total = total_row["total"]

            list_sql = f"""
                SELECT
                    ip.id,
                    ip.blogger_id,
                    b.name AS blogger_name,
                    ip.fund_id,
                    f.name AS fund_name,
                    f.fund_code,
                    ip.shares,
                    ip.cost_amount,
                    ip.record_date
                FROM initial_positions ip
                JOIN bloggers b ON b.id = ip.blogger_id
                JOIN funds f ON f.id = ip.fund_id
                WHERE {where_sql}
                ORDER BY ip.id DESC
                LIMIT %s OFFSET %s
            """
            query_values = values + [params["page_size"], offset]
            cursor.execute(list_sql, query_values)
            rows = cursor.fetchall()
    finally:
        conn.close()

    return success(
        data={
            "items": [serialize_initial_position(row) for row in rows],
            "page": params["page"],
            "page_size": params["page_size"],
            "total": total
        }
    )

@initial_positions_bp.post("/api/v1/initial-positions")
def create_initial_position():
    payload, error_response = parse_position_payload()

    if error_response is not None:
        return error_response

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            if not check_blogger_exists(cursor, payload["blogger_id"]):
                return error(
                    code="BLOGGER_NOT_FOUND",
                    message="博主不存在",
                    details=[],
                    http_status=404
                )

            if not check_fund_exists(cursor, payload["fund_id"]):
                return error(
                    code="FOUND_NOT_FOUND",
                    message="基金不存在",
                    details=[],
                    http_status=404
                )

            cursor.execute(
                """
                SELECT id
                FROM initial_positions
                WHERE blogger_id = %s
                    AND fund_id = %s
                    AND record_date = %s
                LIMIT 1
                """,
                (
                    payload["blogger_id"],
                    payload["fund_id"],
                    payload["record_date"]
                )
            )
            duplicated_row = cursor.fetchone()

            if duplicated_row is not None:
                return error(
                    code="INITIAL_POSITION_DUPLICATED",
                    message="同一博主、同一基金、同一记录日期的初始持仓已经存在",
                    details=[],
                    http_status=409
                )

            cursor.execute(
                """
                INSERT INTO initial_positions (
                    blogger_id,
                    fund_id,
                    shares,
                    cost_amount,
                    record_date
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    payload["blogger_id"],
                    payload["fund_id"],
                    payload["shares"],
                    payload["cost_amount"],
                    payload["record_date"]
                )
            )
            initial_positions_id = cursor.lastrowid
            conn.commit()
            data = fetch_initial_position(cursor, initial_positions_id)
    finally:
        conn.close()

    return success(data=data)

@initial_positions_bp.put("/api/v1/initial-positions/<initial_position_id>")
def update_initial_position(initial_position_id):
    initial_position_id = parse_positive_int(initial_position_id)

    if initial_position_id is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "initial_position_id",
                    "message": "初始持仓ID必须为正整数"
                }
            ],
            http_status=400
        )

    payload, error_response = parse_position_payload()

    if error_response is not None:
        return error_response

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM initial_positions WHERE id = %s",
                (initial_position_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return error(
                    code="INITIAL_POSITION_NOT_FOUND",
                    message="初始持仓不存在",
                    details=[],
                    http_status=404
                )

            if not check_blogger_exists(cursor, payload["blogger_id"]):
                return error(
                    code="BLOGGER_NOT_FOUND",
                    message="博主不存在",
                    details=[],
                    http_status=404
                )

            if not check_fund_exists(cursor, payload["fund_id"]):
                return error(
                    code="FUND_NOT_FOUND",
                    message="基金不存在",
                    details=[],
                    http_status=404
                )

            cursor.execute(
                """
                SELECT id
                FROM initial_positions
                WHERE blogger_id = %s
                    AND fund_id = %s
                    AND record_date = %s
                    AND id <> %s
                LIMIT 1
                """,
                (
                    payload["blogger_id"],
                    payload["fund_id"],
                    payload["record_date"],
                    initial_position_id
                )
            )
            duplicated_row = cursor.fetchone()

            if duplicated_row is not None:
                return error(
                    code="INITIAL_POSITION_DUPLICATED",
                    message="同一博主、同一基金、同一记录日期的初始持仓已经存在",
                    details=[],
                    http_status=409
                )

            cursor.execute(
                """
                UPDATE initial_positions
                SET blogger_id = %s,
                    fund_id = %s,
                    shares = %s,
                    cost_amount = %s,
                    record_date = %s
                WHERE id = %s
                """,
                (
                    payload["blogger_id"],
                    payload["fund_id"],
                    payload["shares"],
                    payload["cost_amount"],
                    payload["record_date"],
                    initial_position_id
                )
            )
            conn.commit()
            data = fetch_initial_position(cursor, initial_position_id)
    finally:
        conn.close()

    return success(data=data)

