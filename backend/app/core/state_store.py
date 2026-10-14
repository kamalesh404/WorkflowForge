from __future__ import annotations

import asyncio
from typing import Any

from .models import ExecutionResult, TaskResult, WorkflowDefinition


class StateStore:
    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}
        self._executions: dict[str, ExecutionResult] = {}
        self._results: dict[str, dict[str, TaskResult]] = {}
        self._lock = asyncio.Lock()

    async def save_workflow(self, workflow: WorkflowDefinition) -> None:
        async with self._lock:
            self._workflows[workflow.id] = workflow

    async def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        async with self._lock:
            return self._workflows.get(workflow_id)

    async def list_workflows(self) -> list[WorkflowDefinition]:
        async with self._lock:
            return list(self._workflows.values())

    async def delete_workflow(self, workflow_id: str) -> bool:
        async with self._lock:
            if workflow_id in self._workflows:
                del self._workflows[workflow_id]
                return True
            return False

    async def save_execution(self, execution: ExecutionResult) -> None:
        async with self._lock:
            self._executions[execution.id] = execution
            self._results[execution.id] = execution.task_results

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
            return sorted(executions, key=lambda e: e.started_at or "", reverse=True)

    async def update_task_result(
        self, execution_id: str, task_result: TaskResult
    ) -> None:
        async with self._lock:
            if execution_id in self._executions:
                self._executions[execution_id].task_results[task_result.task_id] = (
                    task_result
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
            return {
                "total_workflows": len(self._workflows),
                "total_executions": total,
                "running": running,
                "completed": completed,
                "failed": failed,
            }


state_store = StateStore()
