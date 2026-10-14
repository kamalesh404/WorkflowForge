from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import executions, websocket, workflows
from .core.state_store import state_store

app = FastAPI(
    title="WorkflowForge",
    description="Distributed workflow orchestration engine",
    version="1.0.0",
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
