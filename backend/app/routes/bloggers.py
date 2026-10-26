# 数据库查询

from datetime import date, datetime

from flask import Blueprint, request
from pymysql.err import IntegrityError

from app.db import get_connection
from app.utils.responses import error, success
from app.utils.list_params import parse_list_query_params

bloggers_bp = Blueprint("bloggers", __name__)

ALLOWED_SORT_FIELDS = {
    'name': 'b.name',
    'observe_start_date': 'b.observe_start_date',
    'observe_days': 'observe_days',
    'created_at': 'b.created_at'
}

def parse_create_blogger_payload():
    data = request.get_json(silent=True)

    print("DEBUG DATA:", data)
    if not isinstance(data, dict):
        return None, error(
            code='VALIDATION_ERROR',
            message='请求体必须是JOSN对象',
            details=[],
            http_status=400
        )

    name = data.get('name')
    sector = data.get('sector')
    observe_start_date = data.get('observe_start_date')

    details = []

# 进行数据校验，非空校验，和类型校验
    if not isinstance(name, str) or not name.strip():
        details.append(
            {
                'field': 'name',
                'message': 'blogger not be empty'
            }
        )

    if not isinstance(sector, str) or not sector.strip():
        details.append(
            {
                'field': 'sector',
                'message': '所属板块不能为空'
            }
        )

    parsed_date = None

    if not isinstance(observe_start_date, str) or not observe_start_date.strip():
        details.append(
            {
                'field': 'observe_start_date',
                'message': '观察开始日不能为空'
            }
        )
    else:
        try:
            parsed_date = datetime.strptime(
                observe_start_date,
                '%Y-%m-%d'
            ).date()
        except ValueError:
            details.append(
                {
                    'field': 'observe_start_date',
                    'message': '观察开始日格式必须为YYYY-MM-DD'
                }
            )

    if details:
        return None, error(
            code='VALIDATION_ERROR',
            message='参数校验失败',
            details=details,
            http_status=400
        )

    return {
        'name': name.strip(),
        'sector': sector.strip(),
        'observe_start_date': parsed_date
    }, None

def calculate_status(observe_days):
    if observe_days is None:
        return 'inactive'

    if observe_days < 30:
        return 'observing'

    return 'active'

def serialize_blogger(row):
    observe_start_date =row['observe_start_date']
    created_at = row['created_at']
    updated_at = row['updated_at']

    return {
        'blogger_id': row['id'],
        'name': row['name'],
        'sector': row['sector'],
        'observe_start_date': observe_start_date.strftime("%Y-%m-%d"),
        'observe_days': row['observe_days'],
        'status': calculate_status(row['observe_days']),
        'created_at': created_at.strftime("%Y-%m-%d %H:%M:%S"),
        'updated_at': updated_at.strftime("%Y-%m-%d %H:%M:%S"),
    }

def parse_common_params():
    details = []
    keyword = request.args.get("keyword", "").strip()
    sector = request.args.get("sector", "").strip()
    status = request.args.get("status", "").strip()

    if status and status not in ["observing", "active"]:
        details.append(
            {
                "field": "status",
                "message": "status 只允许observing或active"
            }
        )

    raw_order = request.args.get("order")
    if raw_order:
        request.args = request.args.copy()
        request.args["order"] = raw_order.lower()

    common_params, common_details = parse_list_query_params(
        default_sort_by="created_at",
        allowed_sort_fields=ALLOWED_SORT_FIELDS,
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
        "sector": sector,
        "status": status,
        "sort_column": common_params["sort_column"],
        "order": common_params["order"],
        "page": common_params["page"],
        "page_size": common_params["page_size"],
        "offset": common_params["offset"]
    }, None
 
