from __future__ import annotations

import asyncio

from app.sdk.client import WorkflowBuilder, WorkflowForge


def build_pipeline() -> dict:
    builder = WorkflowBuilder(name="etl-pipeline", description="Extract transform load example")
    builder.add_task(
        name="extract",
        handler_name="extract_handler",
        params={"source": "warehouse"},
        context_key="raw",
    )
    builder.add_task(
        name="transform",
        handler_name="transform_handler",
        dependencies=["extract"],
        params={"records": "{extract.raw}"},
        context_key="clean",
    )
    builder.add_task(
        name="load",
        handler_name="load_handler",
        dependencies=["transform"],
        params={"payload": "{transform.clean}"},
        context_key="result",
    )
    return builder.build()


async def main() -> None:
    builder = WorkflowBuilder(
        name="etl-pipeline",
        description="Extract transform load example",
    )
    builder.add_task(
        name="extract",
        handler_name="extract_handler",
        retries=3,
        retry_delay=1.0,
        timeout=30.0,
        params={"source": "warehouse"},
        context_key="raw",
    )
    builder.add_task(
        name="transform",
        handler_name="transform_handler",
        dependencies=["extract"],
        retries=3,
        retry_delay=1.0,
        timeout=30.0,
        params={"records": "{extract.raw}"},
        context_key="clean",
    )
    builder.add_task(
        name="load",
        handler_name="load_handler",
        dependencies=["transform"],
        retries=3,
        retry_delay=1.0,
        timeout=30.0,
        params={"payload": "{transform.clean}"},
        context_key="result",
    )
    payload = builder.build()
    async with WorkflowForge(base_url="http://localhost:8000") as forge:
        registered = await forge.register_workflow(payload)
        workflow_id = registered["id"]
        started = await forge.execute(workflow_id)
        execution_id = started["execution_id"]
        final = await forge.watch_execution(execution_id, poll_interval=1.0, timeout=120.0)
        print(final)


if __name__ == "__main__":
    asyncio.run(main())
