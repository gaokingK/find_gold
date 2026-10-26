from datetime import date, timedelta
from decimal import Decimal

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
from app.utils.list_params import MAX_PAGE_SIZE


dashboard_bp = Blueprint("dashboards", __name__)


ZERO = Decimal("0")


def _to_decimal(value):
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def _to_number(value, places):
    if value is None:
        return None

    return round(float(value), places)


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


def _load_blogger_return_items(cursor, blogger, return_date):
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
        return []

    fund_ids = [item["fund_id"] for item in position_items]
    nav_map = get_nav_on_date_map(
        cursor,
        fund_ids,
        return_date
    )

    return calculate_position_returns(
        position_items,
        nav_map
    )


@dashboard_bp.get("/api/v1/dashboards/bloggers")
def get_blogger_overview_dashboard():
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
                "SELECT id, name FROM bloggers ORDER BY id"
            )
            bloggers = cursor.fetchall()

            all_return_items = []
            blogger_items = []

            for blogger in bloggers:
                return_items = _load_blogger_return_items(
                    cursor,
                    blogger,
                    return_date
                )

                if not return_items:
                    continue

                blogger_summary = calculate_total_returns(return_items)

                all_return_items.extend(return_items)
                blogger_items.append(
                    {
                        "blogger_id": blogger["id"],
                        "blogger_name": blogger["name"],
                        "fund_count": len(return_items),
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
                        )
                    }
                )

            total_summary = calculate_total_returns(all_return_items)
            position_count = len(all_return_items)
    finally:
        conn.close()

    return success(
        data={
            "return_date": return_date.strftime("%Y-%m-%d"),
            "blogger_count": len(blogger_items),
            "position_count": position_count,
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
            "items": blogger_items
        }
    )


@dashboard_bp.get("/api/v1/dashboards/funds")
def get_fund_distribution_dashboard():
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
                "SELECT id, name FROM bloggers ORDER BY id"
            )
            bloggers = cursor.fetchall()
            fund_groups = {}

            for blogger in bloggers:
                return_items = _load_blogger_return_items(
                    cursor, 
                    blogger,
                    return_date
                )

                for item in return_items:
                    fund_id = item["fund_id"]

                    if fund_id not in fund_groups:
                        fund_groups[fund_id] = {
                            "fund_id": fund_id,
                            "fund_name": item["fund_name"],
                            "fund_code": item["fund_code"],
                            "blogger_ids": set(),
                            "shares": ZERO,
                            "cost_amount": ZERO,
                            "nav": item["nav"],
                            "nav_date": item["nav_date"],
                            "market_value": ZERO,
                            "has_missing_nav": False,
                        }

                    group = fund_groups[fund_id]
                    group["blogger_ids"].add(blogger["id"])
                    group["shares"] += _to_decimal(item["shares"])
                    group["cost_amount"] += _to_decimal(item["cost_amount"])

                    if item["market_value"] is None:
                        group["has_missing_nav"] = True
                    else:
                        group["market_value"] += _to_decimal(
                            item["market_value"]
                        )

                        if group["nav"] is None:
                            group["nav"] = item["nav"]
                            group["nav_date"] = item["nav_date"]
    finally:
        conn.close()

    total_cost_amount = sum(
        (group["cost_amount"] for group in fund_groups.values()),
        ZERO
    )

    if any(group["has_missing_nav"] for group in fund_groups.values()):
        total_market_value = None
    else:
        total_market_value = sum(
            (group["market_value"] for group in fund_groups.values()),
            ZERO
        )

    fund_items = []

    for group in sorted(
        fund_groups.values(),
        key=lambda group: group["cost_amount"],
        reverse=True
    ):
        if total_cost_amount > ZERO:
            cost_ratio = group["cost_amount"] / total_cost_amount
        else: 
            cost_ratio = None

        if group["has_missing_nav"]:
            market_value = None
        else:
            market_value = group["market_value"]

        if (
            market_value is None
            or total_market_value is None
            or total_market_value <= ZERO 
        ):
            market_value_ratio = None
        else:
            market_value_ratio = market_value / total_market_value

        nav_date = group["nav_date"]

        fund_items.append(
            {
                "fund_id": group["fund_id"],
                "fund_name": group["fund_name"],
                "fund_code": group["fund_code"],
                "blogger_count": len(group["blogger_ids"]),
                "shares": _to_number(group["shares"], 4),
                "cost_amount": _to_number(group["cost_amount"], 2),
                "nav": _to_number(group["nav"], 4),
                "nav_date": (
                    nav_date.strftime("%Y-%m-%d")
                    if nav_date is not None
                    else None
                ),
                "market_value": _to_number(market_value, 2),
                "cost_ratio": _to_number(cost_ratio, 6),
                "market_value_ratio": _to_number(market_value_ratio, 6)
            }
        )

    return success(
        data={
            "return_date": return_date.strftime("%Y-%m-%d"),
            "fund_count": len(fund_items),
            "total_cost_amount": _to_number(total_cost_amount, 2),
            "total_market_value": _to_number(total_market_value, 2),
            "items": fund_items
        }
    )
        

