# WorkflowForge

A distributed workflow orchestration engine with a real-time monitoring dashboard. Define workflows as Python code, execute them with automatic retries and parallel task scheduling, and monitor everything from a live web UI.

## Features

- DAG-based task execution with dependency resolution
- Automatic retries with exponential backoff
- Parallel task execution for independent steps
- Real-time WebSocket monitoring
- REST API for full workflow lifecycle management
- Python SDK for defining workflows as code
- Docker Compose for one-command setup

## Quick Start

### Docker (recommended)

```bash
docker-compose up
```

Frontend: http://localhost:3000
Backend API: http://localhost:8000
API docs: http://localhost:8000/docs

### Manual Setup

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Python SDK

```python
import asyncio
from workflowforge import WorkflowForge

client = WorkflowForge("http://localhost:8000")

# Register tasks (in practice these are defined in your app)
tasks = [
    {
        "name": "fetch_data",
        "handler": my_fetch_function,
        "params": {"url": "https://api.example.com/data"},
        "retries": 3,
    },
    {
        "name": "process_data",
        "handler": my_process_function,
        "dependencies": ["fetch_data"],
    },
]

# Register and execute
wf = await client.register_workflow("etl-pipeline", tasks)
result = await client.execute(wf["id"])
print(f"Execution started: {result['execution_id']}")
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | Health check |
| GET | /api/stats | System statistics |
| GET | /api/workflows | List all workflows |
| POST | /api/workflows | Register a new workflow |
| GET | /api/workflows/{id} | Get workflow details |
| DELETE | /api/workflows/{id} | Delete a workflow |
| POST | /api/workflows/{id}/execute | Start execution |
| GET | /api/executions | List executions |
| GET | /api/executions/{id} | Get execution details |
| POST | /api/executions/{id}/cancel | Cancel execution |
| WS | /ws | Real-time stats stream |

## Architecture

```
workflowforge/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI application
│   │   ├── api/             # REST endpoints
│   │   ├── core/            # Engine, models, state
│   │   └── sdk/             # Python client library
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Layout, shared UI
│   │   ├── pages/           # Dashboard, Workflows, Executions
│   │   └── api/             # API client
│   ├── package.json
│   └── vite.config.ts
└── docker-compose.yml
```

## Tech Stack

- **Backend**: Python 3.12, FastAPI, asyncio, Pydantic
- **Frontend**: React 18, TypeScript, Vite
- **Real-time**: WebSocket (native)
- **Deployment**: Docker Compose
