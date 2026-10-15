# WorkflowForge

Self-hosted distributed workflow orchestration engine. A lightweight Temporal / Airflow alternative you can run in one Docker command.

## Problem Statement

Enterprise teams lose 40+ hours weekly managing complex multi-step data pipelines, ETL jobs, and business workflows that are fragile, hard to debug, and have zero visibility into execution state. Existing tools are either too heavy (Airflow, Temporal) or too limited (cron + scripts).

## Unique Solution

WorkflowForge gives you production orchestration primitives without the operational burden:

- DAG engine with cycle detection, missing-dependency validation, and parallel level execution
- Context passing between tasks via `{task_id.field}` references, so ETL stages chain typed outputs
- Pause / resume / cancel on live executions, plus workflow-level timeouts and per-task timeouts
- Automatic retries with exponential backoff and skipped-dependency propagation
- JSON file persistence with versioning, execution history, paginated logs, and metrics
- Cron scheduling via APScheduler, webhook notifications with HMAC signatures, SMTP failure alerts
- Real-time WebSocket event bus with per-workflow subscriptions
- Fluent Python SDK with builder pattern and execution watcher that polls to completion
- React dashboard with DAG visualization, execution timeline, metrics, and scheduling UI

## Features

- DAG validation and topological parallel execution
- Context-aware task chaining
- Pause, resume, cancel
- Retries with exponential backoff
- Cron scheduling
- Webhooks + email notifications
- Persistent state with workflow versioning
- Execution metrics (success rate, avg duration)
- Real-time WebSocket monitoring
- Python SDK (builder + watcher)
- Docker Compose one-command setup

## Quick Start

### Docker

```bash
docker-compose up
```

Frontend: http://localhost:3000
Backend API: http://localhost:8000
API docs: http://localhost:8000/docs

### Manual Setup

Backend:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Python SDK

```python
import asyncio
from app.sdk.client import WorkflowBuilder, WorkflowForge

async def main():
    builder = WorkflowBuilder("etl-pipeline", "Extract transform load")
    builder.add_task("extract", params={"url": "https://api.example.com/data"})
    builder.add_task("transform", dependencies=["extract"], params={"raw": "{extract.rows}"})
    builder.add_task("load", dependencies=["transform"], params={"clean": "{transform.clean}"})

    async with WorkflowForge("http://localhost:8000") as client:
        wf = await client.register_workflow("etl-pipeline", builder.build()["tasks"])
        run = await client.execute(wf["id"])
        final = await client.watch_execution(run["execution_id"])
        print(final["status"])

asyncio.run(main())
```

See `backend/examples/etl_pipeline.py` for a full runnable example.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | Health check |
| GET | /api/stats | System statistics |
| GET | /api/workflows | List workflows |
| POST | /api/workflows | Register workflow (validated) |
| GET | /api/workflows/{id} | Get workflow |
| PUT | /api/workflows/{id} | Update workflow (versioned) |
| DELETE | /api/workflows/{id} | Delete workflow |
| GET | /api/workflows/{id}/executions | List executions |
| GET | /api/workflows/{id}/versions | Version history |
| GET | /api/workflows/{id}/metrics | Success rate, avg duration |
| POST | /api/workflows/{id}/execute | Start execution |
| POST | /api/workflows/{id}/schedule | Cron schedule |
| GET | /api/workflows/{id}/schedules | List schedules |
| GET | /api/executions | List executions |
| GET | /api/executions/{id} | Get execution |
| GET | /api/executions/{id}/logs | Execution logs |
| POST | /api/executions/{id}/cancel | Cancel |
| POST | /api/executions/{id}/pause | Pause |
| POST | /api/executions/{id}/resume | Resume |
| WS | /ws | Real-time events + stats |

## Architecture

```
workflowforge/
├── backend/
│   ├── app/
│   │   ├── main.py          # lifespan: state, scheduler, notifications, WS bus
│   │   ├── api/             # workflows, executions, websocket
│   │   ├── core/            # engine, models, state_store, scheduler, notifications
│   │   └── sdk/             # builder + async client + watcher
│   ├── tests/               # engine + api tests
│   ├── examples/            # etl_pipeline demo
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/           # Dashboard, Workflows, WorkflowDetail, Executions, ExecutionDetail
│   │   ├── components/      # Layout with breadcrumbs + live stats
│   │   └── api/             # typed client
│   └── vite.config.ts
└── docker-compose.yml
```

## Tech Stack

- Backend: Python 3.12, FastAPI, asyncio, Pydantic, APScheduler, aiohttp
- Frontend: React 18, TypeScript, Vite, React Router
- Real-time: WebSocket
- Persistence: JSON file store with versioning
- Deployment: Docker Compose

## Running Tests

```bash
cd backend
pytest tests/ -v
```
