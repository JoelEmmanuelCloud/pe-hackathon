def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_json(client):
    response = client.get("/health")
    data = response.get_json()
    assert "status" in data
    assert "db" in data


def test_health_status_ok(client):
    response = client.get("/health")
    data = response.get_json()
    assert data["status"] == "ok"


def test_redis_failure_disables_cache_until_retry(monkeypatch):
    import redis
    from unittest.mock import MagicMock
    from app import cache

    broken = MagicMock()
    broken.get.side_effect = redis.ConnectionError("down")
    monkeypatch.setattr(cache, "_client", broken)
    monkeypatch.setattr(cache, "_down_until", 0.0)

    assert cache.cache_get("k") is None
    assert cache._client is None
    assert cache.get_cache() is None
    assert broken.get.call_count == 1

    monkeypatch.setattr(cache, "_down_until", 0.0)
    healthy = MagicMock()
    monkeypatch.setattr(cache.redis, "Redis", lambda **kwargs: healthy)
    assert cache.get_cache() is healthy


def test_health_reports_cache_unavailable(client, monkeypatch):
    monkeypatch.setattr("app.routes.health.cache_ping", lambda: False)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["cache"] == "unavailable"


def test_health_returns_503_when_db_down(client, monkeypatch):
    from peewee import OperationalError
    from app.database import database_proxy

    def fail(*args, **kwargs):
        raise OperationalError("connection refused")

    with monkeypatch.context() as m:
        m.setattr(database_proxy.obj, "execute_sql", fail)
        response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json()["db"] == "error"


def test_db_outage_returns_503_json(client, monkeypatch):
    from peewee import OperationalError
    from app.models.url import Url

    def fail(*args, **kwargs):
        raise OperationalError("connection refused")

    monkeypatch.setattr(Url, "get_by_id", fail)
    response = client.get("/urls/1")
    assert response.status_code == 503
    assert response.get_json() == {"error": "database unavailable"}