def _serialize_operation_item(row):
    return {
        "operation_id": row["id"],
        "blogger_id": row["blogger_id"],
        "blogger_name": row["blogger_name"],
        "fund_id": row["fund_id"],
        "fund_name": row["fund_name"],
        "fund_code": row["fund_code"],
        "operation_type": row["operation_type"],
        "operation_date": row["operation_date"].strftime("%Y-%m-%d"),
        "shares": _to_number(row["shares"], 4),
        "amount": _to_number(row["amount"], 2)
    }


@dashboard_bp.get("/api/v1/dashboards/recent-operations")
def get_recent_operation_statistics():
    raw_end_date = request.args.get("end_date")
    end_date = parse_snapshot_date(raw_end_date)

    if end_date is None:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "end_date",
                    "message": "结束日期格式必须是 YYYY-MM-DD"
                }
            ],
            http_status=400
        )

    if end_date > date.today():
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "end_date",
                    "message": "结束日期不能晚于今天"
                }
            ], 
            http_status=400
        )

    raw_start_date = request.args.get("start_date")

    if raw_start_date in (None, ""):
        start_date = end_date - timedelta(days=6)
    else:
        start_date = parse_snapshot_date(raw_start_date)

        if start_date is None:
            return error(
                code="VALIDATION_ERROR",
                message="参数校验失败",
                details=[
                    {
                        "field": "start_date",
                        "message": "开始日期格式必须是 YYYY-MM-DD"
                    }
                ],
                http_status=400
            )

        if start_date > end_date:
            return error(
                code="VALIDATION_ERROR",
                message="参数校验失败",
                details=[
                    {
                        "field": "start_date",
                        "message": "开始日期不能晚于结束日期"
                    }
                ],
                http_status=400
            )

    limit = parse_positive_int(request.args.get("limit", 20))

    if limit is None or limit > MAX_PAGE_SIZE:
        return error(
            code="VALIDATION_ERROR",
            message="参数校验失败",
            details=[
                {
                    "field": "limit",
                    "message": f"limit 必须是1 到 {MAX_PAGE_SIZE} 之间的正整数"
                }
            ], 
            http_status=400
        )

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    operation_type,
                    COUNT(*) AS operation_count,
                    COALESCE(SUM(shares), 0) AS total_shares,
                    COALESCE(SUM(amount), 0) AS total_amount
                FROM operations
                WHERE operation_date >= %s
                    AND operation_date <= %s
                GROUP BY operation_type
                """,
                (start_date, end_date)
            )
            summary_rows = cursor.fetchall()

            summary = {
                "operation_count": 0,
                "buy_count": 0,
                "buy_shares": _to_number(ZERO, 4),
                "buy_amount": _to_number(ZERO, 2),
                "sell_count": 0,
                "sell_shares": _to_number(ZERO, 4),
                "sell_amount": _to_number(ZERO, 2),
                "dividend_cash_count": 0,
                "dividend_cash_amount": _to_number(ZERO, 2)
            }

            for row in summary_rows:
                operation_type = row["operation_type"]
                summary["operation_count"] += row["operation_count"]

                if operation_type == "buy":
                    summary["buy_count"] = row["operation_count"]
                    summary["buy_shares"] = _to_number(row["total_shares"], 4)
                    summary["buy_amount"] = _to_number(row["total_amount"], 2)

                if operation_type == "sell": 
                    summary["sell_count"] = row["operation_count"]
                    summary["sell_shares"] = _to_number(row["total_shares"], 4)
                    summary["sell_amount"] = _to_number(row["total_amount"], 2)

                if operation_type == "dividend_cash":
                    summary["dividend_cash_count"] = row["operation_count"]
                    summary["dividend_cash_amount"] = _to_number(row["total_amount"], 2)

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
                    o.amount
                FROM operations AS o
                JOIN bloggers AS b ON b.id = o.blogger_id
                JOIN funds AS f ON f.id = o.fund_id
                WHERE o.operation_date >= %s
                    AND o.operation_date <= %s
                ORDER BY o.operation_date DESC, o.id DESC
                LIMIT %s
                """,
                (start_date, end_date, limit)
            )
            operation_rows = cursor.fetchall()
            operation_items = [
                _serialize_operation_item(row)
                for row in operation_rows
            ]
    finally:
        conn.close()

    return success(
        data={
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "limit": limit,
            "summary": summary,
            "items": operation_items
        }
    )