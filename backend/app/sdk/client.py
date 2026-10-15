from __future__ import annotations

import asyncio
import time

import httpx
from typing import Any, Callable, Coroutine


class WorkflowBuilder:
    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._tasks: list[dict[str, Any]] = []

    def add_task(
        self,
        name: str,
        handler_name: str | None = None,
        dependencies: list[str] | None = None,
        retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float | None = None,
        params: dict[str, Any] | None = None,
        context_key: str | None = None,
    ) -> WorkflowBuilder:
        task: dict[str, Any] = {
            "name": name,
            "dependencies": dependencies or [],
            "retries": retries,
            "retry_delay": retry_delay,
            "timeout": timeout,
            "params": params or {},
        }
        if handler_name is not None:
            task["handler_name"] = handler_name
        if context_key is not None:
            task["context_key"] = context_key
        self._tasks.append(task)
        return self

    def build(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "tasks": self._tasks,
        }


class WorkflowForge:
    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> WorkflowForge:
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    async def _post(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._client is not None:
            resp = await self._client.post(path, json=payload or {})
            resp.raise_for_status()
            return resp.json()
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(path, json=payload or {})
            resp.raise_for_status()
            return resp.json()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if self._client is not None:
            resp = await self._client.get(path, params=params)
            resp.raise_for_status()
            return resp.json()
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.get(path, params=params)
            resp.raise_for_status()
            return resp.json()

    async def _put(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self._client is not None:
            resp = await self._client.put(path, json=payload)
            resp.raise_for_status()
            return resp.json()
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.put(path, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def register_workflow(
        self,
        name: str | dict[str, Any] | WorkflowBuilder,
        tasks: list[dict[str, Any]] | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        if isinstance(name, WorkflowBuilder):
            payload = name.build()
        elif isinstance(name, dict):
            payload = name
        elif tasks is not None:
            payload = {"name": name, "description": description, "tasks": tasks}
        else:
            payload = {"name": name, "description": description, "tasks": []}
        return await self._post("/api/workflows", payload)

    async def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        return await self._get(f"/api/workflows/{workflow_id}")

    async def update_workflow(self, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._put(f"/api/workflows/{workflow_id}", payload)

    async def execute(self, workflow_id: str) -> dict[str, str]:
        return await self._post(f"/api/workflows/{workflow_id}/execute", {})

    async def get_execution(self, execution_id: str) -> dict[str, Any]:
        return await self._get(f"/api/executions/{execution_id}")

    async def list_workflows(self) -> list[dict[str, Any]]:
        result = await self._get("/api/workflows")
        return result if isinstance(result, list) else []

    async def list_executions(self, workflow_id: str | None = None) -> Any:
        params = {"workflow_id": workflow_id} if workflow_id else None
        return await self._get("/api/executions", params=params)

    async def get_logs(self, execution_id: str) -> Any:
        return await self._get(f"/api/executions/{execution_id}/logs")

    async def get_metrics(self, workflow_id: str) -> dict[str, Any]:
        return await self._get(f"/api/workflows/{workflow_id}/metrics")

    async def schedule(
        self,
        workflow_id: str,
        cron: str,
        name: str = "",
        enabled: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"cron": cron, "name": name, "enabled": enabled}
        return await self._post(f"/api/workflows/{workflow_id}/schedule", payload)

    async def cancel(self, execution_id: str) -> dict[str, Any]:
        return await self._post(f"/api/executions/{execution_id}/cancel", {})

    async def pause(self, execution_id: str) -> dict[str, Any]:
        return await self._post(f"/api/executions/{execution_id}/pause", {})

    async def resume(self, execution_id: str) -> dict[str, Any]:
        return await self._post(f"/api/executions/{execution_id}/resume", {})

    async def get_stats(self) -> dict[str, Any]:
        return await self._get("/api/stats")

    async def watch_execution(
        self,
        execution_id: str,
        poll_interval: float = 1.0,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        terminal = {"completed", "failed", "cancelled"}
        start = time.monotonic()
        last: dict[str, Any] = {}
        while True:
            last = await self.get_execution(execution_id)
            status = str(last.get("status", "")).lower()
            if status in terminal:
                return last
            if time.monotonic() - start >= timeout:
                raise TimeoutError(f"Timed out waiting for execution {execution_id}")
            await asyncio.sleep(poll_interval)


def task(
    name: str | None = None,
    depends_on: list[str] | None = None,
    retries: int = 3,
    retry_delay: float = 1.0,
    timeout: float | None = None,
    context_key: str | None = None,
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
            "context_key": context_key,
        }

    return decorator
