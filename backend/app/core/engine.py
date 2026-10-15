from __future__ import annotations

import asyncio
import inspect
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from .models import (
    ExecutionLog,
    ExecutionResult,
    ExecutionStatus,
    TaskDefinition,
    TaskResult,
    TaskStatus,
    WorkflowDefinition,
)
from .state_store import state_store

logger = logging.getLogger(__name__)

EventSink = Callable[[str, dict[str, Any]], Awaitable[None]]

TERMINAL_STATUSES = (
    ExecutionStatus.COMPLETED,
    ExecutionStatus.FAILED,
    ExecutionStatus.CANCELLED,
)

HOOK_EVENTS = (
    "started",
    "completed",
    "failed",
    "cancelled",
    "paused",
    "resumed",
)


class WorkflowEngine:
    def __init__(self) -> None:
        self._running: dict[str, asyncio.Task] = {}
        self._paused: set[str] = set()
        self._resume_events: dict[str, asyncio.Event] = {}
        self._hooks: dict[str, list[Callable]] = {event: [] for event in HOOK_EVENTS}
        self.event_sink: EventSink | None = None

    def add_hook(self, event: str, callback: Callable) -> None:
        key = event.replace("execution_", "").replace("task_", "")
        if key not in self._hooks:
            self._hooks[key] = []
        if callback not in self._hooks[key]:
            self._hooks[key].append(callback)

    def remove_hook(self, event: str, callback: Callable) -> None:
        key = event.replace("execution_", "").replace("task_", "")
        hooks = self._hooks.get(key, [])
        if callback in hooks:
            hooks.remove(callback)

    def validate_workflow(self, workflow: WorkflowDefinition) -> list[str]:
        errors: list[str] = []
        seen: set[str] = set()
        task_ids = {task.id for task in workflow.tasks}
        for task in workflow.tasks:
            if task.id in seen:
                errors.append(
                    f"Duplicate task id '{task.id}' in workflow '{workflow.name}'"
                )
            seen.add(task.id)
            for dependency in task.dependencies:
                if dependency == task.id:
                    errors.append(f"Task '{task.id}' depends on itself")
                elif dependency not in task_ids:
                    errors.append(
                        f"Task '{task.id}' depends on unknown task '{dependency}'"
                    )
        errors.extend(self._detect_cycles(workflow))
        return errors

    def _detect_cycles(self, workflow: WorkflowDefinition) -> list[str]:
        graph = {task.id: list(task.dependencies) for task in workflow.tasks}
        state: dict[str, int] = {}
        cycles: list[str] = []

        def visit(node: str, stack: list[str]) -> None:
            state[node] = 1
            for nxt in graph.get(node, []):
                if nxt not in graph:
                    continue
                if state.get(nxt) == 1:
                    cycle = stack[stack.index(nxt):] + [nxt]
                    cycles.append(" -> ".join(cycle))
                elif state.get(nxt, 0) == 0:
                    visit(nxt, stack + [nxt])
            state[node] = 2

        for node in graph:
            if state.get(node, 0) == 0:
                visit(node, [node])
        return [f"Cycle detected: {cycle}" for cycle in cycles]

    async def execute(self, workflow: WorkflowDefinition) -> str:
        errors = self.validate_workflow(workflow)
        if errors:
            raise ValueError("; ".join(errors))
        execution = ExecutionResult(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            workflow_version=workflow.version,
            status=ExecutionStatus.PENDING,
            total_tasks=len(workflow.tasks),
            task_results={
                task.id: TaskResult(task_id=task.id, task_name=task.name)
                for task in workflow.tasks
            },
        )
        await state_store.save_execution(execution)
        task = asyncio.create_task(self._run_with_timeout(execution.id, workflow))
        self._running[execution.id] = task
        return execution.id

    async def _run_with_timeout(
        self, execution_id: str, workflow: WorkflowDefinition
    ) -> None:
        try:
            if workflow.workflow_timeout is not None:
                await asyncio.wait_for(
                    self._run_workflow(execution_id, workflow),
                    timeout=workflow.workflow_timeout,
                )
            else:
                await self._run_workflow(execution_id, workflow)
        except TimeoutError:
            execution = await state_store.get_execution(execution_id)
            if execution and execution.status not in TERMINAL_STATUSES:
                execution.status = ExecutionStatus.FAILED
                execution.error = (
                    f"Workflow timed out after {workflow.workflow_timeout}s"
                )
                execution.completed_at = datetime.now(timezone.utc)
                await state_store.save_execution(execution)
                await self._emit("execution_failed", execution)
                await self._run_hook("on_failure", workflow, execution, execution.error)
        except asyncio.CancelledError:
            raise
        finally:
            self._resume_events.pop(execution_id, None)
            if execution_id not in self._paused:
                self._running.pop(execution_id, None)

    async def _run_workflow(
        self, execution_id: str, workflow: WorkflowDefinition
    ) -> None:
        execution = await state_store.get_execution(execution_id)
        if execution is None:
            return

        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        await state_store.save_execution(execution)
        await self._emit("execution_started", execution)
        await self._run_hook("on_start", workflow, execution)

        task_map = {task.id: task for task in workflow.tasks}
        completed: set[str] = set()
        failed: set[str] = set()

        while len(completed) + len(failed) < len(workflow.tasks):
            execution = await state_store.get_execution(execution_id)
            if execution is None or execution.status in (
                ExecutionStatus.CANCELLED,
                ExecutionStatus.FAILED,
                ExecutionStatus.COMPLETED,
            ):
                return

            await self._wait_if_paused(execution_id)

            ready, skipped = self._get_ready_tasks(workflow.tasks, completed, failed)
            for skipped_id in skipped:
                result = execution.task_results.get(skipped_id)
                if result is not None:
                    result.status = TaskStatus.SKIPPED
                    result.error = "Skipped because a dependency failed"
                    await state_store.update_task_result(execution_id, result)
                failed.add(skipped_id)

            if not ready:
                break

            await asyncio.gather(
                *[
                    self._execute_task_with_retry(execution_id, task_map[tid], task_map)
                    for tid in ready
                ],
                return_exceptions=True,
            )

            execution = await state_store.get_execution(execution_id)
            if execution is None:
                return
            for tid in ready:
                result = execution.task_results.get(tid)
                if result is None:
                    continue
                if result.status == TaskStatus.COMPLETED:
                    completed.add(tid)
                    execution.completed_tasks += 1
                else:
                    failed.add(tid)
            await state_store.save_execution(execution)

        execution = await state_store.get_execution(execution_id)
        if execution is None or execution.status != ExecutionStatus.RUNNING:
            return

        if failed:
            execution.status = ExecutionStatus.FAILED
            execution.error = f"{len(failed)} task(s) failed"
        else:
            execution.status = ExecutionStatus.COMPLETED
        execution.completed_at = datetime.now(timezone.utc)
        await state_store.save_execution(execution)

        if failed:
            await self._emit("execution_failed", execution)
            await self._run_hook(
                "on_failure", workflow, execution, execution.error
            )
        else:
            await self._emit("execution_completed", execution)
            await self._run_hook("on_complete", workflow, execution)

    def _get_ready_tasks(
        self,
        tasks: list[TaskDefinition],
        completed: set[str],
        failed: set[str],
    ) -> tuple[list[str], list[str]]:
        ready: list[str] = []
        skipped: list[str] = []
        for task in tasks:
            if task.id in completed or task.id in failed:
                continue
            if any(dep in failed for dep in task.dependencies):
                skipped.append(task.id)
            elif all(dep in completed for dep in task.dependencies):
                ready.append(task.id)
        return ready, skipped

    async def _execute_task_with_retry(
        self,
        execution_id: str,
        task: TaskDefinition,
        task_map: dict[str, TaskDefinition],
    ) -> TaskResult:
        execution = await state_store.get_execution(execution_id)
        if execution is None:
            return TaskResult(
                task_id=task.id, task_name=task.name, status=TaskStatus.FAILED
            )

        result = execution.task_results.get(task.id) or TaskResult(
            task_id=task.id, task_name=task.name
        )
        result.started_at = datetime.now(timezone.utc)
        result.status = TaskStatus.RUNNING
        await state_store.update_task_result(execution_id, result)
        await self._emit("task_started", execution, task_id=task.id)

        context = self._build_context(execution, task_map)

        for attempt in range(1, task.retries + 1):
            result.attempts = attempt
            try:
                if task.handler is None:
                    raise ValueError(f"Task '{task.name}' has no handler")
                kwargs = {
                    key: self._resolve_value(value, context)
                    for key, value in (task.params or {}).items()
                }
                if self._accepts_context(task.handler):
                    kwargs["context"] = context
                output = await asyncio.wait_for(
                    task.handler(**kwargs),
                    timeout=task.timeout,
                )
                result.output = output
                result.status = TaskStatus.COMPLETED
                result.completed_at = datetime.now(timezone.utc)
                key = task.context_key or task.id
                execution.context[key] = output
                execution.context[task.name] = output
                break
            except TimeoutError as exc:
                result.error = f"Task timed out after {task.timeout}s"
                result.status = TaskStatus.FAILED
                logger.warning(
                    "Task '%s' attempt %d/%d timed out after %ss",
                    task.name,
                    attempt,
                    task.retries,
                    task.timeout,
                    exc_info=exc,
                )
                if attempt < task.retries:
                    await asyncio.sleep(task.retry_delay * (2 ** (attempt - 1)))
            except Exception as exc:
                result.error = str(exc)
                result.status = TaskStatus.FAILED
                logger.warning(
                    "Task '%s' attempt %d/%d failed: %s",
                    task.name,
                    attempt,
                    task.retries,
                    exc,
                )
                if attempt < task.retries:
                    await asyncio.sleep(task.retry_delay * (2 ** (attempt - 1)))

        if result.status == TaskStatus.COMPLETED:
            await self._emit(
                "task_completed", execution, task_id=task.id, output=result.output
            )
            await state_store.append_log(
                ExecutionLog(
                    execution_id=execution_id,
                    workflow_id=execution.workflow_id,
                    task_id=task.id,
                    task_name=task.name,
                    level="info",
                    message=f"Task '{task.name}' completed",
                )
            )
        else:
            await self._emit(
                "task_failed", execution, task_id=task.id, error=result.error
            )
            await state_store.append_log(
                ExecutionLog(
                    execution_id=execution_id,
                    workflow_id=execution.workflow_id,
                    task_id=task.id,
                    task_name=task.name,
                    level="error",
                    message=f"Task '{task.name}' failed: {result.error}",
                )
            )

        await state_store.update_task_result(execution_id, result)
        return result

    def _build_context(
        self,
        execution: ExecutionResult,
        task_map: dict[str, TaskDefinition],
    ) -> dict[str, Any]:
        context = dict(execution.context)
        for task_id, task in task_map.items():
            result = execution.task_results.get(task_id)
            if (
                result is not None
                and result.status == TaskStatus.COMPLETED
                and result.output is not None
            ):
                context[task_id] = result.output
                context[task.name] = result.output
        return context

    def _resolve_value(self, value: Any, context: dict[str, Any]) -> Any:
        if (
            isinstance(value, str)
            and len(value) > 2
            and value.startswith("{")
            and value.endswith("}")
        ):
            reference = value[1:-1].strip()
            parts = reference.split(".", 1)
            if parts[0] in context:
                output = context[parts[0]]
                if len(parts) == 2:
                    if isinstance(output, dict):
                        return output.get(parts[1])
                    return None
                return output
            return value
        if isinstance(value, dict):
            return {key: self._resolve_value(item, context) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve_value(item, context) for item in value]
        return value

    @staticmethod
    def _accepts_context(handler: Callable[..., Any]) -> bool:
        try:
            signature = inspect.signature(handler)
        except (TypeError, ValueError):
            return False
        return "context" in signature.parameters or any(
            param.kind == inspect.Parameter.VAR_KEYWORD
            for param in signature.parameters.values()
        )

    async def pause(self, execution_id: str) -> bool:
        if execution_id not in self._running:
            return False
        self._paused.add(execution_id)
        event = self._resume_events.setdefault(execution_id, asyncio.Event())
        event.clear()
        execution = await state_store.get_execution(execution_id)
        if execution and execution.status == ExecutionStatus.RUNNING:
            execution.status = ExecutionStatus.PAUSED
            await state_store.save_execution(execution)
            await self._emit("execution_paused", execution)
        return True

    async def resume(self, execution_id: str) -> bool:
        if execution_id not in self._paused:
            return False
        self._paused.discard(execution_id)
        event = self._resume_events.get(execution_id)
        if event is not None:
            event.set()
        execution = await state_store.get_execution(execution_id)
        if execution and execution.status == ExecutionStatus.PAUSED:
            execution.status = ExecutionStatus.RUNNING
            await state_store.save_execution(execution)
            await self._emit("execution_resumed", execution)
        return True

    async def _wait_if_paused(self, execution_id: str) -> None:
        while execution_id in self._paused:
            event = self._resume_events.setdefault(execution_id, asyncio.Event())
            if event.is_set():
                event.clear()
            await event.wait()

    async def cancel(self, execution_id: str) -> bool:
        task = self._running.get(execution_id)
        self._paused.discard(execution_id)
        event = self._resume_events.get(execution_id)
        if event is not None:
            event.set()
        if task is not None and not task.done():
            task.cancel()
            execution = await state_store.get_execution(execution_id)
            if execution and execution.status not in TERMINAL_STATUSES:
                execution.status = ExecutionStatus.CANCELLED
                execution.completed_at = datetime.now(timezone.utc)
                await state_store.save_execution(execution)
                await self._emit("execution_cancelled", execution)
                await self._run_hook("on_failure", workflow=None, execution=execution, error="Cancelled")
            return True
        execution = await state_store.get_execution(execution_id)
        if execution and execution.status in (
            ExecutionStatus.PENDING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.PAUSED,
        ):
            execution.status = ExecutionStatus.CANCELLED
            execution.completed_at = datetime.now(timezone.utc)
            await state_store.save_execution(execution)
            return True
        return False

    async def get_execution_status(
        self, execution_id: str
    ) -> ExecutionResult | None:
        return await state_store.get_execution(execution_id)

    async def _emit(
        self, event_type: str, execution: ExecutionResult, **extra: Any
    ) -> None:
        payload: dict[str, Any] = {
            "event": event_type,
            "execution_id": execution.id,
            "workflow_id": execution.workflow_id,
            "workflow_name": execution.workflow_name,
            "status": execution.status.value,
            "completed_tasks": execution.completed_tasks,
            "total_tasks": execution.total_tasks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **extra,
        }
        hook_key = event_type.replace("execution_", "").replace("task_", "")
        for hook in self._hooks.get(hook_key, []):
            try:
                await hook(payload)
            except Exception:
                logger.exception("Event hook failed for %s", event_type)
        if self.event_sink is not None:
            try:
                await self.event_sink(event_type, payload)
            except Exception:
                logger.exception("Event sink failed for %s", event_type)

    async def _run_hook(
        self,
        hook_name: str,
        workflow: WorkflowDefinition | None,
        execution: ExecutionResult,
        error: str | None = None,
    ) -> None:
        hooks: list[Callable] = []
        if workflow is not None:
            callback = getattr(workflow, hook_name, None)
            if callback is not None:
                hooks.append(callback)
        hooks.extend(self._hooks.get(hook_name, []))
        for hook in hooks:
            try:
                if hook_name == "on_start":
                    await hook(execution)
                elif hook_name == "on_complete":
                    await hook(execution)
                else:
                    await hook(execution, error)
            except Exception:
                logger.exception("Workflow hook '%s' failed", hook_name)


engine = WorkflowEngine()
