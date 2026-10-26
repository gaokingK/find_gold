from collections import defaultdict
from decimal import Decimal


ZERO = Decimal("0")


def _to_decimal(value):
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def _group_initial_positions(initial_positions):
    grouped = defaultdict(list)

    for row in initial_positions:
        grouped[row["fund_id"]].append(row)

    return grouped


def _group_operations(operations):
    grouped = defaultdict(list)

    for row in operations:
        grouped[row["fund_id"]].append(row)

    return grouped


def _pick_first_initial_positions(rows):
    if not rows:
        return None

    return min(rows, key=lambda row: (row["record_date"], row["id"]))


def calculate_position_snapshots(initial_positions, operations):
    grouped_initial_positions = _group_initial_positions(initial_positions)
    grouped_operations = _group_operations(operations)

    fund_ids = set(grouped_initial_positions) | set(grouped_operations)
    result = []

    for fund_id in sorted(fund_ids):
        initial_position = _pick_first_initial_positions(
            grouped_initial_positions.get(fund_id, [])
        )
        fund_operations = grouped_operations.get(fund_id, [])
        fund_operations.sort(key=lambda row: (row["operation_date"], row["id"]))

        if initial_position is None:
            fund_name = fund_operations[0]["fund_name"]
            fund_code = fund_operations[0]["fund_code"]
            initial_record_date = None
            initial_shares = ZERO
            initial_cost_amount = ZERO
        else:
            fund_name = initial_position["fund_name"]
            fund_code = initial_position["fund_code"]
            initial_record_date = initial_position["record_date"]
            initial_shares = _to_decimal(initial_position["shares"])
            initial_cost_amount = _to_decimal(initial_position["cost_amount"])

        shares = initial_shares
        cost_amount = initial_cost_amount
        buy_shares = ZERO
        buy_amount = ZERO
        sell_shares = ZERO
        sell_amount = ZERO
        dividend_cash_amount = ZERO

        for row in fund_operations:
            operation_type = row["operation_type"]
            row_shares = _to_decimal(row["shares"])
            row_amount = _to_decimal(row["amount"])

            if operation_type == "buy":
                shares += row_shares
                cost_amount += row_amount
                buy_shares += row_shares
                buy_amount += row_amount

            elif operation_type == "sell":
                shares_before_sell = shares

                if shares_before_sell > ZERO:
                    average_cost = cost_amount / shares_before_sell
                    cost_amount -= average_cost * row_shares
                else:
                    pass

                shares -= row_shares
                sell_shares += row_shares
                sell_amount += row_amount

            elif operation_type == "dividend_cash":
                dividend_cash_amount += row_amount

        result.append(
            {
                "fund_id": fund_id,
                "fund_name": fund_name,
                "fund_code": fund_code,
                "initial_record_date": initial_record_date,
                "initial_shares": initial_shares,
                "initial_cost_amount": initial_cost_amount,
                "buy_shares": buy_shares,
                "buy_amount": buy_amount,
                "sell_shares": sell_shares,
                "sell_amount": sell_amount,
                "dividend_cash_amount": dividend_cash_amount,
                "shares": shares,
                "cost_amount": cost_amount
            }
        )
    return result