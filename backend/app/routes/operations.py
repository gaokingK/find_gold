from datetime import date, datetime

from flask import Blueprint, request

from app.db import get_connection
from app.utils.responses import error, success
from app.utils.list_params import parse_list_query_params


operations_bp = Blueprint("operations", __name__)


ALLOWED_OPERATION_TYPES = {
    "buy",
    "sell",
    "dividend_cash",
}

ALLOWED_OPERATION_SORT_FIELDS = {
    "operation_date": "o.operation_date",
    "amount": "o.amount",
    "created_at": "o.created_at",
}


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


def parse_operation_payload():
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
    operation_type = data.get("operation_type")
    operation_date = data.get("operation_date")
    shares = data.get("shares")
    amount = data.get("amount")
    remark = data.get("remark")

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

    if operation_type not in ALLOWED_OPERATION_TYPES:
        details.append(
            {
                "field": "operation_type",
                "message": "操作类型值允许 buy、 sell、dividend_cash"
            }
        )

    parsed_operation_date = None

    if not isinstance(operation_date, str):
        details.append(
            {
                "field": "operation_date",
                "message": "操作日期提起不能为空"
            }
        )
    else:
        try:
            parsed_operation_date = datetime.strptime(
                operation_date,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            details.append(
                {
                    "field": "operation_date",
                    "message": "操作日期格式必须是 YYYY-MM-DD"
                }
            )

        if parsed_operation_date is not None:
            if parsed_operation_date > date.today():
                details.append(
                    {
                        "field": "operation_date",
                        "message": "操作日期不能晚于今天"
                    }
                )
                parsed_operation_date = None

    if shares is None and operation_type == "dividend_cash":
        parsed_shares = 0.0
    elif not isinstance(shares, (int, float)) or isinstance(shares, bool):
        details.append(
            {
                "field": "shares",
                "message": "份额必须是数字"
            }
        )
        parsed_shares = None
    else:
        parsed_shares = float(shares)

    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        details.append(
            {
                "field": "amount",
                "message": "金额必须是数字"
            }
        )
        parsed_amount = None
    else:
        parsed_amount = float(amount)

    if operation_type == "buy" or operation_type == "sell":
        if parsed_shares is not None and parsed_shares <= 0:
            details.append(
                {
                    "field": "shares",
                    "message": "买入和卖出份额必须大于0"
                }
            )

        if parsed_amount is not None and parsed_amount <= 0:
            details.append(
                {
                    "field": "amount",
                    "message": "买入和卖出金额必须大于0"
                }
            )

    if operation_type == "dividend_cash":
        if parsed_shares is not None and parsed_shares != 0:
            details.append(
                {
                    "field": "shares",
                    "message": "现金分红的份额必须等于0"
                }
            )

        if parsed_amount is not None and parsed_amount <= 0:
            details.append(
                {
                    "field": "amount",
                    "message": "现金分红金额必须大于0"
                }
            )

    parsed_remark = None

    if remark not in (None, ""):
        if not isinstance(remark, str):
            details.append(
                {
                    "field": "remark",
                    "message": "备注必须是字符串"
                }
            )
        elif len(remark.strip()) > 255:
            details.append(
                {
                    "field": "remark",
                    "message": "备注不能超过255个字符"
                }
            )
        else:
            parsed_remark = remark.strip()

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
        "operation_date": parsed_operation_date,
        "operation_type": operation_type,
        "shares": parsed_shares,
        "amount": parsed_amount,
        "remark": parsed_remark
    }, None


def serialize_operation(row):
    operation_date = row["operation_date"]
    created_at = row["created_at"]
    updated_at = row["updated_at"]

    return {
        "operation_id": row["id"],
        "blogger_id": row["blogger_id"],
        "fund_id": row["fund_id"],
        "blogger_name": row["blogger_name"],
        "fund_name": row["fund_name"],
        "fund_code": row["fund_code"],
        "operation_date": operation_date.strftime("%Y-%m-%d"),
        "operation_type": row["operation_type"],
        "shares": float(row["shares"]),
        "amount": float(row["amount"]),
        "remark": row["remark"],
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": updated_at.strftime("%Y-%m-%d %H:%M:%S"),
    }

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

def fetch_operation_by_id(cursor, operation_id):
    cursor.execute(
        """
        SELECT
            o.id,
            o.blogger_id,
            b.name AS blogger_name,
            o.fund_id,
            f.name AS fund_name,
            f.fund_code,
            o.operation_type,
            o.operation_date,
            o.shares,
            o.amount,
            o.remark,
            o.created_at,
            o.updated_at
        FROM operations o
        JOIN bloggers b ON b.id = o.blogger_id
        JOIN funds f ON f.id = o.fund_id
        WHERE o.id = %s
        """,
        (operation_id,)
    )
    row = cursor.fetchone()

    if row is None:
        return None

    return serialize_operation(row)

def fetch_initial_position_date(cursor, blogger_id, fund_id):
    cursor.execute(
        """
        SELECT MIN(record_date) AS first_record_date
        FROM initial_positions
        WHERE blogger_id = %s AND fund_id = %s
        """,
        (blogger_id, fund_id)
    )
    row = cursor.fetchone()

    if row is None:
        return None

    return row["first_record_date"]

