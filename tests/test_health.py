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
