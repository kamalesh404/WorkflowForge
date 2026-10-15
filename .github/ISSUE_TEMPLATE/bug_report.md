---
name: Bug report
about: Report a reproducible problem in WorkflowForge
title: "[BUG] "
labels: bug
assignees: ""
---

## Description

A clear and concise description of the bug.

## Reproduction steps

1.
2.
3.

Include minimal workflow JSON, API requests, or SDK snippet if applicable.

## Expected behavior

What you expected to happen.

## Logs

Paste relevant output from:

- Backend logs (`docker-compose logs backend` or uvicorn output)
- `GET /api/executions/{id}/logs`
- Browser console (for UI issues)

```text
paste logs here
```

## Environment

- WorkflowForge version / commit:
- Backend: Python 3.12 (`pip freeze` relevant lines):
- Frontend: Node version, npm version:
- Deployment: docker-compose / manual:
- OS / browser:
