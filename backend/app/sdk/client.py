from __future__ import annotations

import httpx
from typing import Any, Callable, Coroutine


class WorkflowForge:
    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")

    async def register_workflow(
        self,
        name: str,
        tasks: list[dict[str, Any]],
        description: str = "",
    ) -> dict[str, Any]:
        payload = {"name": name, "description": description, "tasks": tasks}
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/api/workflows", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def execute(self, workflow_id: str) -> dict[str, str]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/workflows/{workflow_id}/execute"
            )
            resp.raise_for_status()
            return resp.json()

    async def get_execution(self, execution_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/executions/{execution_id}"
            )
            resp.raise_for_status()
            return resp.json()

    async def list_workflows(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/api/workflows")
            resp.raise_for_status()
            return resp.json()

    async def get_stats(self) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/api/stats")
            resp.raise_for_status()
            return resp.json()


def task(
    name: str | None = None,
    depends_on: list[str] | None = None,
    retries: int = 3,
    retry_delay: float = 1.0,
    timeout: float | None = None,
) -> Callable:
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> dict[str, Any]:
        return {
            "name": name or func.__name__,
            "handler": func,
            "dependencies": depends_on or [],
            "retries": retries,
            "retry_delay": retry_delay,
            "timeout": timeout,
            "params": {},
        }

    return decorator
