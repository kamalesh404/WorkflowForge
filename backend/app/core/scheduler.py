from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .models import WorkflowSchedule
from .state_store import state_store

logger = logging.getLogger(__name__)


async def run_scheduled_workflow(workflow_id: str) -> None:
    from .engine import engine

    workflow = await state_store.get_workflow(workflow_id)
    if workflow is None:
        logger.warning("Scheduled workflow %s no longer exists", workflow_id)
        return
    try:
        await engine.execute(workflow)
    except Exception:
        logger.exception("Scheduled execution of workflow %s failed", workflow_id)
    schedules = await state_store.list_schedules(workflow_id)
    for schedule in schedules:
        schedule.last_triggered_at = datetime.now(timezone.utc)
        await state_store.save_schedule(schedule)


class WorkflowScheduler:
    def __init__(self) -> None:
        self._scheduler: AsyncIOScheduler | None = None

    async def start(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._scheduler.start()

    async def stop(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    async def load_schedules(self) -> int:
        schedules = await state_store.list_schedules()
        count = 0
        for schedule in schedules:
            if schedule.enabled:
                self.add_schedule(schedule)
                count += 1
        return count

    def add_schedule(self, schedule: WorkflowSchedule) -> None:
        if self._scheduler is None:
            raise RuntimeError("Scheduler is not running")
        self._scheduler.add_job(
            run_scheduled_workflow,
            trigger=CronTrigger.from_crontab(schedule.cron),
            id=schedule.id,
            args=[schedule.workflow_id],
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    def remove_schedule(self, schedule_id: str) -> None:
        if self._scheduler is None:
            return
        try:
            self._scheduler.remove_job(schedule_id)
        except JobLookupError:
            pass


workflow_scheduler = WorkflowScheduler()