# 动态构建SQL查询的WHERE子句机器对应的参数列表
def build_conditions(params):
    conditions = []
    values = []

    if params['keyword']:
        conditions.append('b.name LIKE %s')
        values.append(f"%{params['keyword']}%")

    if params['sector']:
        conditions.append('b.sector = %s')
        values.append(params['sector'])

    if params['status'] == 'observing':
        conditions.append('DATEDIFF(CURDATE(), b.observe_start_date) < 30')

    if params['status'] == 'active': 
        conditions.append('DATEDIFF(CURDATE(), b.observe_start_date) >= 30')

    where_sql = " AND ".join(conditions) if conditions else "1 = 1"
    return where_sql, values

@bloggers_bp.get('/api/v1/bloggers')
def list_bloggers():
    params, error_response = parse_common_params()

    if error_response is not None:
        return error_response

    where_sql, values = build_conditions(params)

    sort_column = params["sort_column"]
    order_sql = 'ASC' if params['order'] == 'asc' else 'DESC'
    offset = params["offset"]

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            count_sql = f"SELECT COUNT(*) AS total FROM bloggers b WHERE {where_sql}"
            cursor.execute(count_sql, values)
            total_row = cursor.fetchone()
            total = total_row['total']

            list_sql = f"""
                SELECT
                    b.id,
                    b.name,
                    b.sector,
                    b.observe_start_date,
                    DATEDIFF(CURDATE(), b.observe_start_date) AS observe_days,
                    b.created_at,
                    b.updated_at
                FROM bloggers b
                WHERE {where_sql}
                ORDER BY {sort_column} {order_sql}
                LIMIT %s OFFSET %s
            """
            query_values = values + [params['page_size'], offset]
            cursor.execute(list_sql, query_values)
            rows = cursor.fetchall()
    finally:
        conn.close()

    return success(
        {
            'items': [serialize_blogger(row) for row in rows],
            'page': params['page'],
            'page_size': params['page_size'],
            'total': total
        }
    )

