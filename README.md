# Task API

Operational task management service for the fictional SparrowX SaaS platform. This demonstration workload shows how a PostgreSQL-backed service can be onboarded to ECS/Fargate and deployed separately to `dev` and `prod`.

## Service responsibilities

- Create, list, filter, update, and delete operational tasks.
- Track task status and assignment.
- Persist data in the dedicated private RDS database `taskdb`.
- Expose health and Prometheus-compatible metrics endpoints.

## API documentation

FastAPI documentation is available at `/docs` (Swagger UI), `/redoc` (ReDoc), and `/openapi.json` (OpenAPI schema). The main API prefix is `/api/tasks`:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/tasks/` | Create a task |
| `GET` | `/api/tasks/` | List/filter tasks |
| `GET` | `/api/tasks/{task_id}` | Retrieve a task |
| `PUT` | `/api/tasks/{task_id}` | Update a task |
| `DELETE` | `/api/tasks/{task_id}` | Delete a task |
| `GET` | `/health` | Container/target-group health check |
| `GET` | `/api/tasks/health` | API smoke-test health check |
| `GET` | `/metrics` | Prometheus metrics |

## Runtime environment variables

| Variable | Required | Description |
| --- | --- | --- |
| `DB_HOST` | Yes | Private RDS PostgreSQL endpoint for `taskdb`. |
| `DB_PORT` | No | PostgreSQL port; defaults to `5432`. |
| `DB_NAME` | Yes | Database name, normally `taskdb`. |
| `DB_USERNAME` | Yes | Database username injected from the service secret. |
| `DB_PASSWORD` | Yes | Database password injected from the service secret. |
| `CORS_ALLOW_ORIGINS` | No | Comma-separated browser origins; defaults to local development origins. |

## Local development

```bash
python -m pip install -r requirements-dev.txt
pytest
uvicorn src.main:app --reload --port 8000
```

Open <http://localhost:8000/docs> after configuring the database variables.

## CI/CD cycle

Pull requests detect relevant changes, run Python tests with PostgreSQL, build an immutable image tagged with the commit SHA, scan it with Trivy, and publish metadata. A merge to `main` resolves the image, deploys it to `dev`, runs the environment smoke test, and publishes the successful tag/digest as the production candidate.

The manually confirmed production workflow resolves the candidate, verifies and copies the image by digest from `dev` ECR to `prod` ECR, deploys it, smoke-tests it, and records production metadata. The same artifact is used in both environments under **Build Once, Promote Many**.

## Environments and deployment tracking

`dev` deploys automatically from `main`; `prod` is promoted manually after validation. Each environment has separate ECS resources, ECR namespace, parameter file, URL, SSM metadata path, and GitHub deployment history. See [`ecs-parameters-dev.yaml`](ecs-parameters-dev.yaml) and [`ecs-parameters-prod.yaml`](ecs-parameters-prod.yaml).

## Rollback options

### Git revert

Revert the problematic commit and merge the revert. The standard pipeline will validate and deploy the corrective commit.

### Quicker manual image rollback

1. Open **Deployments** in this repository and select the `prod` environment.
2. Open the desired previous successful deployment and copy its image tag.
3. Go to **Actions → Manual Rollback Production To Selected Image Tag → Run workflow**.
4. Enter `ROLLBACK`, paste the image tag, and run it.

The workflow redeploys the selected immutable image, smoke-tests production, and publishes rollback metadata. ECS also has deployment circuit-breaker rollback enabled.

## Repository variables

| Variable | Description |
| --- | --- |
| `AWS_ACCOUNT_ID` | AWS account containing the ECS platform and ECR repositories. |
| `AWS_REGION` | AWS region used by GitHub Actions. |
| `AWS_ROLE_NAME` | IAM role assumed through GitHub OIDC. |
| `DEV_BASE_URL` | Development smoke-test origin containing protocol and domain only. |
| `DEV_DEPLOYED_PARAM_STORE_PATH` | SSM path for the last successful `dev` image. |
| `PROD_BASE_URL` | Production smoke-test origin containing protocol and domain only. |
| `PROD_CANDIDATE_PARAM_STORE_PATH` | SSM path for the candidate image. |
| `PROD_DEPLOYED_PARAM_STORE_PATH` | SSM path for the last successful `prod` image. |

The smoke-test workflow appends the configured service path to each base URL.

## Container and deployment configuration

- Container port: `8000`.
- ALB path: `/api/tasks/*`.
- Health check: `/health`.
- Smoke-test path: `/api/tasks/health`.
- Database: enabled in both environments.

## License

This is a proprietary portfolio project. It is publicly viewable but not open source. All rights are reserved. See [LICENSE.md](LICENSE.md).
