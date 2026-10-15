import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import executions, websocket, workflows
from .api.websocket import websocket_manager
from .core.engine import engine
from .core.notifications import notification_manager
from .core.scheduler import workflow_scheduler
from .core.state_store import state_store


async def dispatch_event(event_type: str, payload: dict) -> None:
    await websocket_manager.broadcast(payload)
    await notification_manager.notify(event_type, payload)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await state_store.start()
    await notification_manager.start()
    await workflow_scheduler.start()
    loaded = await workflow_scheduler.load_schedules()
    engine.event_sink = dispatch_event
    logging.getLogger(__name__).info(
        "WorkflowForge started with %d scheduled job(s)", loaded
    )
    yield
    engine.event_sink = None
    await workflow_scheduler.stop()
    await notification_manager.stop()
    await state_store.stop()


app = FastAPI(
    title="WorkflowForge",
    description="Distributed workflow orchestration engine",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflows.router)
app.include_router(executions.router)
app.include_router(websocket.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "workflowforge"}


@app.get("/api/stats")
async def get_stats() -> dict:
    return await state_store.get_stats()
