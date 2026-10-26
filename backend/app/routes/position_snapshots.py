from datetime import date

from flask import Blueprint, request

from app.db import get_connection
from app.services.position_snapshot import calculate_position_snapshots
from app.utils.responses import success, error
from app.utils.snapshot_data import (
    get_initial_positions,
    get_operations,
    parse_snapshot_date
)


position_snapshots_bp = Blueprint("position_snapshots", __name__)


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


def _serialize_position_snapshot_item(item):
    initial_record_date = item["initial_record_date"]

    return {
        "fund_id": item["fund_id"],
        "fund_name": item["fund_name"],
        "fund_code": item["fund_code"],
        "initial_record_date": (
            initial_record_date.strftime("%Y-%m-%d")
            if initial_record_date is not None
            else None
        ),
        "initial_shares": _to_number(item["initial_shares"], 4),
        "initial_cost_amount": _to_number(item["initial_cost_amount"], 2),
        "buy_shares": _to_number(item["buy_shares"], 4),
        "buy_amount": _to_number(item["buy_amount"], 2),
        "sell_amount": _to_number(item["sell_amount"], 2),
        "sell_shares": _to_number(item["sell_shares"], 4),
        "dividend_cash_amount": _to_number(item["dividend_cash_amount"], 2),
        "shares": _to_number(item["shares"], 4),
        "cost_amount": _to_number(item["cost_amount"], 2),
    }


@position_snapshots_bp.get("/api/v1/bloggers/<blogger_id>/position-snapshots")
def get_position_snapshots(blogger_id):
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

    snapshot_date = parse_snapshot_date(request.args.get("snapshot_date"))

    if snapshot_date is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "snapshot_date",
                    "message": "快照日期格式必须是 YYYY-MM-DD"
                }
            ],
            http_status=400
        )

    if snapshot_date > date.today():
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "snapshot_date",
                    "message": "快照日期不能晚于今天"
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
                snapshot_date
            )
            operations = get_operations(
                cursor,
                parsed_blogger_id,
                snapshot_date
            )
            items = calculate_position_snapshots(
                initial_positions,
                operations
            )
            serialized_items = [
                _serialize_position_snapshot_item(item)
                for item in items
            ]
    finally:
        conn.close()

    return success(
        data={
            "blogger_id": parsed_blogger_id,
            "blogger_name": blogger["name"],
            "snapshot_date": snapshot_date.strftime("%Y-%m-%d"),
            "items": serialized_items
        }
    )