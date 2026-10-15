# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-10-01

### Added

- DAG validation with cycle detection and missing-dependency checks before registration and execution.
- Context passing between tasks via `{task_id.field}` references for chained ETL outputs.
- Pause and resume controls for live executions alongside cancel and workflow-level plus per-task timeouts.
- Cron scheduling via APScheduler with list and delete endpoints for workflow schedules.
- Webhook notifications with HMAC signatures and SMTP failure alerts.
- Fluent Python SDK builder (`WorkflowBuilder`) with async client (`WorkflowForge`) and execution watcher that polls to completion.
- Execution metrics endpoints covering success rate and average duration.
- Paginated execution logs and workflow version history.
- Real-time WebSocket event bus with per-workflow subscriptions and live stats.
- React dashboard with DAG visualization, execution timeline, metrics view, and scheduling UI.

### Changed

- Standardized execution lifecycle states to `completed`, `failed`, and `cancelled` for SDK watchers and API consumers.
- Versioned workflow updates so `PUT /api/workflows/{id}` preserves history retrievable via versions endpoint.

### Fixed

- Skipped-dependency propagation so downstream tasks no longer hang when an upstream task fails.
- Automatic retries with exponential backoff for transient task failures.

## [1.0.0] - 2026-06-15

### Added

- Initial release of WorkflowForge as a self-hosted distributed workflow orchestration engine.
- FastAPI backend with workflow registration, execution, listing, and health and stats endpoints.
- Asyncio execution engine with topological parallel level execution.
- JSON file persistence for workflows, executions, and schedules.
- Docker Compose setup for backend and frontend.
- React frontend with workflow list, detail, executions, and execution detail pages.
- Typed frontend API client and Vite development proxy for `/api` to the backend.
