# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | Supported          |
| 1.0.x   | Supported for critical fixes |
| < 1.0   | Not supported      |

We recommend running the latest 2.0.x release. Only the backend API, execution engine, scheduler, notification subsystem, and the React frontend shipped in this repository are covered by this policy.

## Scope

In scope:

- `backend/` including FastAPI routes under `/api/workflows`, `/api/executions`, `/api/health`, `/api/stats`, and the WebSocket endpoint `/ws`
- Execution engine, state store, APScheduler integration, webhook and SMTP notifications
- `frontend/` React dashboard and its API client
- `docker-compose.yml` default deployment configuration

Out of scope:

- Third-party dependencies, hosting infrastructure, or forked deployments
- Social engineering, physical attacks, or denial-of-service volume testing

## Reporting a Vulnerability

Email kamaleshorbit@gmail.com with:

- A description of the vulnerability and affected component or endpoint
- Steps to reproduce, including minimal workflow definition or request samples
- Affected version or commit hash
- Any logs or proof of concept (redact secrets)
- Your contact details for follow-up

Please encrypt sensitive attachments if possible and do not open a public issue for unpatched vulnerabilities.

You will receive an acknowledgment within 3 business days and a triage update within 14 days.

## Disclosure Policy

- We follow coordinated disclosure with a 90-day disclosure window from the initial report.
- We will work with you on a fix and credit reporters who follow this policy, unless anonymity is requested.
- If a fix cannot be shipped within 90 days, we will agree a revised timeline with you before any public disclosure.
- Public disclosure before a fix is available should only occur by mutual agreement.

## Severity and Remediation

We assess reports using impact and exploitability. Critical authentication bypass, remote code execution, or data-loss issues in supported versions receive priority patches and a CHANGELOG entry. Lower-severity issues are scheduled into the next minor release.

Thank you for helping keep WorkflowForge and its users safe.
