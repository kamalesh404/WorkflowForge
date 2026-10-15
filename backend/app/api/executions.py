from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ..core.state_store import state_store

router = APIRouter(prefix="/api/executions", tags=["executions"])


@router.get("")
async def list_executions(
    workflow_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
    paginated: bool = False,
) -> Any:
    if paginated:
        return await state_store.list_executions_page(workflow_id, page, page_size)
    return await state_store.list_executions(workflow_id)


@router.get("/{execution_id}")
async def get_execution(execution_id: str):
    execution = await state_store.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.get("/{execution_id}/logs")
async def get_execution_logs(
    execution_id: str,
    page: int = 1,
    page_size: int = 50,
    paginated: bool = False,
) -> Any:
    execution = await state_store.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    if paginated:
        return await state_store.list_logs_page(execution_id, page, page_size)
    return await state_store.list_logs(execution_id)


@router.post("/{execution_id}/cancel")
async def cancel_execution(execution_id: str) -> dict[str, bool]:
    from ..core.engine import engine

    ok = await engine.cancel(execution_id)
    if not ok:
        raise HTTPException(
            status_code=404, detail="Execution not found or already finished"
        )
    return {"cancelled": True}


@router.post("/{execution_id}/pause")
async def pause_execution(execution_id: str) -> dict[str, bool]:
    from ..core.engine import engine

    execution = await state_store.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    ok = await engine.pause(execution_id)
    if not ok:
        raise HTTPException(
            status_code=409,
            detail="Execution is not running or already finished",
        )
    return {"paused": True}


@router.post("/{execution_id}/resume")
async def resume_execution(execution_id: str) -> dict[str, bool]:
    from ..core.engine import engine

    execution = await state_store.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    ok = await engine.resume(execution_id)
    if not ok:
        raise HTTPException(status_code=409, detail="Execution is not paused")
    return {"resumed": True}
