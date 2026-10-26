from io import BytesIO

from app.utils.nav_csv import parse_nav_history_csv


def test_parse_nav_history_csv_successs():
    content = b"fund_code,nav_date,nav\n000001,2026-09-30,1.2345\n"

    rows, errors = parse_nav_history_csv(BytesIO(content))

    assert errors == []
    assert len(rows) == 1
    assert rows[0]["fund_code"] == "000001"
    assert rows[0]["nav_date"].isoformat() == "2026-09-30"
    assert str(rows[0]["nav"]) == "1.2345"


def test_parse_nav_history_csv_supports_utf8_bom():
    content = b"\xef\xbb\xbffund_code,nav_date,nav\n000001,2026-09-30,1.2345\n"

    rows, errors = parse_nav_history_csv(BytesIO(content))

    assert errors == []
    assert rows[0]["fund_code"] == "000001"


def test_parse_nav_history_csv_reports_row_errors():
    content = (
        b"fund_code,nav_date,nav\n"
        b"000001,2026/09/30,1.2345\n"
        b",2026-09-30,1.2345\n"
        b"000002,2026-09-39,0\n"
    )

    rows, errors = parse_nav_history_csv(BytesIO(content))

    assert rows is None
    assert len(errors) >= 3


def test_parse_nav_history_csv_rejects_duplicate_key():
    content = (
        b"fund_code,nav_date,nav\n"
        b"000001,2026-09-30,1.2345\n"
        b"000001,2026-09-30,1.2345\n"
    )

    rows, errors = parse_nav_history_csv(BytesIO(content))

    assert rows is None
    assert any("重复" in error["message"] for error in errors)


def create_csv_file(content: str):
    return {
        "file": (
            BytesIO(content.encode("utf-8")),
            "nav_history.csv"
        )
    }


def test_import_nav_history_csv_success(client, create_fund):
    fund = create_fund(
        name="净值导入基金",
        fund_code="NAV000001"
    )

    csv_content = (
        "fund_code,nav_date,nav\n"
        f"{fund['fund_code']},2026-09-29,1.2000\n"
        f"{fund['fund_code']},2026-09-30,1.2345\n"
    )

    response = client.post(
        "/api/v1/nav-history/import",
        data=create_csv_file(csv_content),
        content_type="multipart/form-data"
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["total_rows"] == 2
    assert body["data"]["processed_rows"] == 2


def test_import_nav_history_csv_rejects_invalid_row(client, create_fund):
    fund = create_fund(
        name="净值导入失败基金",
        fund_code="NAV000002"
    )

    csv_content = (
        "fund_code,nav_date,nav\n"
        f"{fund['fund_code']},2026-09-29,1.2000\n"
        f"{fund['fund_code']},2026-09-30,0\n"
    )

    response = client.post(
        "/api/v1/nav-history/import",
        data=create_csv_file(csv_content),
        content_type="multipart/form-data"
    )
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"


def test_import_nav_history_csv_rejects_unknown_fund_code(client):
    csv_content = (
        "fund_code,nav_date,nav\n"
        "NOT_EXIST,2026-09-30,1.2345\n"
    )

    response = client.post(
        "/api/v1/nav-history/import",
        data=create_csv_file(csv_content),
        content_type="multipart/form_data"
    )
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"
