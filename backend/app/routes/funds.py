from flask import Blueprint, request

from app.db import get_connection
from app.utils.responses import error, success
from app.utils.list_params import parse_list_query_params

funds_bp = Blueprint("funds", __name__)

def parse_fund_id(value):
    if isinstance(value, bool):
        return None

    try:
        fund_id = int(value)
    except (TypeError, ValueError):
        return None 

    if fund_id <= 0:
        return None

    return fund_id

def serialize_fund(row):
    created_at = row['created_at']
    updated_at = row['updated_at']

    return {
        'fund_id': row['id'],
        'name': row['name'],
        'fund_code': row['fund_code'],
        'created_at': created_at.strftime("%Y-%m-%d %H:%M:%S"),
        'updated_at': updated_at.strftime("%Y-%m-%d %H:%M:%S"),
    }

def fetch_fund(cursor, fund_id):
    cursor.execute(
        """
        SELECT
            id, 
            name,
            fund_code,
            created_at,
            updated_at
        FROM funds
        WHERE id = %s
        """,
        (fund_id)
    )
    row = cursor.fetchone()

    if row is None:
        return None

    return serialize_fund(row)

def parse_list_params():
    details = []
    keyword = request.args.get("keyword", "").strip()

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
        "keyword": keyword,
        "page": common_params["page"],
        "page_size": common_params["page_size"],
        "offset": common_params["offset"]
    }, None

def parse_fund_payload():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None, error(
            code='VALIDATION_ERROR',
            message='请求体必须是 JSON 对象',
            details=[],
            http_status=400
        )

    name = data.get('name')
    fund_code = data.get('fund_code')
    details = []

    if not isinstance(name, str) or not name.strip():
        details.append({"field": "name", "message": "基金名称不能为空"})

    if not isinstance(fund_code, str) or not fund_code.strip():
        details.append({"field": "fund_code", "message": "基金代码不能为空"})

    if details:
        return None, error(
            code='VALIDATION_ERROR',
            message='参数校验失败',
            details=details,
            http_status=400
        )

    return {
        'name': name.strip(),
        'fund_code': fund_code.strip()
    }, None

@funds_bp.get('/api/v1/funds')
def list_funds():
    params, error_response = parse_list_params()

    if error_response is not None:
        return error_response

    conditions = []
    values = []

    if params["keyword"]:
        conditions.append("(name LIKE %s OR fund_code LIKE %s)")
        values.extend(
            [
                f"%{params['keyword']}%",
                f"%{params['keyword']}%"
            ]
        )

    where_sql = " AND ".join(conditions) if conditions else "1 = 1"
    offset = params["offset"]
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            count_sql = f"SELECT COUNT(*) AS total FROM funds WHERE {where_sql}"
            cursor.execute(count_sql, values)
            total_row = cursor.fetchone()
            total = total_row['total']

            list_sql = f"""
                SELECT
                    id, 
                    name,
                    fund_code,
                    created_at,
                    updated_at
                FROM funds
                WHERE {where_sql}
                ORDER BY id ASC
                LIMIT %s OFFSET %s
            """
            query_values = values + [params["page_size"], offset]
            cursor.execute(list_sql, query_values)
            rows = cursor.fetchall()
    finally:
        conn.close()

    return success(
        data={
            "items": [serialize_fund(row) for row in rows],
            "page": params["page"],
            "page_size": params["page_size"],
            "total": total    
        }
    
    )

@funds_bp.post('/api/v1/funds')
def create_fund():
    payload, error_response = parse_fund_payload()

    if error_response is not None:
        return error_response

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM funds
                WHERE fund_code = %s
                LIMIT 1
                """,
                (payload["fund_code"],)
            )
            duplicated_row = cursor.fetchone()

            if duplicated_row is not None:
                return error(
                    code="FUND_CODE_DUPLICATED",
                    message='基金代码已经存在',
                    details=[],
                    http_status=409
                )

            cursor.execute(
                """
                INSERT INTO funds (name, fund_code)
                VALUES (%s, %s)
                """,
                (payload["name"], payload["fund_code"])
            )
            fund_id = cursor.lastrowid
            conn.commit()
            data = fetch_fund(cursor, fund_id)
    finally:
        conn.close()

    return success(data=data)

@funds_bp.put('/api/v1/funds/<fund_id>')
def update_fund(fund_id):
    fund_id = parse_fund_id(fund_id)

    if fund_id is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "fund_id",
                    "message": "基金ID必须为正整数"
                }
            ],
            http_status=400
        )

    payload, error_response = parse_fund_payload()

    if error_response is not None:
        return error_response

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM funds WHERE id = %s",
                (fund_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return error(
                    code="FUND_NOT_FOUND",
                    message="基金不存在",
                    details=[],
                    http_status=404
                )

            cursor.execute(
                """
                SELECT id 
                FROM funds
                WHERE fund_code = %s AND id <> %s
                LIMIT 1
                """,
                (payload["fund_code"], fund_id)
            )
            duplicated_row = cursor.fetchone()

            if duplicated_row is not None:
                return error(
                    code="FUND_CODE_DUPLICATED",
                    message="基金代码已经存在",
                    details=[],
                    http_status=409
                )

            cursor.execute(
                """
                UPDATE funds
                SET name = %s,
                    fund_code = %s
                WHERE id = %s
                """,
                (
                    payload["name"],
                    payload["fund_code"],
                    fund_id
                )
            )
            conn.commit()
            data = fetch_fund(cursor, fund_id)
    finally:
        conn.close()

    return success(data=data)