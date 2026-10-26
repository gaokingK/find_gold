from datetime import date

from flask import Blueprint, request

from app.db import get_connection
from app.services.position_snapshot import calculate_position_snapshots
from app.services.return_calculation import (
    calculate_position_returns,
    calculate_total_returns,
)
from app.utils.responses import success, error
from app.utils.snapshot_data import (
    get_initial_positions,
    get_nav_on_date_map,
    get_operations,
    parse_snapshot_date,
)


returns_bp = Blueprint("returns", __name__)


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


def _to_number(value, places):
    if value is None:
        return None

    return round(float(value), places)


def _serialize_return_item(item):
    nav_date = item.get("nav_date")

    return {
        "fund_id": item["fund_id"],
        "fund_name": item["fund_name"],
        "fund_code": item["fund_code"],
        "shares": _to_number(item["shares"], 4),
        "cost_amount": _to_number(item["cost_amount"], 2),
        "nav": _to_number(item["nav"], 4),
        "nav_date": (
            nav_date.strftime("%Y-%m-%d")
            if nav_date is not None
            else None
        ),
        "market_value": _to_number(item["market_value"], 2),
        "profit_amount": _to_number(item["profit_amount"], 2),
        "return_rate": _to_number(item["return_rate"], 6)
    }


@returns_bp.get("/api/v1/bloggers/<blogger_id>/returns")
def get_blogger_returns(blogger_id):
    parsed_blogger_id = parse_positive_int(blogger_id)

    if parsed_blogger_id is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "blogger_id",
                    "message": "博主ID必须为正整数"
                }
            ],
            http_status=400
        )

    return_date = parse_snapshot_date(request.args.get("return_date"))

    if return_date is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "return_date",
                    "message": "收益日期格式必须是 YYYY-MM-DD"
                }
            ],
            http_status=400
        )

    if return_date > date.today():
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "return_date",
                    "message": "收益日期不能晚于今天"
                }
            ],
            http_status=400
        )

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name FROM bloggers WHERE id = %s",
                (parsed_blogger_id,)
            )
            blogger = cursor.fetchone()

            if blogger is None:
                return error(
                    code="BLOGGER_NOT_FOUND",
                    message="博主不存在",
                    details=[],
                    http_status=404
                )

            initial_positions = get_initial_positions(
                cursor,
                parsed_blogger_id,
                return_date
            )
            operations = get_operations(
                cursor,
                parsed_blogger_id,
                return_date
            )
            position_items = calculate_position_snapshots(
                initial_positions,
                operations
            )
            fund_ids = [item["fund_id"] for item in position_items]
            nav_map = get_nav_on_date_map(
                cursor,
                fund_ids,
                return_date
            )
            return_items = calculate_position_returns(
                position_items,
                nav_map
            )
            summary = calculate_total_returns(return_items)
            serialized_items = [
                _serialize_return_item(item)
                for item in return_items
            ]
    finally:
        conn.close()

    return success(
        data={
            "blogger_id": parsed_blogger_id,
            "blogger_name": blogger["name"],
            "return_date": return_date.strftime("%Y-%m-%d"),
            "total_cost_amount": _to_number(
                summary["total_cost_amount"],
                2
            ),
            "total_market_value": _to_number(
                summary["total_market_value"],
                2
            ),
            "profit_amount": _to_number(
                summary["profit_amount"],
                2
            ),
            "return_rate": _to_number(
                summary["return_rate"],
                6
            ),
            "items": serialized_items
        }
    )


