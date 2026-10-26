from datetime import date, datetime


def parse_snapshot_date(raw_snapshot_date):
    if raw_snapshot_date in (None, ""):
        return date.today()

    try:
        return datetime.strptime(
            raw_snapshot_date,
            "%Y-%m-%d"
        ).date()
    except (TypeError, ValueError):
        return None


def get_initial_positions(cursor, blogger_id, snapshot_date):
    cursor.execute(
        """
        SELECT 
            ip.id,
            ip.blogger_id,
            ip.fund_id,
            ip.shares,
            ip.cost_amount,
            ip.record_date,
            f.name AS fund_name,
            f.fund_code
        FROM initial_positions AS ip
        JOIN funds AS f ON f.id = ip.fund_id
        WHERE ip.blogger_id = %s
          AND ip.record_date <= %s
        ORDER BY ip.fund_id, ip.record_date, ip.id
        """,
        (blogger_id, snapshot_date)
    )
    return cursor.fetchall()


def get_operations(cursor, blogger_id, snapshot_date):
    cursor.execute(
        """
        SELECT 
            o.id,
            o.blogger_id,
            o.fund_id,
            o.operation_type,
            o.operation_date,
            o.shares,
            o.amount,
            f.name AS fund_name,
            f.fund_code
        FROM operations AS o
        JOIN funds AS f ON f.id = o.fund_id
        WHERE o.blogger_id = %s
          AND o.operation_date <= %s
        ORDER BY o.fund_id, o.operation_date, o.id
        """,
        (blogger_id, snapshot_date)
    )
    return cursor.fetchall()


def get_nav_on_date_map(cursor, fund_ids, nav_date):
    fund_id_list = list(fund_ids)

    if not fund_id_list:
        return {}

    placeholders = ",".join(["%s"] * len(fund_id_list))

    cursor.execute(
        f"""
        SELECT 
            fund_id,
            nav_date,
            nav
        FROM nav_history
        WHERE fund_id IN ({placeholders})
          AND nav_date = %s
        """,
        (*fund_id_list, nav_date)
    )

    return {
        row["fund_id"]: row
        for row in cursor.fetchall()
    }