from datetime import datetime

from pydantic import ConfigDict
from sqlmodel import Field, SQLModel

from src.models import TaskStatus


class TaskCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200, description="Short task title")
    description: str | None = Field(default=None, max_length=2000)
    assigned_to: str | None = Field(default=None, max_length=150, description="Employee or team assigned to the task")


class TaskUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    assigned_to: str | None = Field(default=None, max_length=150)
    status: TaskStatus | None = None


class TaskRead(TaskCreate):
    id: int
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
