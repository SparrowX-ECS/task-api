from collections.abc import Generator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from prometheus_client import Counter, Gauge
from sqlmodel import Session, select

from src.models import Task, TaskStatus
from src.schemas import TaskCreate, TaskRead, TaskUpdate


router = APIRouter(prefix="/api/task", tags=["tasks"])
tasks_created_total = Counter("task_api_tasks_created_total", "Total tasks created")
tasks_by_status = Gauge("task_api_tasks_by_status", "Current tasks by status", ("status",))


def refresh_status_metrics(session: Session) -> None:
    counts = {task_status: 0 for task_status in TaskStatus}
    for task in session.exec(select(Task)).all():
        counts[task.status] += 1
    for task_status, count in counts.items():
        tasks_by_status.labels(status=task_status.value).set(count)


def get_session(request: Request) -> Generator[Session, None, None]:
    with Session(request.app.state.engine) as session:
        yield session


@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, session: Session = Depends(get_session)) -> Task:
    task = Task.model_validate(payload)
    session.add(task)
    session.commit()
    session.refresh(task)
    tasks_created_total.inc()
    refresh_status_metrics(session)
    return task


@router.get("/", response_model=list[TaskRead])
def list_tasks(
    session: Session = Depends(get_session),
    task_status: TaskStatus | None = Query(default=None, alias="status"),
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


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, session: Session = Depends(get_session)) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, payload: TaskUpdate, session: Session = Depends(get_session)) -> Task:
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


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, session: Session = Depends(get_session)) -> None:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    session.delete(task)
    session.commit()
    refresh_status_metrics(session)
