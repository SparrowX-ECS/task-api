# SparrowX Labs Task API

The Task API is the lightweight Operations Team service owned by Daniel Brooks. It manages internal tasks using Python 3.12+, FastAPI, SQLModel, and PostgreSQL.

## API contract

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/task/` | Create a task (`title`, optional `description`, optional `assigned_to`) |
| `GET` | `/api/task/` | List tasks; filter by `status` or `assigned_to` |
| `GET` | `/api/task/{id}` | Retrieve a task |
| `PUT` | `/api/task/{id}` | Update task fields, assign it, or change its status |
| `DELETE` | `/api/task/{id}` | Delete a task |

Statuses are `TODO`, `IN_PROGRESS`, `DONE`, and `CANCELLED`. New tasks start as `TODO`. Missing tasks return `404`; invalid request data returns `422`; successful creation returns `201` and deletion returns `204`.

## Local development

From this directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
pytest -q
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The application reads `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USERNAME`, and `DB_PASSWORD` from the environment.

- OpenAPI UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Health: `GET /health` returns `{"status":"ok"}`
- Metrics: <http://localhost:8000/metrics>

The sample Grafana dashboard is `monitoring/grafana-dashboard.json`; it expects the Prometheus job label `task-api`.

## Docker

```bash
docker build -t task-api .
docker run --rm --network sparrowx-local -p 8000:8000 \
  -e DB_HOST=local-customer-postgres-db \
  -e DB_PORT=5432 \
  -e DB_NAME=taskdb \
  -e DB_USERNAME=postgres \
  -e DB_PASSWORD=postgres \
  task-api
```
