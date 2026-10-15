from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import smtplib
from email.message import EmailMessage
from typing import Any

import aiohttp

from .models import WebhookConfig
from .state_store import state_store

logger = logging.getLogger(__name__)

EVENT_STARTED = "execution_started"
EVENT_COMPLETED = "execution_completed"
EVENT_FAILED = "execution_failed"
EVENT_CANCELLED = "execution_cancelled"
EVENT_TASK_STARTED = "task_started"
EVENT_TASK_COMPLETED = "task_completed"
EVENT_TASK_FAILED = "task_failed"

ALL_EVENTS = (
    EVENT_STARTED,
    EVENT_COMPLETED,
    EVENT_FAILED,
    EVENT_CANCELLED,
    EVENT_TASK_STARTED,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_FAILED,
)

DEFAULT_WEBHOOK_EVENTS = [EVENT_COMPLETED, EVENT_FAILED]


class NotificationRulesEngine:
    def __init__(self) -> None:
        self._rules: list[dict[str, Any]] = []

    def add_rule(
        self, name: str, event: str, actions: list[str] | None = None
    ) -> None:
        self._rules.append(
            {
                "name": name,
                "event": event,
                "actions": actions or ["webhook"],
            }
        )

    def remove_rule(self, name: str) -> bool:
        for rule in list(self._rules):
            if rule["name"] == name:
                self._rules.remove(rule)
                return True
        return False

    def evaluate(self, event_type: str, payload: dict[str, Any]) -> list[str]:
        matched = []
        for rule in self._rules:
            if rule["event"] in (event_type, "*"):
                matched.append(rule["name"])
        return matched

    def rules(self) -> list[dict[str, Any]]:
        return list(self._rules)


class NotificationManager:
    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._smtp_config: dict[str, Any] = {}
        self.rules_engine = NotificationRulesEngine()

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()

    async def stop(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    def configure_smtp(
        self,
        host: str = "localhost",
        port: int = 25,
        username: str | None = None,
        password: str | None = None,
        from_addr: str = "workflowforge@localhost",
        to_addrs: list[str] | None = None,
        use_tls: bool = False,
    ) -> None:
        self._smtp_config = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "from": from_addr,
            "to_addrs": to_addrs or [],
            "use_tls": use_tls,
        }

    async def register_webhook(
        self,
        url: str,
        events: list[str] | None = None,
        secret: str | None = None,
        workflow_id: str | None = None,
    ) -> WebhookConfig:
        webhook = WebhookConfig(
            url=url,
            events=events or DEFAULT_WEBHOOK_EVENTS,
            secret=secret,
            workflow_id=workflow_id,
        )
        await state_store.save_webhook(webhook)
        return webhook

    async def remove_webhook(self, webhook_id: str) -> bool:
        return await state_store.delete_webhook(webhook_id)

    async def notify(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        results: dict[str, Any] = {"webhooks": {}, "rules": [], "email": False}
        results["rules"] = self.rules_engine.evaluate(event_type, payload)

        webhooks = await self._matching_webhooks(
            event_type, payload.get("workflow_id")
        )
        for webhook in webhooks:
            results["webhooks"][webhook.id] = await self._send_webhook(
                webhook, event_type, payload
            )

        if event_type == EVENT_FAILED and self._smtp_config:
            execution = await state_store.get_execution(payload.get("execution_id", ""))
            subject = f"WorkflowForge: execution {payload.get('execution_id')} failed"
            body = (
                f"Workflow: {payload.get('workflow_name')}\n"
                f"Execution: {payload.get('execution_id')}\n"
                f"Error: {payload.get('error') or (execution.error if execution else 'unknown')}\n"
            )
            results["email"] = await self.send_email(subject, body)

        return results

    async def _matching_webhooks(
        self, event_type: str, workflow_id: str | None
    ) -> list[WebhookConfig]:
        webhooks = await state_store.list_webhooks(enabled=True)
        return [
            webhook
            for webhook in webhooks
            if event_type in webhook.events
            and (webhook.workflow_id is None or webhook.workflow_id == workflow_id)
        ]

    async def _send_webhook(
        self, webhook: WebhookConfig, event_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        if self._session is None:
            return {"ok": False, "error": "Notification manager not started"}
        execution = await state_store.get_execution(payload.get("execution_id", ""))
        body = {
            "event": event_type,
            "execution_id": payload.get("execution_id"),
            "workflow_id": payload.get("workflow_id"),
            "workflow_name": payload.get("workflow_name"),
            "status": payload.get("status"),
            "timestamp": payload.get("timestamp"),
            "execution": execution.model_dump(mode="json") if execution else None,
        }
        raw = json.dumps(body, default=str).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-WorkflowForge-Event": event_type,
        }
        if webhook.secret:
            signature = hmac.new(
                webhook.secret.encode("utf-8"), raw, hashlib.sha256
            ).hexdigest()
            headers["X-WorkflowForge-Signature"] = f"sha256={signature}"
        try:
            async with self._session.post(
                webhook.url,
                data=raw,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                return {"status": response.status, "ok": response.status < 400}
        except Exception as exc:
            logger.warning("Webhook delivery to %s failed: %s", webhook.url, exc)
            return {"status": 0, "ok": False, "error": str(exc)}

    async def send_email(
        self, subject: str, body: str, to_addrs: list[str] | None = None
    ) -> bool:
        if not self._smtp_config:
            return False
        return await asyncio.to_thread(self._smtp_send, subject, body, to_addrs)

    def _smtp_send(
        self, subject: str, body: str, to_addrs: list[str] | None
    ) -> bool:
        config = self._smtp_config
        recipients = to_addrs or config.get("to_addrs") or []
        if not recipients:
            return False
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = config["from"]
        message["To"] = ", ".join(recipients)
        message.set_content(body)
        try:
            if config.get("use_tls"):
                server: smtplib.SMTP = smtplib.SMTP_SSL(
                    config["host"], config["port"]
                )
            else:
                server = smtplib.SMTP(config["host"], config["port"])
            with server:
                if config.get("username"):
                    server.login(config["username"], config["password"])
                server.send_message(message)
            return True
        except Exception as exc:
            logger.error("SMTP delivery failed: %s", exc)
            return False


notification_manager = NotificationManager()
