import asyncio

import pytest

from app.core.engine import WorkflowEngine
from app.core.models import ExecutionStatus, TaskDefinition, WorkflowDefinition


async def _wait_for_status(engine: WorkflowEngine, execution_id: str, timeout: float = 10.0):
    deadline = asyncio.get_event_loop().time() + timeout
    last = None
    while asyncio.get_event_loop().time() < deadline:
        last = await engine.get_execution_status(execution_id)
        if last is None:
            await asyncio.sleep(0.05)
            continue
        if last.status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED):
            return last
        await asyncio.sleep(0.05)
    return last


@pytest.mark.asyncio
async def test_cycle_detection_raises():
    async def noop() -> str:
        return "ok"

    engine = WorkflowEngine()
    wf = WorkflowDefinition(
        name="cycle",
        tasks=[
            TaskDefinition(id="a", name="a", handler=noop, dependencies=["c"]),
            TaskDefinition(id="b", name="b", handler=noop, dependencies=["a"]),
            TaskDefinition(id="c", name="c", handler=noop, dependencies=["b"]),
        ],
    )
    errors = engine.validate_workflow(wf)
    assert any("Cycle detected" in e for e in errors)
    with pytest.raises(ValueError):
        await engine.execute(wf)


@pytest.mark.asyncio
async def test_self_dependency_error():
    async def noop() -> str:
        return "ok"

    engine = WorkflowEngine()
    wf = WorkflowDefinition(
        name="selfdep",
        tasks=[
            TaskDefinition(id="a", name="a", handler=noop, dependencies=["a"]),
        ],
    )
    errors = engine.validate_workflow(wf)
    assert any("depends on itself" in e for e in errors)
    with pytest.raises(ValueError):
        await engine.execute(wf)


@pytest.mark.asyncio
async def test_context_passing_between_tasks():
    async def produce() -> dict:
        return {"result": 21}

    async def consume(value: int) -> int:
        return value * 2

    engine = WorkflowEngine()
    wf = WorkflowDefinition(
        name="context",
        tasks=[
            TaskDefinition(id="taskA", name="taskA", handler=produce, context_key="taskA"),
            TaskDefinition(
                id="taskB",
                name="taskB",
                handler=consume,
                dependencies=["taskA"],
                params={"value": "{taskA.result}"},
            ),
        ],
    )
    exec_id = await engine.execute(wf)
    result = await _wait_for_status(engine, exec_id, timeout=10.0)
    assert result is not None
    assert result.status == ExecutionStatus.COMPLETED
    task_b_id = next(t.id for t in wf.tasks if t.name == "taskB")
    assert result.task_results[task_b_id].output == 42


@pytest.mark.asyncio
async def test_timeout_handling():
    async def slow() -> str:
        await asyncio.sleep(5.0)
        return "done"

    engine = WorkflowEngine()
    wf = WorkflowDefinition(
        name="timeout",
        tasks=[
            TaskDefinition(id="slow", name="slow", handler=slow, timeout=0.2, retries=1, retry_delay=0.01),
        ],
    )
    exec_id = await engine.execute(wf)
    result = await _wait_for_status(engine, exec_id, timeout=15.0)
    assert result is not None
    assert result.status == ExecutionStatus.FAILED
    task_id = wf.tasks[0].id
    assert result.task_results[task_id].status.value == "failed"
    assert "timed out" in (result.task_results[task_id].error or "").lower()


@pytest.mark.asyncio
async def test_pause_resume():
    started = asyncio.Event()
    release = asyncio.Event()

    async def first() -> str:
        started.set()
        await asyncio.sleep(0.05)
        return "first"

    async def second() -> str:
        await release.wait()
        return "second"

    engine = WorkflowEngine()
    wf = WorkflowDefinition(
        name="pauseresume",
        tasks=[
            TaskDefinition(id="step1", name="step1", handler=first),
            TaskDefinition(id="step2", name="step2", handler=second, dependencies=["step1"]),
        ],
    )
    exec_id = await engine.execute(wf)
    await asyncio.wait_for(started.wait(), timeout=5.0)
    paused = await engine.pause(exec_id)
    assert paused is True
    status = await engine.get_execution_status(exec_id)
    assert status is not None
    assert status.status == ExecutionStatus.PAUSED
    release.set()
    resumed = await engine.resume(exec_id)
    assert resumed is True
    result = await _wait_for_status(engine, exec_id, timeout=10.0)
    assert result is not None
    assert result.status == ExecutionStatus.COMPLETED
