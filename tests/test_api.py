import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_and_documentation(client: AsyncClient) -> None:
    assert (await client.get("/health")).json() == {"status": "ok"}
    assert (await client.get("/api/task/health")).json() == {"status": "ok"}
    assert (await client.get("/docs")).status_code == 200
    spec = (await client.get("/openapi.json")).json()
    assert set(spec["paths"]) == {"/health", "/api/task/health", "/api/task/", "/api/task/{task_id}"}
    assert set(spec["components"]["schemas"]["TaskStatus"]["enum"]) == {"TODO", "IN_PROGRESS", "DONE", "CANCELLED"}


@pytest.mark.anyio
async def test_task_lifecycle_and_filters(client: AsyncClient) -> None:
    created = await client.post("/api/task/", json={"title": "Prepare report", "description": "Compile weekly numbers"})
    assert created.status_code == 201
    task = created.json()
    assert task["status"] == "TODO"
    task_id = task["id"]

    assert (await client.get(f"/api/task/{task_id}")).json()["title"] == "Prepare report"
    assert (await client.put(f"/api/task/{task_id}", json={"assigned_to": "operations-team", "status": "IN_PROGRESS"})).status_code == 200
    assert (await client.get("/api/task/?status=IN_PROGRESS&assigned_to=operations-team")).json()[0]["id"] == task_id
    assert (await client.put(f"/api/task/{task_id}", json={"status": "DONE"})).json()["status"] == "DONE"
    assert (await client.delete(f"/api/task/{task_id}")).status_code == 204
    assert (await client.get(f"/api/task/{task_id}")).status_code == 404


@pytest.mark.anyio
async def test_validation_and_not_found(client: AsyncClient) -> None:
    assert (await client.post("/api/task/", json={"title": ""})).status_code == 422
    assert (await client.post("/api/task/", json={"title": "x", "status": "DONE"})).status_code == 422
    assert (await client.get("/api/task/?status=UNKNOWN")).status_code == 422
    assert (await client.get("/api/task/999999")).status_code == 404


@pytest.mark.anyio
async def test_metrics_are_prometheus_text(client: AsyncClient) -> None:
    await client.post("/api/task/", json={"title": "Metric task"})
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "task_api_http_requests_total" in response.text
    assert "task_api_tasks_created_total" in response.text
    assert "task_api_tasks_by_status" in response.text
