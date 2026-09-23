import sys
import asyncio
from pathlib import Path

import httpx
import pytest
from sqlmodel import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


class SyncASGIClient:
    def __init__(self, application):
        self.application = application

    def request(self, method, url, **kwargs):
        async def send_request():
            transport = httpx.ASGITransport(app=self.application)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(send_request())

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    app.engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    app.create_db_and_tables()
    with app.Session(app.engine) as session:
        app.refresh_status_metrics(session)
    yield SyncASGIClient(app.app)


def test_health_and_documentation(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()
    assert set(spec["paths"]) == {"/health", "/tasks", "/tasks/{task_id}"}
    assert set(spec["components"]["schemas"]["TaskStatus"]["enum"]) == {"TODO", "IN_PROGRESS", "DONE", "CANCELLED"}


def test_task_lifecycle_and_filters(client):
    created = client.post("/tasks", json={"title": "Prepare report", "description": "Compile weekly numbers"})
    assert created.status_code == 201
    task = created.json()
    assert task["status"] == "TODO"
    task_id = task["id"]

    assert client.get(f"/tasks/{task_id}").json()["title"] == "Prepare report"
    assert client.put(f"/tasks/{task_id}", json={"assigned_to": "operations-team", "status": "IN_PROGRESS"}).status_code == 200
    assert client.get("/tasks?status=IN_PROGRESS&assigned_to=operations-team").json()[0]["id"] == task_id
    assert client.put(f"/tasks/{task_id}", json={"status": "DONE"}).json()["status"] == "DONE"
    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404


def test_validation_and_not_found(client):
    assert client.post("/tasks", json={"title": ""}).status_code == 422
    assert client.post("/tasks", json={"title": "x", "status": "DONE"}).status_code == 422
    assert client.get("/tasks?status=UNKNOWN").status_code == 422
    assert client.get("/tasks/999").status_code == 404


def test_metrics_are_prometheus_text(client):
    client.post("/tasks", json={"title": "Metric task"})
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "task_api_http_requests_total" in response.text
    assert "task_api_tasks_created_total" in response.text
    assert "task_api_tasks_by_status" in response.text
