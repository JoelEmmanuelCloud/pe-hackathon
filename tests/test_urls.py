import json


def test_shorten_creates_url(client, sample_user):
    response = client.post("/shorten", json={
        "original_url": "https://google.com",
        "title": "Google",
        "user_id": sample_user.id,
    })
    assert response.status_code == 201
    data = response.get_json()
    assert "short_code" in data
    assert data["original_url"] == "https://google.com"
    assert data["is_active"] is True


def test_shorten_missing_url_returns_400(client):
    response = client.post("/shorten", json={"title": "No URL"})
    assert response.status_code == 400


def test_shorten_invalid_url_returns_400(client):
    response = client.post("/shorten", json={"original_url": "not-a-url"})
    assert response.status_code == 400


def test_shorten_invalid_user_returns_404(client):
    response = client.post("/shorten", json={
        "original_url": "https://example.com",
        "user_id": 999999,
    })
    assert response.status_code == 404


def test_shorten_no_body_returns_400(client):
    response = client.post("/shorten", data="not json", content_type="text/plain")
    assert response.status_code == 400


def test_redirect_returns_302(client, sample_url):
    response = client.get(f"/{sample_url.short_code}")
    assert response.status_code == 302


def test_redirect_goes_to_correct_url(client, sample_url):
    response = client.get(f"/{sample_url.short_code}")
    assert response.location == sample_url.original_url


def test_redirect_unknown_code_returns_404(client):
    response = client.get("/zzzzzz")
    assert response.status_code == 404


def test_redirect_inactive_url_returns_410(client, sample_url):
    sample_url.is_active = False
    sample_url.save()
    response = client.get(f"/{sample_url.short_code}")
    assert response.status_code == 410


def test_list_urls_returns_200(client, sample_url):
    response = client.get("/urls")
    assert response.status_code == 200
    data = response.get_json()
    assert "urls" in data
    assert "total" in data


def test_list_urls_invalid_page_returns_400(client):
    response = client.get("/urls?page=-1")
    assert response.status_code == 400


def test_get_url_by_id(client, sample_url):
    response = client.get(f"/urls/{sample_url.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["short_code"] == sample_url.short_code


def test_get_url_not_found(client):
    response = client.get("/urls/999999")
    assert response.status_code == 404


def test_stats_returns_click_count(client, sample_url):
    client.get(f"/{sample_url.short_code}")
    response = client.get(f"/stats/{sample_url.short_code}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["click_count"] >= 1


def test_stats_unknown_code_returns_404(client):
    response = client.get("/stats/zzzzzz")
    assert response.status_code == 404


def test_deactivate_url(client, sample_url):
    response = client.delete(f"/urls/{sample_url.id}")
    assert response.status_code == 200
    get_resp = client.get(f"/{sample_url.short_code}")
    assert get_resp.status_code == 410


def test_deactivate_nonexistent_url(client):
    response = client.delete("/urls/999999")
    assert response.status_code == 404


def test_list_users(client, sample_user):
    response = client.get("/users")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert any(u["username"] == "testuser" for u in data)


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"http_requests_total" in response.data or b"process_cpu_percent" in response.data


def test_metrics_records_requests(client, sample_url):
    client.get(f"/{sample_url.short_code}")
    response = client.get("/metrics")
    body = response.data.decode()
    assert 'http_requests_total{endpoint="/<short_code>",method="GET",status="302"}' in body
    assert 'http_request_duration_seconds_count{endpoint="/<short_code>",method="GET"}' in body
    assert 'cache_lookups_total{cache="redirect",result="miss"}' in body


def test_redirect_cache_hit_records_click(client, sample_url):
    import json
    from unittest.mock import patch

    cached = json.dumps({"id": sample_url.id, "url": sample_url.original_url})
    with patch("app.routes.urls.cache_get", return_value=cached):
        response = client.get(f"/{sample_url.short_code}")
    assert response.status_code == 302
    assert response.headers["Location"] == sample_url.original_url
    stats = client.get(f"/stats/{sample_url.short_code}").get_json()
    assert stats["click_count"] == 1


def test_update_rejects_non_http_url(client, sample_url):
    response = client.put(f"/urls/{sample_url.id}", json={"original_url": "javascript:alert(1)"})
    assert response.status_code == 400
    assert client.get(f"/urls/{sample_url.id}").get_json()["original_url"] == "https://example.com"


def test_update_accepts_https_url(client, sample_url):
    response = client.put(f"/urls/{sample_url.id}", json={"original_url": " https://example.com/new "})
    assert response.status_code == 200
    assert response.get_json()["original_url"] == "https://example.com/new"


def test_rename_user_to_taken_username_returns_409(client, sample_user):
    from app.models.user import User
    other = User.create(username="other", email="other@example.com")
    response = client.put(f"/users/{other.id}", json={"username": "testuser"})
    assert response.status_code == 409
    assert User.get_by_id(other.id).username == "other"


def test_rename_user_to_own_username_is_allowed(client, sample_user):
    response = client.put(f"/users/{sample_user.id}", json={"username": "testuser", "email": "test@example.com"})
    assert response.status_code == 200


def test_update_user_race_on_unique_returns_409(client, sample_user, monkeypatch):
    from peewee import IntegrityError
    from app.models.user import User

    def fail(*args, **kwargs):
        raise IntegrityError("duplicate key")

    monkeypatch.setattr(User, "save", fail)
    response = client.put(f"/users/{sample_user.id}", json={"username": "fresh"})
    assert response.status_code == 409