@bloggers_bp.post('/api/v1/bloggers')
def create_bloggers():
    payload, error_response = parse_create_blogger_payload()

    if error_response is not None:
        return error_response

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT id FROM bloggers WHERE name = %s', 
                (payload['name'],)
            )
            existing = cursor.fetchone()

            if existing:
                return error(
                    code='BLOGGER_NAME_DUPLICATED',
                    message='博主名称已经存在',
                    details=[],
                    http_status=409
                )

            cursor.execute(
                """
                INSERT INTO bloggers (name, sector, observe_start_date)
                VALUES (%s, %s, %s)
                """,
                (
                    payload['name'],
                    payload['sector'],
                    payload['observe_start_date']
                )
            )
            blogger_id = cursor.lastrowid

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    sector,
                    observe_start_date,
                    DATEDIFF(CURDATE(), observe_start_date) AS observe_days,
                    created_at,
                    updated_at
                FROM bloggers
                WHERE id = %s
                """,
                (blogger_id,)
            )
            row = cursor.fetchone()

        conn.commit()
    finally:
        conn.close()

    return success(serialize_blogger(row))

def parse_blogger_id(value):
    if isinstance(value, bool):
        return None

    try:
        blogger_id = int(value)
    except (TypeError, ValueError):
        return None

    if blogger_id <= 0:
        return None

    return blogger_id

def fetch_blogger(cursor, blogger_id):
    cursor.execute(
        """
        SELECT
            id, 
            name,
            sector,
            observe_start_date,
            DATEDIFF(CURDATE(), observe_start_date) AS observe_days,
            created_at,
            updated_at
        FROM bloggers
        WHERE id = %s
        """,
        (blogger_id,)
    )
    row = cursor.fetchone()

    if row is None:
        return None

    return serialize_blogger(row)

def parse_update_blogger_payload():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None, error(
            code='VALIDATION_ERROR',
            message='请求体必须是JSON对象',
            details=[],
            http_status=400
        )

    name = data.get('name')
    sector = data.get('sector')
    observe_start_date = data.get('observe_start_date')
    details= []

    if not isinstance(name, str) or not name.strip():
        details.append({'field': 'name', 'message': '博主名称不能为空'})

    if not isinstance(sector, str) or not sector.strip():
        details.append({'field': 'sector', 'message': '所属板块不能为空'})

    if not isinstance(observe_start_date, str):
        details.append({'field': 'observe_start_date', 'message': '观察开始日不能为空'})
    else:
        try:
            observe_start_date = datetime.strptime(
                observe_start_date,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            details.append(
                {
                    'field': 'observe_start_date',
                    'message': '观察开始日格式必须是 YYYY-MM-DD'
                }
            )

    if details:
        return None, error(
            code='VALIDATION_ERROR',
            message='参数校验失败',
            details=details,
            http_status=400
        )

    return {
        'name': name.strip(),
        'sector': sector.strip(),
        'observe_start_date': observe_start_date
    }, None

@bloggers_bp.get('/api/v1/bloggers/<blogger_id>')
def get_blogger(blogger_id):
    blogger_id = parse_blogger_id(blogger_id)

    if blogger_id is None:
        return error(
            code='VALIDATION_ERROR',
            message='参数校验失败',
            details=[
                {
                    'field': 'blogger_id',
                    'message': '博主ID必须为正整数'
                }
            ],
            http_status=400
        )

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            data = fetch_blogger(cursor, blogger_id)
    finally:
        conn.close()

    if data is None:
        return error(
            code='BLOGGER_NOT_FOUND',
            message='博主不存在',
            details=[],
            http_status=404
        )

    return success(data=data)

@bloggers_bp.put('/api/v1/bloggers/<blogger_id>')
def update_blogger(blogger_id):
    blogger_id = parse_blogger_id(blogger_id)

    if blogger_id is None:
        return error(
            code='VALIDATION_ERROR',
            message='参数校验失败',
            details=[
                {
                    'field': 'blogger_id',
                    'message': '博主ID必须为正整数'
                }
            ],
            http_status=400
        )

    payload, error_response = parse_update_blogger_payload()

    if error_response is not None:
        return error_response

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT id FROM bloggers WHERE id = %s',
                (blogger_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return error(
                    code='BLOGGER_NOT_FOUND',
                    message='博主不存在',
                    details=[],
                    http_status=404
                )

            cursor.execute(
                """
                SELECT id
                FROM bloggers
                WHERE name = %s AND id <> %s
                LIMIT 1
                """,
                (payload['name'], blogger_id)
            )
            duplicated_row = cursor.fetchone()

            if duplicated_row is not None:
                return error(
                    code='BLOGGER_NAME_DUPLICATED',
                    message='博主名称已存在',
                    details=[],
                    http_status=409
                )

            cursor.execute(
                """
                UPDATE bloggers
                SET name = %s,
                    sector = %s,
                    observe_start_date = %s
                WHERE id = %s
                """,
                (
                    payload['name'],
                    payload['sector'],
                    payload['observe_start_date'],
                    blogger_id
                )
            )
            conn.commit()
            data = fetch_blogger(cursor, blogger_id)
    finally:
        conn.close()

    return success(data=data)

@bloggers_bp.delete('/api/v1/bloggers/<blogger_id>')
def delete_blogger(blogger_id):
    blogger_id = parse_blogger_id(blogger_id)

    if blogger_id is None:
        return error(
            code='VALIDATION_ERROR',
            message='参数校验失败',
            details=[
                {
                    'field': 'blogger_id',
                    'message': '博主ID必须为正整数'
                }
            ],
            http_status=400
        )

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT id FROM bloggers WHERE id = %s',
                (blogger_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return error(
                    code='BLOGGER_NOT_FOUND',
                    message='博主不存在',
                    details=[],
                    http_status=404
                )

            cursor.execute(
                'DELETE FROM operations WHERE blogger_id = %s',
                (blogger_id,)
            )

            cursor.execute(
                'DELETE FROM initial_positions WHERE blogger_id = %s',
                (blogger_id,)
            )
            cursor.execute(
                'DELETE FROM bloggers WHERE id = %s',
                (blogger_id,)
            )
            conn.commit()
    finally:
        conn.close()

    return success(data={})