@operations_bp.post("/api/v1/operations")
def create_operation():
    payload, error_response = parse_operation_payload()

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
                    code="FUND_NOT_FOUND",
                    message="基金不存在",
                    details=[],
                    http_status=404
                )

            first_record_date = fetch_initial_position_date(
                cursor,
                payload["blogger_id"],
                payload["fund_id"]
            )

            if first_record_date is not None:
                if payload["operation_date"] < first_record_date:
                    return error(
                        code="VALIDATION_ERROR",
                        message="参数校验失败",
                        details=[
                            {
                                "field": "operation_date",
                                "message": (
                                    "操作日期不能早于初始持仓记录日期"
                                    f"{first_record_date.strftime('%Y-%m-%d')}"
                                )
                            }
                        ],
                        http_status=400
                    )

            cursor.execute(
                """
                INSERT INTO operations(
                blogger_id,
                fund_id,
                operation_date,
                operation_type,
                shares,
                amount,
                remark
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    payload["blogger_id"],
                    payload["fund_id"],
                    payload["operation_date"],
                    payload["operation_type"],
                    payload["shares"],
                    payload["amount"],
                    payload["remark"]
                )
            )
            operation_id = cursor.lastrowid
            conn.commit()

            data = fetch_operation_by_id(cursor, operation_id)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    return success(data=data)

def parse_operation_list_params():
    details =[]

    blogger_id = None
    fund_id = None
    operation_type = request.args.get("operation_type")

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

    if operation_type not in (None, "") and operation_type not in ALLOWED_OPERATION_TYPES:
        details.append(
            {
                "field": "operation_type",
                "message": "操作类型只允许 buy、sell、dividend_cash"
            }
        )

    date_from = None
    date_to = None

    raw_date_from = request.args.get("date_from")
    raw_date_to = request.args.get("date_to")

    if raw_date_from not in (None, ""):
        try:
            date_from = datetime.strptime(
                raw_date_from,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            details.append(
                {
                    "field": "date_from",
                    "message": "date_from格式必须是YYYY-MM-DD"
                }
            )

    if raw_date_to not in (None, ""):
        try:
            date_to = datetime.strptime(
                raw_date_to,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            details.append(
                {
                    "field": "date_to",
                    "message": "date_to格式必须是YYYY-MM-DD"
                }
            )

    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        details.append(
            {
                "field": "date_from",
                "message": "date_from 不能晚于date_to"
            }
        )

    keyword = request.args.get("keyword", "").strip()

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

def build_operation_conditions(params):
    conditions = []
    values = []

    if params["blogger_id"] is not None:
        conditions.append("o.blogger_id = %s")
        values.append(params["blogger_id"])

    if params["fund_id"] is not None:
        conditions.append("o.fund_id = %s")
        values.append(params["fund_id"])

    if params["operation_type"] not in (None, ""):
        conditions.append("o.operation_type = %s")
        values.append(params["operation_type"])

    if params["date_from"] is not None:
        conditions.append("o.operation_date >= %s")
        values.append(params["date_from"])

    if params["date_to"] is not None:
        conditions.append("o.operation_date <= %s")
        values.append(params["date_to"])

    if params["keyword"]:
        conditions.append("o.remark LIKE %s")
        values.append(f"%{params['keyword']}")

    where_sql = " AND ".join(conditions) if conditions else "1 = 1"

    return where_sql, values

@operations_bp.get("/api/v1/operations")
def list_operation():
    params, error_response = parse_operation_list_params()

    if error_response is not None:
        return error_response

    where_sql, values = build_operation_conditions(params)
    sort_column = params["sort_by"]
    order_sql = "ASC" if params["order"] == "asc" else "DESC"
    offset = (params["page"] - 1) * params["page_size"]

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            count_sql = f"""
                SELECT COUNT(*) AS total
                FROM operations o
                WHERE {where_sql}
            """
            cursor.execute(count_sql, values)
            total_row = cursor.fetchone()
            total = total_row["total"]

            list_sql = f"""
                SELECT 
                    o.id,
                    o.blogger_id,
                    b.name AS blogger_name,
                    o.fund_id,
                    f.name AS fund_name,
                    f.fund_code,
                    o.operation_type,
                    o.operation_date,
                    o.shares,
                    o.amount,
                    o.remark,
                    o.created_at,
                    o.updated_at
                FROM operations o
                JOIN bloggers b ON b.id = o.blogger_id
                JOIN funds f ON f.id = o.fund_id
                WHERE {where_sql}
                ORDER BY {sort_column} {order_sql}, o.id DESC
                LIMIT %s OFFSET %s
            """
            query_values = values + [params["page_size"], offset]
            cursor.execute(list_sql, query_values)
            rows = cursor.fetchall()
    finally:
        conn.close()

    return success(
        data={
            "items": [serialize_operation(row) for row in rows],
            "page": params["page"],
            "page_size": params["page_size"],
            "total": total
        }
    )

@operations_bp.delete("/api/v1/operations/<operation_id>")
def delete_operation(operation_id):
    parsed_operation_id = parse_positive_int(operation_id)

    if parsed_operation_id is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "operation_id",
                    "message": "操作记录ID必须为正整数"
                }
            ],
            http_status=400
        )

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM operations WHERE id = %s",
                (parsed_operation_id,)
            )

            if cursor.fetchone() is None:
                return error(
                    code="OPERATION_ERROR",
                    message="操作记录不存在",
                    details=[],
                    http_status=404
                )

            cursor.execute(
                "DELETE FROM operations WHERE id = %s",
                (parsed_operation_id,)
            )

        conn.commit()
    finally:
        conn.close()

    return success(data={"operation_id": parsed_operation_id})