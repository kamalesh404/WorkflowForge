from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from .models import (
    ExecutionLog,
    ExecutionMetrics,
    ExecutionResult,
    ExecutionStatus,
    TaskResult,
    TaskStatus,
    WebhookConfig,
    WorkflowDefinition,
    WorkflowSchedule,
)

_MAX_LOGS = 10_000
_AUTOSAVE_INTERVAL = 2.0
_PERSISTED_STATUSES = (
    ExecutionStatus.COMPLETED,
    ExecutionStatus.FAILED,
    ExecutionStatus.CANCELLED,
)


class StateStore:
    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = Path(
            data_dir or os.environ.get("WORKFLOWFORGE_DATA_DIR", "./data")
        )
        self._lock = asyncio.Lock()
        self._dirty = False
        self._save_task: asyncio.Task | None = None
        self._workflows: dict[str, WorkflowDefinition] = {}
        self._workflow_versions: dict[str, list[WorkflowDefinition]] = {}
        self._executions: dict[str, ExecutionResult] = {}
        self._results: dict[str, dict[str, TaskResult]] = {}
        self._logs: list[ExecutionLog] = []
        self._schedules: dict[str, WorkflowSchedule] = {}
        self._webhooks: dict[str, WebhookConfig] = {}

    async def start(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        await self._load()
        self._save_task = asyncio.create_task(self._autosave_loop())

    async def stop(self) -> None:
        if self._save_task is not None:
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass
            self._save_task = None
        await self._persist_now()

    async def _autosave_loop(self) -> None:
        while True:
            await asyncio.sleep(_AUTOSAVE_INTERVAL)
            if self._dirty:
                await self._persist_now()

    async def _persist_now(self) -> None:
        async with self._lock:
            if not self._dirty:
                return
            await asyncio.to_thread(self._write_files)
            self._dirty = False

    def _workflow_to_dict(self, workflow: WorkflowDefinition) -> dict[str, Any]:
        return {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "tasks": [
                {
                    "id": task.id,
                    "name": task.name,
                    "dependencies": task.dependencies,
                    "retries": task.retries,
                    "retry_delay": task.retry_delay,
                    "timeout": task.timeout,
                    "params": task.params,
                    "context_key": task.context_key,
                }
                for task in workflow.tasks
            ],
            "created_at": workflow.created_at.isoformat(),
            "version": workflow.version,
            "workflow_timeout": workflow.workflow_timeout,
        }

    def _write_files(self) -> None:
        payload = {
            "workflows": [
                self._workflow_to_dict(w) for w in self._workflows.values()
            ],
            "workflow_versions": {
                wid: [self._workflow_to_dict(w) for w in versions]
                for wid, versions in self._workflow_versions.items()
            },
            "executions": [
                e.model_dump(mode="json") for e in self._executions.values()
            ],
            "logs": [log.model_dump(mode="json") for log in self._logs],
            "schedules": [
                s.model_dump(mode="json") for s in self._schedules.values()
            ],
            "webhooks": [w.model_dump(mode="json") for w in self._webhooks.values()],
        }
        for name, data in payload.items():
            path = self._data_dir / f"{name}.json"
            tmp_path = path.with_suffix(".json.tmp")
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, default=str)
            os.replace(tmp_path, path)

    async def _load(self) -> None:
        workflows_raw = self._read_json("workflows.json")
        for item in workflows_raw:
            workflow = WorkflowDefinition(**item)
            self._workflows[workflow.id] = workflow
        versions_raw = self._read_json("workflow_versions.json")
        for wid, items in versions_raw.items():
            self._workflow_versions[wid] = [
                WorkflowDefinition(**item) for item in items
            ]
        executions_raw = self._read_json("executions.json")
        for item in executions_raw:
            execution = ExecutionResult(**item)
            self._executions[execution.id] = execution
            self._results[execution.id] = execution.task_results
        logs_raw = self._read_json("logs.json")
        self._logs = [ExecutionLog(**item) for item in logs_raw]
        schedules_raw = self._read_json("schedules.json")
        for item in schedules_raw:
            schedule = WorkflowSchedule(**item)
            self._schedules[schedule.id] = schedule
        webhooks_raw = self._read_json("webhooks.json")
        for item in webhooks_raw:
            webhook = WebhookConfig(**item)
            self._webhooks[webhook.id] = webhook

    def _read_json(self, filename: str) -> list[Any]:
        path = self._data_dir / filename
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    async def save_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        async with self._lock:
            existing = self._workflows.get(workflow.id)
            if existing is not None:
                self._workflow_versions.setdefault(workflow.id, []).append(existing)
                workflow.version = existing.version + 1
            self._workflows[workflow.id] = workflow
            self._dirty = True
        return workflow

    async def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        async with self._lock:
            return self._workflows.get(workflow_id)

    async def list_workflows(self) -> list[WorkflowDefinition]:
        async with self._lock:
            return list(self._workflows.values())

    async def get_workflow_versions(
        self, workflow_id: str
    ) -> list[WorkflowDefinition]:
        async with self._lock:
            return list(self._workflow_versions.get(workflow_id, []))

    async def delete_workflow(self, workflow_id: str) -> bool:
        async with self._lock:
            if workflow_id in self._workflows:
                del self._workflows[workflow_id]
                self._workflow_versions.pop(workflow_id, None)
                self._dirty = True
                return True
            return False

    async def save_execution(self, execution: ExecutionResult) -> None:
        async with self._lock:
            self._executions[execution.id] = execution
            self._results[execution.id] = execution.task_results
            self._dirty = True

    async def get_execution(self, execution_id: str) -> ExecutionResult | None:
        async with self._lock:
            return self._executions.get(execution_id)

    async def list_executions(
        self, workflow_id: str | None = None
    ) -> list[ExecutionResult]:
        async with self._lock:
            executions = list(self._executions.values())
            if workflow_id:
                executions = [e for e in executions if e.workflow_id == workflow_id]
            return sorted(
                executions, key=lambda e: e.started_at or "", reverse=True
            )

    async def list_executions_page(
        self,
        workflow_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        executions = await self.list_executions(workflow_id)
        total = len(executions)
        start = max(page - 1, 0) * page_size
        items = executions[start : start + page_size]
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_task_result(
        self, execution_id: str, task_result: TaskResult
    ) -> None:
        async with self._lock:
            execution = self._executions.get(execution_id)
            if execution is not None:
                execution.task_results[task_result.task_id] = task_result
                self._dirty = True

    async def append_log(self, log: ExecutionLog) -> None:
        async with self._lock:
            self._logs.append(log)
            if len(self._logs) > _MAX_LOGS:
                self._logs = self._logs[-_MAX_LOGS:]
            self._dirty = True

    async def list_logs(
        self, execution_id: str | None = None
    ) -> list[ExecutionLog]:
        async with self._lock:
            logs = list(self._logs)
            if execution_id:
                logs = [log for log in logs if log.execution_id == execution_id]
            return sorted(logs, key=lambda log: log.timestamp, reverse=True)

    async def list_logs_page(
        self,
        execution_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        logs = await self.list_logs(execution_id)
        total = len(logs)
        start = max(page - 1, 0) * page_size
        items = logs[start : start + page_size]
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def save_schedule(self, schedule: WorkflowSchedule) -> WorkflowSchedule:
        async with self._lock:
            self._schedules[schedule.id] = schedule
            self._dirty = True
        return schedule

    async def get_schedule(self, schedule_id: str) -> WorkflowSchedule | None:
        async with self._lock:
            return self._schedules.get(schedule_id)

    async def list_schedules(
        self, workflow_id: str | None = None
    ) -> list[WorkflowSchedule]:
        async with self._lock:
            schedules = list(self._schedules.values())
            if workflow_id:
                schedules = [s for s in schedules if s.workflow_id == workflow_id]
            return schedules

    async def delete_schedule(self, schedule_id: str) -> bool:
        async with self._lock:
            if schedule_id in self._schedules:
                del self._schedules[schedule_id]
                self._dirty = True
                return True
            return False

    async def save_webhook(self, webhook: WebhookConfig) -> WebhookConfig:
        async with self._lock:
            self._webhooks[webhook.id] = webhook
            self._dirty = True
        return webhook

    async def get_webhook(self, webhook_id: str) -> WebhookConfig | None:
        async with self._lock:
            return self._webhooks.get(webhook_id)

    async def list_webhooks(
        self, enabled: bool | None = None
    ) -> list[WebhookConfig]:
        async with self._lock:
            webhooks = list(self._webhooks.values())
            if enabled is not None:
                webhooks = [w for w in webhooks if w.enabled == enabled]
            return webhooks

    async def delete_webhook(self, webhook_id: str) -> bool:
        async with self._lock:
            if webhook_id in self._webhooks:
                del self._webhooks[webhook_id]
                self._dirty = True
                return True
            return False

    async def get_metrics(self, workflow_id: str) -> ExecutionMetrics:
        async with self._lock:
            executions = [
                e
                for e in self._executions.values()
                if e.workflow_id == workflow_id
            ]
        successful = sum(
            1 for e in executions if e.status == ExecutionStatus.COMPLETED
        )
        failed = sum(1 for e in executions if e.status == ExecutionStatus.FAILED)
        cancelled = sum(
            1 for e in executions if e.status == ExecutionStatus.CANCELLED
        )
        durations = [
            (e.completed_at - e.started_at).total_seconds()
            for e in executions
            if e.status in _PERSISTED_STATUSES
            and e.started_at is not None
            and e.completed_at is not None
        ]
        total = len(executions)
        avg_duration = (
            sum(durations) / len(durations) if durations else None
        )
        last_execution_at = (
            max(e.started_at for e in executions if e.started_at is not None)
            if any(e.started_at is not None for e in executions)
            else None
        )
        return ExecutionMetrics(
            workflow_id=workflow_id,
            total_executions=total,
            successful=successful,
            failed=failed,
            cancelled=cancelled,
            success_rate=round(successful / total, 4) if total else 0.0,
            avg_duration_seconds=round(avg_duration, 4)
            if avg_duration is not None
            else None,
            last_execution_at=last_execution_at,
        )

    async def get_stats(self) -> dict[str, Any]:
        async with self._lock:
            total = len(self._executions)
            running = sum(
                1
                for e in self._executions.values()
                if e.status.value == "running"
            )
            completed = sum(
                1
                for e in self._executions.values()
                if e.status.value == "completed"
            )
            failed = sum(
                1
                for e in self._executions.values()
                if e.status.value == "failed"
            )
            paused = sum(
                1
                for e in self._executions.values()
                if e.status.value == "paused"
            )
            return {
                "total_workflows": len(self._workflows),
                "total_executions": total,
                "running": running,
                "paused": paused,
                "completed": completed,
                "failed": failed,
            }


state_store = StateStore()
