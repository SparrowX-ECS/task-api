# SparrowX Labs Task API

The Task API is the lightweight Operations Team service owned by Daniel Brooks. It manages internal tasks using Python 3.12+, FastAPI, SQLModel, and SQLite.

## API contract

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/tasks` | Create a task (`title`, optional `description`, optional `assigned_to`) |
| `GET` | `/tasks` | List tasks; filter by `status` or `assigned_to` |
| `GET` | `/tasks/{id}` | Retrieve a task |
| `PUT` | `/tasks/{id}` | Update task fields, assign it, or change its status |
| `DELETE` | `/tasks/{id}` | Delete a task |

Statuses are `TODO`, `IN_PROGRESS`, `DONE`, and `CANCELLED`. New tasks start as `TODO`. Missing tasks return `404`; invalid request data returns `422`; successful creation returns `201` and deletion returns `204`.

## Local development

From this directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
pytest -q
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The default database is `./task.db`. Set `TASK_API_DATABASE_URL` to another SQLite URL, such as `sqlite:///./local.db`.

- OpenAPI UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Health: `GET /health` returns `{"status":"ok"}`
- Metrics: <http://localhost:8000/metrics>

The sample Grafana dashboard is `monitoring/grafana-dashboard.json`; it expects the Prometheus job label `task-api`.

## Docker

```bash
docker build -t task-api .
docker run --rm -p 8000:8000 -v task-api-data:/data task-api
```

The container runs as a non-root user and stores SQLite data in `/data`.
