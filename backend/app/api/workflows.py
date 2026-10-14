from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..core.models import TaskDefinition, WorkflowDefinition
from ..core.state_store import state_store

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("")
async def list_workflows() -> list[WorkflowDefinition]:
    return await state_store.list_workflows()


@router.post("", status_code=201)
async def create_workflow(workflow: WorkflowDefinition) -> WorkflowDefinition:
    await state_store.save_workflow(workflow)
    return workflow


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str) -> WorkflowDefinition:
    wf = await state_store.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str) -> dict[str, bool]:
    ok = await state_store.delete_workflow(workflow_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"deleted": True}


@router.post("/{workflow_id}/execute", status_code=202)
async def execute_workflow(workflow_id: str) -> dict[str, str]:
    from ..core.engine import engine

    wf = await state_store.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    execution_id = await engine.execute(wf)
    return {"execution_id": execution_id, "status": "started"}
