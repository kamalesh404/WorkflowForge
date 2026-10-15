# WorkflowForge

[![CI](https://github.com/kamalesh404/workflowforge/actions/workflows/ci.yml/badge.svg)](https://github.com/kamalesh404/workflowforge/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](backend/requirements.txt)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-009688.svg)](backend/requirements.txt)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](frontend/package.json)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Self-hosted distributed workflow orchestration engine. A lightweight Temporal / Airflow alternative you can run in one Docker command.

## Table of Contents

- [Problem Statement](#problem-statement)
- [Unique Solution](#unique-solution)
- [Features](#features)
- [Quick Start](#quick-start)
- [Python SDK](#python-sdk)
- [API Reference](#api-reference)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Tests](#tests)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Problem Statement

Enterprise teams lose 40+ hours weekly managing complex multi-step data pipelines, ETL jobs, and business workflows that are fragile, hard to debug, and have zero visibility into execution state. Existing tools are either too heavy to operate (Airflow, Temporal) or too limited to scale (cron plus scripts).

The result is missed SLAs, silent failures, unversioned workflow definitions, and no unified view of runs, logs, schedules, and metrics.

## Unique Solution

WorkflowForge provides production orchestration primitives without the operational burden:

- DAG engine with cycle detection, missing-dependency validation, and parallel level execution.
- Context passing between tasks via `{task_id.field}` references, so ETL stages chain typed outputs.
- Pause, resume, and cancel on live executions, plus workflow-level timeouts and per-task timeouts.
- Automatic retries with exponential backoff and skipped-dependency propagation.
- JSON file persistence with versioning, execution history, paginated logs, and metrics.
- Cron scheduling via APScheduler, webhook notifications with HMAC signatures, and SMTP failure alerts.
- Real-time WebSocket event bus with per-workflow subscriptions.
- Fluent Python SDK with builder pattern and execution watcher that polls to completion.
- React dashboard with DAG visualization, execution timeline, metrics, and scheduling UI.

## Features

| Area | Capability |
| ---- | ---------- |
| DAG engine | Cycle detection, missing-dependency validation, topological parallel execution |
| Task chaining | Context passing with `{task_id.field}` references |
| Execution control | Pause, resume, cancel, workflow and per-task timeouts |
| Reliability | Retries with exponential backoff, skipped-dependency propagation |
| Persistence | JSON file store, workflow versioning, execution history |
| Observability | Paginated logs, success rate and avg duration metrics, WebSocket live events |
| Scheduling | Cron schedules via APScheduler, list and delete schedule endpoints |
| Notifications | Webhooks with HMAC signatures, SMTP failure alerts |
| SDK | `WorkflowBuilder`, async `WorkflowForge` client, `watch_execution` poller, `task` decorator |
| Dashboard | Workflows, WorkflowDetail, Executions, ExecutionDetail, DAG view, metrics, scheduling UI |
| Deployment | Docker Compose one-command setup, Vite dev proxy for `/api` |

## Quick Start

### Docker

```bash
docker-compose up
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

The Compose stack builds `backend` from `./backend` and runs the frontend on `node:20-alpine` with `/app` mounted from `./frontend`.

### Manual setup

Backend (Python 3.12):

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (Node 20):

```bash
cd frontend
npm ci
npm run dev
```

The Vite dev server runs on port 3000 and proxies `/api` to `http://localhost:8000`.

## Python SDK

The SDK lives in `backend/app/sdk/client.py` and works against the running API.

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

Additional client methods cover `get_workflow`, `update_workflow`, `list_workflows`, `list_executions`, `get_execution`, `get_logs`, `get_metrics`, `schedule`, `pause`, `resume`, `cancel`, and `get_stats`.

See `backend/examples/etl_pipeline.py` for a full runnable example.

## API Reference

Base URL: `http://localhost:8000`. Routers are mounted under `/api/workflows`, `/api/executions`, and `/ws`.

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | /api/health | Health check |
| GET | /api/stats | System statistics |
| GET | /api/workflows | List workflows |
| POST | /api/workflows | Register workflow (validated) |
| GET | /api/workflows/{workflow_id} | Get workflow |
| PUT | /api/workflows/{workflow_id} | Update workflow (versioned) |
| DELETE | /api/workflows/{workflow_id} | Delete workflow |
| GET | /api/workflows/{workflow_id}/executions | List executions for a workflow |
| GET | /api/workflows/{workflow_id}/versions | Version history |
| GET | /api/workflows/{workflow_id}/metrics | Success rate, avg duration |
| POST | /api/workflows/{workflow_id}/execute | Start execution (202 Accepted) |
| POST | /api/workflows/{workflow_id}/schedule | Create cron schedule |
| GET | /api/workflows/{workflow_id}/schedules | List schedules |
| DELETE | /api/workflows/schedules/{schedule_id} | Delete schedule |
| GET | /api/executions | List executions (filterable by `workflow_id`) |
| GET | /api/executions/{execution_id} | Get execution |
| GET | /api/executions/{execution_id}/logs | Paginated execution logs |
| POST | /api/executions/{execution_id}/cancel | Cancel execution |
| POST | /api/executions/{execution_id}/pause | Pause execution |
| POST | /api/executions/{execution_id}/resume | Resume execution |
| WS | /ws | Real-time events and stats |

Interactive docs are available at `/docs` when the backend is running.

## Architecture

```text
workflowforge/
├── backend/
│   ├── app/
│   │   ├── main.py          # lifespan: state, scheduler, notifications, WS bus
│   │   ├── api/             # workflows, executions, websocket
│   │   ├── core/            # engine, models, state_store, scheduler, notifications
│   │   └── sdk/             # builder + async client + watcher
│   ├── tests/               # engine + api tests
│   ├── examples/            # etl_pipeline demo
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/           # Dashboard, Workflows, WorkflowDetail, Executions, ExecutionDetail
│   │   ├── components/      # Layout with breadcrumbs + live stats
│   │   └── api/             # typed client
│   ├── vite.config.ts       # dev proxy for /api
│   └── package.json
└── docker-compose.yml
```

Request flow: React dashboard and SDK call FastAPI routes, the engine validates the DAG and executes levels in parallel with asyncio, state is persisted to the JSON store with version snapshots, and `dispatch_event` fans out to the WebSocket manager and notification manager. APScheduler loads persisted cron schedules on startup.

## Tech Stack

- Backend: Python 3.12, FastAPI 0.115.6, asyncio, Pydantic 2.10.4, APScheduler 3.11.0, aiohttp 3.11.11, httpx 0.28.1, websockets 14.1
- Frontend: React 18.3, TypeScript 5.6, Vite 5.4, React Router 6.28
- Real-time: WebSocket event bus with per-workflow subscriptions
- Persistence: JSON file store with versioning
- Deployment: Docker Compose (backend build plus Node 20 frontend)
- CI: GitHub Actions with Python 3.12 and Node 20 jobs

## Tests

Backend:

```bash
cd backend
pytest tests/ -v
```

Frontend typecheck and build:

```bash
cd frontend
npm ci
npx tsc -b
npm run build
```

CI runs `compileall` plus `pytest` for the backend and `tsc -b` plus `vite build` for the frontend on push and pull requests to `main` and `master`.

## Roadmap

- Postgres backend as an alternative to the JSON file store
- Task queue workers for multi-node execution
- API tokens and role-based access control
- Snowflake-style execution search and filtering in the dashboard
- Exportable audit trail for executions and schedule changes
- Official SDK packaging on PyPI

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md). Open issues with the bug report or feature request templates and submit PRs against `main` using Conventional Commits.

## License

Distributed under the MIT License. See [LICENSE](LICENSE).
