from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from .models import (
    ExecutionResult,
    ExecutionStatus,
    TaskDefinition,
    TaskResult,
    TaskStatus,
    WorkflowDefinition,
)
from .state_store import state_store

logger = logging.getLogger(__name__)


class WorkflowEngine:
    def __init__(self) -> None:
        self._running: dict[str, asyncio.Task] = {}

    async def execute(self, workflow: WorkflowDefinition) -> str:
        execution = ExecutionResult(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            status=ExecutionStatus.PENDING,
            total_tasks=len(workflow.tasks),
            task_results={
                task.id: TaskResult(task_id=task.id, task_name=task.name)
                for task in workflow.tasks
            },
        )
        await state_store.save_execution(execution)

        task = asyncio.create_task(self._run_workflow(execution.id, workflow))
        self._running[execution.id] = task
        return execution.id

    async def _run_workflow(
        self, execution_id: str, workflow: WorkflowDefinition
    ) -> None:
        execution = await state_store.get_execution(execution_id)
        if not execution:
            return

        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        await state_store.save_execution(execution)

        task_map = {t.id: t for t in workflow.tasks}
        completed: set[str] = set()
        failed: set[str] = set()

        while len(completed) + len(failed) < len(workflow.tasks):
            ready = self._get_ready_tasks(workflow.tasks, completed, failed)
            if not ready:
                break

            results = await asyncio.gather(
                *[self._execute_task_with_retry(execution_id, task_map[tid]) for tid in ready],
                return_exceptions=True,
            )

            for tid, result in zip(ready, results):
                if isinstance(result, Exception):
                    failed.add(tid)
                else:
                    completed.add(tid)
                    execution.completed_tasks += 1
                    await state_store.save_execution(execution)

        execution = await state_store.get_execution(execution_id)
        if execution:
            if failed:
                execution.status = ExecutionStatus.FAILED
            else:
                execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)
            await state_store.save_execution(execution)

        self._running.pop(execution_id, None)

    def _get_ready_tasks(
        self,
        tasks: list[TaskDefinition],
        completed: set[str],
        failed: set[str],
    ) -> list[str]:
        ready = []
        for task in tasks:
            if task.id in completed or task.id in failed:
                continue
            deps_satisfied = all(d in completed for d in task.dependencies)
            deps_failed = any(d in failed for d in task.dependencies)
            if deps_failed:
                failed.add(task.id)
                continue
            if deps_satisfied:
                ready.append(task.id)
        return ready

    async def _execute_task_with_retry(
        self, execution_id: str, task: TaskDefinition
    ) -> TaskResult:
        result = TaskResult(task_id=task.id, task_name=task.name)
        result.started_at = datetime.now(timezone.utc)
        result.status = TaskStatus.RUNNING

        for attempt in range(1, task.retries + 1):
            result.attempts = attempt
            try:
                if task.handler is None:
                    raise ValueError(f"Task {task.name} has no handler")
                output = await asyncio.wait_for(
                    task.handler(**(task.params or {})),
                    timeout=task.timeout,
                )
                result.output = output
                result.status = TaskStatus.COMPLETED
                result.completed_at = datetime.now(timezone.utc)
                break
            except Exception as exc:
                result.error = str(exc)
                result.status = TaskStatus.FAILED
                logger.warning(
                    "Task %s attempt %d/%d failed: %s",
                    task.name,
                    attempt,
                    task.retries,
                    exc,
                )
                if attempt < task.retries:
                    await asyncio.sleep(task.retry_delay * (2 ** (attempt - 1)))

        await state_store.update_task_result(execution_id, result)
        return result

    async def cancel(self, execution_id: str) -> bool:
        task = self._running.get(execution_id)
        if task and not task.done():
            task.cancel()
            execution = await state_store.get_execution(execution_id)
            if execution:
                execution.status = ExecutionStatus.CANCELLED
                execution.completed_at = datetime.now(timezone.utc)
                await state_store.save_execution(execution)
            return True
        return False

    async def get_execution_status(
        self, execution_id: str
    ) -> ExecutionResult | None:
        return await state_store.get_execution(execution_id)


engine = WorkflowEngine()
