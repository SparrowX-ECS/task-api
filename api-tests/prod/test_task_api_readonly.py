import os

import httpx


BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")


def client() -> httpx.Client:
    if not BASE_URL:
        raise RuntimeError("BASE_URL must point to the deployed task-api service")
    return httpx.Client(base_url=BASE_URL, timeout=15.0, follow_redirects=True)


def test_health_endpoint() -> None:
    with client() as api:
        response = api.get("/api/tasks/health")

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok"}


def test_list_tasks_is_readable() -> None:
    with client() as api:
        response = api.get("/api/tasks/")

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_openapi_contains_task_routes() -> None:
    with client() as api:
        response = api.get("/api/tasks/openapi.json")

    assert response.status_code == 200, response.text
    paths = response.json()["paths"]
    assert "/api/tasks/" in paths
    assert "/api/tasks/{task_id}" in paths
