"""Thin adapter layer called by FastAPI BackgroundTasks.

Routers import from here so they stay decoupled from the runtime internals.
"""

from __future__ import annotations

import logging

from backend.agent.runtime import complete_run, run_agent_cycle

logger = logging.getLogger(__name__)


async def run_agent(run_id: str) -> None:
    """Wake the supervisor agent for a run (called on run creation or resume)."""
    logger.info("run_agent triggered  run_id=%s  trigger=api_call", run_id)
    await run_agent_cycle(run_id, trigger="api_call")


async def run_classifier(run_id: str, event_payload: dict) -> None:
    """Classify an incoming event; wake the agent if warranted."""
    from backend.agent.classifier import classify_event
    from backend.db.database import AsyncSessionLocal
    from sqlalchemy import text

    logger.info("run_classifier triggered  run_id=%s", run_id)

    # Load the run + supervisor for classification context
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("""
                SELECT r.id, r.status, r.current_state, r.order_id,
                       s.wake_aggressiveness, s.name AS supervisor_name
                FROM   runs r
                JOIN   supervisors s ON r.supervisor_id = s.id
                WHERE  r.id = :id
            """),
            {"id": run_id},
        )
        row = result.fetchone()

    if row is None:
        logger.error("run_classifier: run_id=%s not found", run_id)
        return

    run_dict = {
        "id": str(row.id),
        "status": row.status,
        "current_state": row.current_state if isinstance(row.current_state, dict) else {},
        "order_id": row.order_id,
    }
    supervisor_dict = {
        "wake_aggressiveness": row.wake_aggressiveness,
        "name": row.supervisor_name,
    }

    decision = await classify_event(run_dict, event_payload, supervisor_dict)
    logger.info(
        "Classifier decision  run_id=%s  should_wake=%s  urgency=%s  reason=%s",
        run_id,
        decision.get("should_wake"),
        decision.get("urgency"),
        decision.get("reason"),
    )

    # Log the classifier decision to activity_log
    from backend.agent.runtime import _log_entry, _session_scope
    import json

    async with _session_scope() as db:
        await _log_entry(db, run_id, "classifier_decision", decision)
        await db.commit()

    if decision.get("should_wake"):
        await run_agent_cycle(run_id, trigger=f"event:{event_payload.get('event_type', 'unknown')}")


async def generate_final_summary(run_id: str) -> None:
    """Generate and store a final_summary for a terminated run without changing its status."""
    logger.info("generate_final_summary triggered  run_id=%s", run_id)
    import json

    from google import genai
    from google.genai import types
    from backend.agent.runtime import _format_log_entries, _log_entry, _session_scope
    from backend.config import settings
    from sqlalchemy import text

    async with _session_scope() as db:
        result = await db.execute(
            text("""
                SELECT entry_type, payload, created_at
                FROM   activity_log
                WHERE  run_id = :run_id
                ORDER  BY created_at ASC
            """),
            {"run_id": run_id},
        )
        entries = result.fetchall()
        activity_text = _format_log_entries(entries)

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        summary_prompt = (
            "You are reviewing a terminated order supervision run. "
            "Based on the activity log below, produce a JSON summary.\n\n"
            "Return ONLY valid JSON:\n"
            '{"summary": "string", "actions_taken": ["..."], '
            '"key_learnings": ["..."], "recommendations": ["..."]}\n\n'
            f"Activity log:\n{activity_text}"
        )
        try:
            response = await client.aio.models.generate_content(
                model=settings.MAIN_AGENT_MODEL,
                contents=summary_prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=1024,
                    response_mime_type="application/json"
                )
            )
            raw = response.text.strip()
            start, end = raw.find("{"), raw.rfind("}") + 1
            final_summary = json.loads(raw[start:end]) if start != -1 else {
                "summary": raw, "actions_taken": [], "key_learnings": [], "recommendations": [],
            }
        except Exception as exc:
            logger.error("generate_final_summary API error for %s: %s", run_id, exc)
            final_summary = {
                "summary": "Summary generation failed.",
                "actions_taken": [], "key_learnings": [], "recommendations": [],
            }

        await db.execute(
            text("UPDATE runs SET final_summary = CAST(:s AS jsonb) WHERE id = :id"),
            {"id": run_id, "s": json.dumps(final_summary)},
        )
        await _log_entry(db, run_id, "final_output", final_summary)
        await db.commit()
        logger.info("generate_final_summary complete  run_id=%s", run_id)
