import os
import uuid

import httpx


BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")


def client() -> httpx.Client:
    if not BASE_URL:
        raise RuntimeError("BASE_URL must point to the deployed task-api service")
    return httpx.Client(base_url=BASE_URL, timeout=15.0, follow_redirects=True)


def test_task_lifecycle() -> None:
    title = f"Deployment validation task {uuid.uuid4().hex}"
    payload = {
        "title": title,
        "description": "Exercise the deployed task lifecycle.",
        "assigned_to": "deployment-validation",
    }

    with client() as api:
        created = api.post("/api/tasks/", json=payload)
        assert created.status_code == 201, created.text
        task = created.json()
        task_id = task["id"]
        assert task["title"] == title
        assert task["status"] == "TODO"

        try:
            fetched = api.get(f"/api/tasks/{task_id}")
            assert fetched.status_code == 200, fetched.text
            assert fetched.json()["id"] == task_id

            filtered = api.get(
                "/api/tasks/",
                params={"status": "TODO", "assigned_to": "deployment-validation"},
            )
            assert filtered.status_code == 200, filtered.text
            assert any(item["id"] == task_id for item in filtered.json())

            updated = api.put(
                f"/api/tasks/{task_id}",
                json={"assigned_to": "operations-team", "status": "IN_PROGRESS"},
            )
            assert updated.status_code == 200, updated.text
            assert updated.json()["assigned_to"] == "operations-team"
            assert updated.json()["status"] == "IN_PROGRESS"

            completed = api.put(
                f"/api/tasks/{task_id}",
                json={"status": "DONE"},
            )
            assert completed.status_code == 200, completed.text
            assert completed.json()["status"] == "DONE"

            deleted = api.delete(f"/api/tasks/{task_id}")
            assert deleted.status_code == 204, deleted.text
        finally:
            # Keep the deployed environment clean if a lifecycle assertion fails.
            api.delete(f"/api/tasks/{task_id}")

        missing = api.get(f"/api/tasks/{task_id}")
        assert missing.status_code == 404, missing.text


def test_task_api_rejects_invalid_requests() -> None:
    with client() as api:
        empty_title = api.post("/api/tasks/", json={"title": ""})
        assert empty_title.status_code == 422, empty_title.text

        invalid_status = api.put(
            "/api/tasks/999999",
            json={"status": "UNKNOWN"},
        )
        assert invalid_status.status_code == 422, invalid_status.text

        unknown_task = api.get("/api/tasks/999999")
        assert unknown_task.status_code == 404, unknown_task.text
