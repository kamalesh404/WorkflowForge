import asyncio

import pytest

from app.core.engine import WorkflowEngine
from app.core.models import ExecutionStatus, TaskDefinition, WorkflowDefinition


@pytest.mark.asyncio
async def test_simple_workflow_execution():
    async def add(a: int, b: int) -> int:
        return a + b

    engine = WorkflowEngine()
    wf = WorkflowDefinition(
        name="test",
        tasks=[
            TaskDefinition(name="add", handler=add, params={"a": 2, "b": 3}),
        ],
    )

    exec_id = await engine.execute(wf)
    await asyncio.sleep(0.5)

    result = await engine.get_execution_status(exec_id)
    assert result.status == ExecutionStatus.COMPLETED
    assert result.task_results[wf.tasks[0].id].output == 5


@pytest.mark.asyncio
async def test_workflow_with_dependencies():
    order = []

    async def step1() -> str:
        order.append("step1")
        return "a"

    async def step2() -> str:
        order.append("step2")
        return "b"

    async def step3(x: str, y: str) -> str:
        order.append("step3")
        return x + y

    engine = WorkflowEngine()
    wf = WorkflowDefinition(
        name="deps_test",
        tasks=[
            TaskDefinition(name="s1", handler=step1),
            TaskDefinition(name="s2", handler=step2),
            TaskDefinition(name="s3", handler=step3, dependencies=["s1", "s2"], params={"x": "a", "y": "b"}),
        ],
    )

    exec_id = await engine.execute(wf)
    await asyncio.sleep(1.0)

    result = await engine.get_execution_status(exec_id)
    assert result.status == ExecutionStatus.COMPLETED
    assert order == ["step1", "step2", "step3"]
