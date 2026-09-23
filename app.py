from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import perf_counter
from typing import Annotated, Any, Generator
from enum import Enum

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import ConfigDict
from sqlmodel import Field, Session, SQLModel, create_engine, select


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class TaskBase(SQLModel):
    title: str = Field(min_length=1, max_length=200, description="Short task title")
    description: str | None = Field(default=None, max_length=2000)
    assigned_to: str | None = Field(default=None, max_length=150, description="Employee or team assigned to the task")


class Task(TaskBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: TaskStatus = Field(default=TaskStatus.TODO, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskCreate(TaskBase):
    model_config = ConfigDict(extra="forbid")


class TaskUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    assigned_to: str | None = Field(default=None, max_length=150)
    status: TaskStatus | None = None


class TaskRead(TaskBase):
    id: int
    status: TaskStatus
    created_at: datetime
    updated_at: datetime


DATABASE_URL = os.getenv("TASK_API_DATABASE_URL", "sqlite:///./task.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

http_requests_total = Counter("task_api_http_requests_total", "Total HTTP requests handled", ("method", "path", "status"))
http_request_duration_seconds = Histogram("task_api_http_request_duration_seconds", "HTTP request duration", ("method", "path"))
tasks_created_total = Counter("task_api_tasks_created_total", "Total tasks created")
tasks_by_status = Gauge("task_api_tasks_by_status", "Current tasks by status", ("status",))


def refresh_status_metrics(session: Session) -> None:
    counts = {task_status: 0 for task_status in TaskStatus}
    for task in session.exec(select(Task)).all():
        counts[task.status] += 1
    for task_status, count in counts.items():
        tasks_by_status.labels(status=task_status.value).set(count)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        refresh_status_metrics(session)
    yield


app = FastAPI(
    title="SparrowX Labs Task API",
    version="1.0.0",
    description="Manages internal operational tasks for the Operations Team. Owned by Daniel Brooks.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:8080,http://localhost:3000").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MetricsMiddleware:
    def __init__(self, application: Any):
        self.application = application

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope["path"] == "/metrics":
            await self.application(scope, receive, send)
            return
        started = perf_counter()
        response_status = 500

        async def record_response(message: dict[str, Any]) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            await send(message)

        await self.application(scope, receive, record_response)
        path = scope["path"]
        if path.startswith("/tasks/"):
            path = "/tasks/{task_id}"
        http_requests_total.labels(scope["method"], path, str(response_status)).inc()
        http_request_duration_seconds.labels(scope["method"], path).observe(perf_counter() - started)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)
    started = perf_counter()
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/tasks/"):
        path = "/tasks/{task_id}"
    http_requests_total.labels(request.method, path, str(response.status_code)).inc()
    http_request_duration_seconds.labels(request.method, path).observe(perf_counter() - started)
    return response


async def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/health", tags=["system"], summary="Health check")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED, tags=["tasks"], summary="Create a task")
async def create_task(payload: TaskCreate, session: SessionDep) -> Task:
    task = Task.model_validate(payload)
    session.add(task)
    session.commit()
    session.refresh(task)
    tasks_created_total.inc()
    refresh_status_metrics(session)
    return task


@app.get("/tasks", response_model=list[TaskRead], tags=["tasks"], summary="List and filter tasks")
async def list_tasks(
    session: SessionDep,
    task_status: TaskStatus | None = Query(default=None, alias="status", description="Filter by task status"),
    assigned_to: str | None = Query(default=None, min_length=1, max_length=150),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[Task]:
    statement = select(Task)
    if task_status is not None:
        statement = statement.where(Task.status == task_status)
    if assigned_to is not None:
        statement = statement.where(Task.assigned_to == assigned_to)
    statement = statement.order_by(Task.created_at.desc()).offset(offset).limit(limit)
    return list(session.exec(statement).all())


@app.get("/tasks/{task_id}", response_model=TaskRead, tags=["tasks"], summary="Retrieve a task", responses={404: {"description": "Task not found"}})
async def get_task(task_id: int, session: SessionDep) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/tasks/{task_id}", response_model=TaskRead, tags=["tasks"], summary="Update, assign, or change task status", responses={404: {"description": "Task not found"}})
async def update_task(task_id: int, payload: TaskUpdate, session: SessionDep) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    task.updated_at = datetime.now(timezone.utc)
    session.add(task)
    session.commit()
    session.refresh(task)
    refresh_status_metrics(session)
    return task


@app.delete("/tasks/{task_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT, tags=["tasks"], summary="Delete a task", responses={404: {"description": "Task not found"}})
async def delete_task(task_id: int, session: SessionDep) -> None:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    session.delete(task)
    session.commit()
    refresh_status_metrics(session)
