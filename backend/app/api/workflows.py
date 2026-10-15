from __future__ import annotations

import uuid
from typing import Any

from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, HTTPException

from ..core.engine import engine
from ..core.models import TaskDefinition, WorkflowDefinition, WorkflowSchedule
from ..core.scheduler import workflow_scheduler
from ..core.state_store import state_store

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("")
async def list_workflows() -> list[WorkflowDefinition]:
    return await state_store.list_workflows()


@router.post("", status_code=201)
async def create_workflow(workflow: WorkflowDefinition) -> WorkflowDefinition:
    errors = engine.validate_workflow(workflow)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    return await state_store.save_workflow(workflow)


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str) -> WorkflowDefinition:
    wf = await state_store.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str, workflow: WorkflowDefinition
) -> WorkflowDefinition:
    existing = await state_store.get_workflow(workflow_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow.id = workflow_id
    errors = engine.validate_workflow(workflow)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    return await state_store.save_workflow(workflow)


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str) -> dict[str, bool]:
    ok = await state_store.delete_workflow(workflow_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Workflow not found")
    for schedule in await state_store.list_schedules(workflow_id):
        workflow_scheduler.remove_schedule(schedule.id)
        await state_store.delete_schedule(schedule.id)
    return {"deleted": True}


@router.get("/{workflow_id}/executions")
async def list_workflow_executions(
    workflow_id: str,
    page: int = 1,
    page_size: int = 20,
    paginated: bool = False,
) -> Any:
    wf = await state_store.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if paginated:
        return await state_store.list_executions_page(workflow_id, page, page_size)
    return await state_store.list_executions(workflow_id)


@router.get("/{workflow_id}/versions")
async def list_workflow_versions(workflow_id: str) -> list[WorkflowDefinition]:
    wf = await state_store.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    versions = await state_store.get_workflow_versions(workflow_id)
    return [wf] + versions


@router.get("/{workflow_id}/metrics")
async def get_workflow_metrics(workflow_id: str) -> dict[str, Any]:
    wf = await state_store.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    metrics = await state_store.get_metrics(workflow_id)
    avg_duration_ms = (
        metrics.avg_duration_seconds * 1000
        if metrics.avg_duration_seconds is not None
        else None
    )
    return {
        "workflow_id": metrics.workflow_id,
        "total_executions": metrics.total_executions,
        "total_runs": metrics.total_executions,
        "successful": metrics.successful,
        "failed": metrics.failed,
        "failed_runs": metrics.failed,
        "cancelled": metrics.cancelled,
        "success_rate": metrics.success_rate,
        "avg_duration_seconds": metrics.avg_duration_seconds,
        "avg_duration_ms": avg_duration_ms,
        "last_execution_at": metrics.last_execution_at.isoformat()
        if metrics.last_execution_at
        else None,
    }


@router.post("/{workflow_id}/schedule", status_code=201)
async def schedule_workflow(workflow_id: str, body: dict[str, Any]) -> dict[str, Any]:
    wf = await state_store.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    cron = body.get("cron")
    if not cron or not isinstance(cron, str):
        raise HTTPException(status_code=400, detail="A 'cron' expression is required")
    try:
        CronTrigger.from_crontab(cron)
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid cron expression: {exc}"
        )
    schedule = WorkflowSchedule(
        id=body.get("schedule_id") or uuid.uuid4().hex[:12],
        workflow_id=workflow_id,
        name=body.get("name", ""),
        cron=cron,
        enabled=body.get("enabled", True),
    )
    await state_store.save_schedule(schedule)
    if schedule.enabled:
        workflow_scheduler.add_schedule(schedule)
    return {"scheduled": True, "schedule_id": schedule.id}


@router.get("/{workflow_id}/schedules")
async def list_workflow_schedules(workflow_id: str) -> list[WorkflowSchedule]:
    if not await state_store.get_workflow(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found")
    return await state_store.list_schedules(workflow_id)


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str) -> dict[str, bool]:
    schedule = await state_store.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    workflow_scheduler.remove_schedule(schedule_id)
    await state_store.delete_schedule(schedule_id)
    return {"deleted": True}


@router.post("/{workflow_id}/execute", status_code=202)
async def execute_workflow(workflow_id: str) -> dict[str, str]:
    wf = await state_store.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    errors = engine.validate_workflow(wf)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    execution_id = await engine.execute(wf)
    return {"execution_id": execution_id, "status": "started"}
