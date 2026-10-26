from factories import create_blogger

def test_create_blogger_success(client):
    data = create_blogger(client, name="新增成功博主")

    assert data["name"] == "新增成功博主"
    assert data["sector"] == "成长股"
    assert data["observe_start_date"] == "2020-01-01"
    assert "blogger_id" in data 

def  test_create_blogger_with_duplicate_name(client):
    create_blogger(client, name="重复名称博主")

    response = client.post(
        "/api/v1/bloggers",
        json={
            "name": "重复名称博主",
            "sector": "价值股",
            "observe_start_date": "2020-01-01"
        }
    )
    body = response.get_json()

    assert response.status_code == 409
    assert body["code"] == "BLOGGER_NAME_DUPLICATED"

def test_list_bloggers_returns_created_blogger(client):
    create_blogger(client, name="列表测试博主")

    response = client.get("/api/v1/bloggers")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["total"] >= 1
    assert any(
        item["name"] == "列表测试博主"
        for item in body["data"]["items"]
    )

def test_get_blogger_detail(client):
    blogger = create_blogger(client, name="详情测试博主")

    response = client.get(f"/api/v1/bloggers/{blogger['blogger_id']}")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["name"] == "详情测试博主"

def test_update_blogger_success(client):
    blogger = create_blogger(client, name="编辑前博主")

    response = client.put(
        f"/api/v1/bloggers/{blogger['blogger_id']}",
        json={
            "name": "编辑后博主",
            "sector": "价值股",
            "observe_start_date": "2020-01-01"
        }
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["name"] == "编辑后博主"
    assert body["data"]["sector"] == "价值股"

def test_update_blogger_with_duplicate_name(client):
    blogger_a = create_blogger(client, name="博主A")
    create_blogger(client, name="博主B")

    response = client.put(
        f"/api/v1/bloggers/{blogger_a['blogger_id']}",
        json={
            "name": "博主B",
            "sector": "价值股",
            "observe_start_date": "2020-01-01"
        }
    )
    body = response.get_json()

    assert response.status_code == 409
    assert body["code"] == "BLOGGER_NAME_DUPLICATED"

def test_delete_blogger_success(client):
    blogger = create_blogger(client, name="删除测试博主")

    response = client.delete(f"/api/v1/bloggers/{blogger['blogger_id']}")
    body = response.get_json()

    assert response.status_code == 200
    assert body["code"] == 0

    detail_response = client.get(f"/api/v1/bloggers/{blogger['blogger_id']}")
    detail_body = detail_response.get_json()

    assert detail_response.status_code == 404
    assert detail_body["code"] == "BLOGGER_NOT_FOUND"

def test_get_blogger_with_invalid_id(client):
    for blogger_id in ["0", "abc"]:
        response = client.get(f"/api/v1/bloggers/{blogger_id}")
        body = response.get_json()

        assert response.status_code == 400
        assert body["code"] == "VALIDATION_ERROR"

def test_create_blogger_with_missing_fields(client):
    response = client.post(
        "/api/v1/bloggers",
        json={}
    )
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"
    assert len(body["details"]) > 0

def test_list_bloggers_rejects_unknown_sort_field(client):
    response = client.get("/api/v1/bloggers?sort_by=password")
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"

def test_list_bloggers_rejects_invalid_paging(client):
    for query in ["page=0", "page_size=0", "page_size=101"]:
        response = client.get("/api/v1/bloggers", query_string=query)
        body = response.get_json()

        assert response.status_code == 400
        assert body["code"] == "VALIDATION_ERROR"

def test_list_bloggers_status_filter(client):
    response = client.get("/api/v1/bloggers?status_code=observing")

    assert response.status_code == 200

    response = client.get("/api/v1/bloggers?status=unknown_status")
    body = response.get_json()

    assert response.status_code == 400
    assert body["code"] == "VALIDATION_ERROR"