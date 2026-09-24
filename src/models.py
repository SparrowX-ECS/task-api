from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class TaskFields(SQLModel):
    title: str = Field(min_length=1, max_length=200, description="Short task title")
    description: str | None = Field(default=None, max_length=2000)
    assigned_to: str | None = Field(default=None, max_length=150, description="Employee or team assigned to the task")


class Task(TaskFields, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: TaskStatus = Field(default=TaskStatus.TODO, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
