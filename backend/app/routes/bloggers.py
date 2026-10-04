# 数据库查询

from datetime import date

from flask import Blueprint, request

from app.db import get_connection
from app.utils.responses import error, success

bloggers_bp = Blueprint("bloggers", __name__)

ALLOWED_SORT_FIELDS = {
    'name': 'b.name',
    'observe_start_date': 'b.observe_start_date',
    'observe_days': 'observe_days',
    'created_at': 'b.created_at'
}

def calculate_status(observe_days):
    if observe_days is None:
        return 'inactive'

    if observe_days < 30:
        return 'obsering'

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
    keyword = request.args.get('keyword', '').strip()
    sector = request.args.get('sector', '').strip()
    status = request.args.get('status', '').strip()
    sort_by = request.args.get('sort_by', 'created_at')
    order = request.args.get('order', 'desc').lower()

    try:
        page = int(request.args.get('page', '1'))
        page_size = int(request.args.get('page_size', '20'))
    except ValueError:
        return None, error(
            code='VALIDATION_ERROR',
            message='分页参数不合法',
            details=[
                {
                    'field': 'page/page_size',
                    'message': 'page and page_size must be int'
                }
            ],
            http_status=400
        )

    if page < 1:
        return None, error(
            code='VALIDATION_ERROR',
            message='page参数不合法',
            details=[
                {
                    'field': 'page', 
                    'message': 'page must be > 1'
                }
            ],
            http_status=400
        )

    if page_size < 1 or page_size > 100:
        return None, error(
            code='VALIDATION_ERROR',
            message='page_size参数不合法',
            details=[
                {
                    'field': 'page_size',
                    'message': 'page_size must be between 1 and 100'
                }
            ],
            http_status=400
        )

    if status and status not in ['observing', 'active']:
        return None, error(
            code='VALIDATION_ERROR',
            message='status不合法',
            details=[
                {
                    'field': 'status',
                    'message': 'status allow observing or active'
                }
            ],
            http_status=400
        )

    if sort_by not in ALLOWED_SORT_FIELDS:
        return None, error(
            code='VALIDATION_ERROR',
            message='sort_by 参数不合法',
            details=[
                {
                    'field': 'sort_by',
                    'message': 'sort_by allow name, observe_start_date, observe_days, created_at'
                }
            ],
            http_status=400
        )

    if order not in ['asc', 'desc']:
        return None, error(
            code='VALIDATION_ERROR',
            message='order parse不合法',
            details=[
                {
                    'field': 'order',
                    'message': 'order allow asc or desc'
                }
            ],
            http_status=400
        )

    params = {
        'keyword': keyword,
        'sector': sector,
        'status': status,
        'sort_by': sort_by,
        'order': order,
        'page': page,
        'page_size': page_size
    }
    return params, None

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
    sort_column = ALLOWED_SORT_FIELDS[params['sort_by']]
    order_sql = 'ASC' if params['order'] == 'asc' else 'DESC'
    offset = (params['page'] - 1) * params['page_size']

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