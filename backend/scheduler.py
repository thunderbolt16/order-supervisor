"""APScheduler setup — polls sleeping runs and enforces the age limit."""

from __future__ import annotations

import logging
from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text

from backend.config import settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


# ---------------------------------------------------------------------------
# Scheduled job
# ---------------------------------------------------------------------------


async def poll_sleeping_runs() -> None:
    """Main scheduler tick:
    1. Wake every sleeping run whose next_wake_at has elapsed.
    2. Force-complete any run that has exceeded MAX_RUN_AGE_HOURS.
    """
    # Deferred imports to avoid circular references at module load
    from backend.agent.runtime import complete_run, run_agent_cycle
    from backend.db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # -- Runs to wake
        wake_result = await db.execute(
            text("""
                SELECT id
                FROM   runs
                WHERE  status       = 'sleeping'
                AND    next_wake_at <= NOW()
            """)
        )
        sleeping_ids = [str(r.id) for r in wake_result.fetchall()]

        # -- Runs that have exceeded the age limit (running or sleeping)
        aged_result = await db.execute(
            text("""
                SELECT id
                FROM   runs
                WHERE  status IN ('running', 'sleeping')
                AND    started_at < NOW() - (:hours * interval '1 hour')
            """),
            {"hours": settings.MAX_RUN_AGE_HOURS},
        )
        aged_ids = {str(r.id) for r in aged_result.fetchall()}

    if not sleeping_ids and not aged_ids:
        return

    logger.info(
        "Scheduler tick: %d run(s) to wake, %d run(s) aged out",
        len(sleeping_ids),
        len(aged_ids),
    )

    # Complete aged-out runs first so we don't also try to wake them
    for run_id in aged_ids:
        logger.info("Completing aged-out run  run_id=%s", run_id)
        try:
            await complete_run(run_id)
        except Exception as exc:
            logger.exception("complete_run failed for run_id=%s: %s", run_id, exc)

    # Wake sleeping runs that haven't been aged out
    for run_id in sleeping_ids:
        if run_id in aged_ids:
            continue  # already handled above
        logger.info("Scheduler waking run  run_id=%s", run_id)
        try:
            await run_agent_cycle(run_id, trigger="scheduled_wake")
        except Exception as exc:
            logger.exception("run_agent_cycle failed for run_id=%s: %s", run_id, exc)


# ---------------------------------------------------------------------------
# Lifecycle helpers called from main.py lifespan
# ---------------------------------------------------------------------------


def start_scheduler() -> None:
    """Create and start the AsyncIOScheduler."""
    global _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        poll_sleeping_runs,
        trigger="interval",
        seconds=settings.SCHEDULER_INTERVAL_SECONDS,
        id="poll_sleeping_runs",
        replace_existing=True,
        max_instances=1,  # never overlap; long agent cycles are expected
    )
    _scheduler.start()
    logger.info(
        "Scheduler started — polling every %ds  (age limit: %dh)",
        settings.SCHEDULER_INTERVAL_SECONDS,
        settings.MAX_RUN_AGE_HOURS,
    )


def stop_scheduler() -> None:
    """Gracefully stop the scheduler on app shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