@returns_bp.get("/api/v1/bloggers/<blogger_id>/funds/<fund_id>/return")
def get_blogger_fund_return(blogger_id, fund_id):
    parsed_blogger_id = parse_positive_int(blogger_id)

    if parsed_blogger_id is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "blogger_id",
                    "message": "博主ID必须为正整数"
                }
            ],
            http_status=400
        )

    parsed_fund_id = parse_positive_int(fund_id)

    if parsed_fund_id is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "fund_id",
                    "message": "基金ID必须为整数"
                }
            ],
            http_status=400
        )

    return_date = parse_snapshot_date(request.args.get("return_date"))

    if return_date is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "return_date",
                    "message": "收益日期格式必须是 YYYY-MM-DD"
                }
            ],
            http_status=400
        )

    if return_date > date.today():
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "return_date",
                    "message": "收益日期不能晚于今天"
                }
            ],
            http_status=400
        )

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name FROM bloggers WHERE id = %s",
                (parsed_blogger_id,)
            )
            blogger = cursor.fetchone()

            if blogger is None:
                return error(
                    code="BLOGGER_NOT_FOUND",
                    message="博主不存在",
                    details=[],
                    http_status=404
                )

            cursor.execute(
                "SELECT id, name, fund_code FROM funds WHERE id = %s",
                (parsed_fund_id,)
            )
            fund = cursor.fetchone()

            if fund is None:
                return error(
                    code="FOUND_NOT_FOUND",
                    message="基金不存在，或该博主未持有该基金",
                    details=[],
                    http_status=404
                )

            initial_positions = get_initial_positions(
                cursor,
                parsed_blogger_id,
                return_date
            )
            operations = get_operations(
                cursor,
                parsed_blogger_id,
                return_date
            )
            position_items = calculate_position_snapshots(
                initial_positions,
                operations
            )
            fund_ids = [item["fund_id"] for item in position_items]
            nav_map = get_nav_on_date_map(
                cursor,
                fund_ids,
                return_date
            )
            return_items = calculate_position_returns(
                position_items,
                nav_map
            )
            matched_item = next(
                (
                    item
                    for item in return_items
                    if item["fund_id"] == parsed_fund_id
                ),
                None
            )

            if matched_item is None:
                return error(
                    code="FUND_NOT_FOUDN",
                    message="基金不存在，或该博主未持该基金",
                    details=[],
                    http_status=404
                )
    finally:
        conn.close()

    serialized_fund = _serialize_return_item(matched_item)
    serialized_fund.update(
        {
            "blogger_id": parsed_blogger_id,
            "blogger_name": blogger["name"],
            "return_date": return_date.strftime("%Y-%m-%d"),
        }
    )

    return success(data=serialized_fund)


@returns_bp.get("/api/v1/returns/summary")
def get_total_returns_summary():
    return_date = parse_snapshot_date(request.args.get("return_date"))

    if return_date is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "return_date",
                    "message": "收益日期格式必须是 YYYY-MM-DD"
                }
            ],
            http_status=400
        )

    if return_date > date.today():
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "return_date",
                    "message": "收益日期不能晚于今天"
                }
            ],
            http_status=400
        )

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name FROM bloggers ORDER BY id",
            )
            bloggers = cursor.fetchall()

            all_return_items = []
            blogger_summaries = []

            for blogger in bloggers:
                initial_positions = get_initial_positions(
                    cursor,
                    blogger["id"],
                    return_date
                )
                operations = get_operations(
                    cursor,
                    blogger["id"],
                    return_date
                )
                position_items = calculate_position_snapshots(
                    initial_positions,
                    operations
                )

                if not position_items:
                    continue

                fund_ids = [item["fund_id"] for item in position_items]
                nav_map = get_nav_on_date_map(
                    cursor,
                    fund_ids,
                    return_date
                )
                return_items = calculate_position_returns(
                    position_items,
                    nav_map
                )
                blogger_summary = calculate_total_returns(return_items)

                all_return_items.extend(return_items)
                blogger_summaries.append(
                    {
                        "blogger_id": blogger["id"],
                        "blogger_name": blogger["name"],
                        "total_cost_amount": _to_number(
                            blogger_summary["total_cost_amount"],
                            2
                        ),
                        "total_market_value": _to_number(
                            blogger_summary["total_market_value"],
                            2
                        ),
                        "profit_amount": _to_number(
                            blogger_summary["profit_amount"],
                            2
                        ),
                        "return_rate": _to_number(
                            blogger_summary["return_rate"],
                            6
                        ),
                        "funds": [
                            _serialize_return_item(item)
                            for item in return_items
                        ]
                    }
                )

            total_summary = calculate_total_returns(all_return_items)
    finally:
        conn.close()

    return success(
        data={
            "return_date": return_date.strftime("%Y-%m-%d"),
            "total_cost_amount": _to_number(
                total_summary["total_cost_amount"],
                2
            ),
            "total_market_value": _to_number(
                total_summary["total_market_value"],
                2
            ),
            "profit_amount": _to_number(
                total_summary["profit_amount"],
                2
            ),
            "return_rate": _to_number(
                total_summary["return_rate"],
                6
            ),
            "blogger_count": len(blogger_summaries),
            "items": blogger_summaries
        }
    )