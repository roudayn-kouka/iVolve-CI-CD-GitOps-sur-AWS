import pytest

from app import app


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_index_ok(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"DevOps Graduation Project" in response.data


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_version_default(client, monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    assert client.get("/version").get_json() == {"version": "dev"}


def test_version_from_env(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "42")
    assert client.get("/version").get_json() == {"version": "42"}


def test_unknown_route_404(client):
    assert client.get("/nope").status_code == 404
