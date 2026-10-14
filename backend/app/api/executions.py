from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..core.state_store import state_store

router = APIRouter(prefix="/api/executions", tags=["executions"])


@router.get("")
async def list_executions(workflow_id: str | None = None) -> list:
    return await state_store.list_executions(workflow_id)


@router.get("/{execution_id}")
async def get_execution(execution_id: str):
    execution = await state_store.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.post("/{execution_id}/cancel")
async def cancel_execution(execution_id: str) -> dict[str, bool]:
    from ..core.engine import engine

    ok = await engine.cancel(execution_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Execution not found or already finished")
    return {"cancelled": True}
