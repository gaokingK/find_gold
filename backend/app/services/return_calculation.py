from decimal import Decimal


ZERO = Decimal("0")


def _to_decimal(value):
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def calculate_return_metrics(cost_amount, market_value):
    cost = _to_decimal(cost_amount)

    if market_value is None:
        return {
            "profit_amount": None,
            "return_rate": None
        }

    market_value = _to_decimal(market_value)
    profit_amount = market_value - cost

    if cost <= ZERO:
        return_rate = None
    else:
        return_rate = profit_amount / cost

    return {
        "profit_amount": profit_amount,
        "return_rate": return_rate
    }


def calculate_position_returns(position_items, nav_map):
    result = []

    for item in position_items:
        fund_id = item["fund_id"]
        nav_record = nav_map.get(fund_id)

        if nav_record is None:
            nav = None
            nav_date = None
            market_value = None
        else:
            nav = _to_decimal(nav_record["nav"])
            nav_date = nav_record["nav_date"]
            market_value = _to_decimal(item["shares"]) * nav

        metrics = calculate_return_metrics(
            item["cost_amount"],
            market_value
        )

        result.append(
            {
                **item,
                "nav": nav,
                "nav_date": nav_date,
                "market_value": market_value,
                "profit_amount": metrics["profit_amount"],
                "return_rate": metrics["return_rate"]
            }
        )

    return result


def calculate_total_returns(return_items):
    total_cost_amount = ZERO

    for item in return_items:
        total_cost_amount += _to_decimal(item["cost_amount"])

    if any(item["market_value"] is None for item in return_items):
        total_market_value = None
    else:
        total_market_value = ZERO

        for item in return_items:
            total_market_value += _to_decimal(item["market_value"])

    metrics = calculate_return_metrics(
        total_cost_amount,
        total_market_value
    )

    return {
        "total_cost_amount": total_cost_amount,
        "total_market_value": total_market_value,
        "profit_amount": metrics["profit_amount"],
        "return_rate": metrics["return_rate"]
    }

