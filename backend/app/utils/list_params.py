from flask import request


MAX_PAGE_SIZE = 100


def parse_list_query_params(
        default_sort_by=None,
        allowed_sort_fields=None,
        default_order="desc"
):
    details = []
    params = {}

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
    except (TypeError, ValueError):
        details.append(
            {
                "field": "page",
                "message": "page和page_size必须是整数"
            }
        )
        page = 0
        page_size = 0

    if page <= 0:
        details.append(
            {
                "field": "page",
                "message": "page必须大于0"
            }
        )

    if page_size <= 0 or page_size > MAX_PAGE_SIZE:
        details.append(
            {
                "field": "page_size",
                "message": f"page_size必须在1到{MAX_PAGE_SIZE}之间"
            }
        )

    params["page"] = page
    params["page_size"] = page_size
    params["offset"] = (page - 1) * page_size if page > 0 else 0

    if allowed_sort_fields is None:
        return params, details

    sort_by = request.args.get("sort_by", default_sort_by)
    order = request.args.get("order", default_order)

    if sort_by in allowed_sort_fields:
        sort_column = allowed_sort_fields[sort_by]
    else:
        sort_column = None
        allowed_text = "、 ".join(allowed_sort_fields.keys())
        details.append(
            {
                "field": "sort_by",
                "message": f"sort_by只允许 {allowed_text}"
            }
        )

    if order not in ("asc", "desc"):
        details.append(
            {
                "field": "order",
                "message": "order只允许asc或desc"
            }
        )

    params["sort_by"] = sort_by
    params["sort_column"] = sort_column
    params["order"] = order

    return params, details

