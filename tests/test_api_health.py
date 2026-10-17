from fastapi.testclient import TestClient

from case3.api import app

client = TestClient(app)


def test_health_endpoint():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert "docker_ok" in data
    assert "chart_types" in data
    assert "bar" in data["chart_types"]


def test_chart_types_endpoint():
    r = client.get("/api/chart-types")
    assert r.status_code == 200
    assert "bar" in r.json()["types"]
