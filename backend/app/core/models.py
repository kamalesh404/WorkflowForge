from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Optional

from pydantic import BaseModel, ConfigDict, Field

EventHook = Callable[..., Coroutine[Any, Any, Any]]


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskDefinition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    dependencies: list[str] = Field(default_factory=list)
    retries: int = 3
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    handler: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None
    params: dict[str, Any] = Field(default_factory=dict)
    context_key: Optional[str] = None


class WorkflowDefinition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    description: str = ""
    tasks: list[TaskDefinition] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    workflow_timeout: Optional[float] = None
    on_start: Optional[EventHook] = None
    on_complete: Optional[EventHook] = None
    on_failure: Optional[EventHook] = None


class TaskResult(BaseModel):
    task_id: str
    task_name: str
    status: TaskStatus = TaskStatus.PENDING
    output: Any = None
    error: Optional[str] = None
    attempts: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ExecutionResult(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    workflow_id: str
    workflow_name: str = ""
    workflow_version: int = 1
    status: ExecutionStatus = ExecutionStatus.PENDING
    task_results: dict[str, TaskResult] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_tasks: int = 0
    completed_tasks: int = 0


class WorkflowSchedule(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    workflow_id: str
    name: str = ""
    cron: str
    enabled: bool = True
    last_triggered_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionLog(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    execution_id: str
    workflow_id: str
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    level: str = "info"
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WebhookConfig(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    url: str
    events: list[str] = Field(
        default_factory=lambda: ["execution_completed", "execution_failed"]
    )
    secret: Optional[str] = None
    workflow_id: Optional[str] = None
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionMetrics(BaseModel):
    workflow_id: str
    total_executions: int = 0
    successful: int = 0
    failed: int = 0
    cancelled: int = 0
    success_rate: float = 0.0
    avg_duration_seconds: Optional[float] = None
    last_execution_at: Optional[datetime] = None
