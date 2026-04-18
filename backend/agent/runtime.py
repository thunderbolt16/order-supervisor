"""Core agent loop — loads context, calls Gemini, processes tools, updates DB."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from google import genai
from google.genai import types
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.tools import TOOL_ENTRY_TYPE, TOOLS
from backend.config import settings
from backend.db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

MAX_AGENT_ITERATIONS = 10  # safety cap on the agentic loop

# Minimum interval (minutes) before retrying after an API error
_API_ERROR_SLEEP_MINUTES = 5


# ---------------------------------------------------------------------------
# Session scope helper
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _session_scope(db_session: AsyncSession | None = None):
    """Yield a session; create and close our own if one is not provided."""
    if db_session is not None:
        yield db_session
    else:
        async with AsyncSessionLocal() as db:
            yield db


# ---------------------------------------------------------------------------
# Low-level DB helpers
# ---------------------------------------------------------------------------


async def _log_entry(
    db: AsyncSession, run_id: str, entry_type: str, payload: dict
) -> None:
    await db.execute(
        text("""
            INSERT INTO activity_log (run_id, entry_type, payload)
            VALUES (:run_id, :entry_type, :payload)
        """),
        {
            "run_id": run_id,
            "entry_type": entry_type,
            "payload": json.dumps(payload),
        },
    )


async def _set_sleeping(
    db: AsyncSession, run_id: str, duration_minutes: int
) -> None:
    await db.execute(
        text("""
            UPDATE runs
            SET    status       = 'sleeping',
                   next_wake_at = NOW() + (:minutes * interval '1 minute')
            WHERE  id = :id
        """),
        {"id": run_id, "minutes": duration_minutes},
    )


async def _set_running(db: AsyncSession, run_id: str) -> None:
    await db.execute(
        text("UPDATE runs SET status = 'running' WHERE id = :id"),
        {"id": run_id},
    )


async def _merge_state(db: AsyncSession, run_id: str, updates: dict) -> None:
    await db.execute(
        text("""
            UPDATE runs
            SET current_state = current_state || CAST(:updates AS jsonb)
            WHERE id = :id
        """),
        {"id": run_id, "updates": json.dumps(updates)},
    )


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------


def _format_log_entries(entries: list) -> str:
    lines = []
    for e in entries:
        ts = e.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        payload_str = json.dumps(
            e.payload if isinstance(e.payload, dict) else {}, ensure_ascii=False
        )
        # Truncate very long payloads to keep the context manageable
        if len(payload_str) > 300:
            payload_str = payload_str[:297] + "…"
        lines.append(f"[{ts}] {e.entry_type}: {payload_str}")
    return "\n".join(lines) if lines else "(no prior activity)"


def _build_system_prompt(supervisor: Any, run: Any) -> str:
    parts = [supervisor.base_instruction]

    extra = list(run.extra_instructions or [])
    if extra:
        parts.append("\n\nAdditional operator instructions:")
        parts.extend(f"  {i+1}. {instr}" for i, instr in enumerate(extra))

    current_state = run.current_state if isinstance(run.current_state, dict) else {}
    parts.append(
        f"\n\nCurrent order state:\n{json.dumps(current_state, indent=2)}"
    )

    parts.append(
        "\n\nGuidelines:\n"
        "- Use set_sleep when no immediate action is needed.\n"
        "- Use update_state to persist key information across wake cycles.\n"
        "- Use create_internal_note to document your reasoning.\n"
        "- Only message teams or customers when there is a genuine, actionable reason.\n"
        "- Always call set_sleep or let the loop end naturally when done with a cycle."
    )

    return "\n".join(parts)


def _build_context_message(run: Any, trigger: str, log_entries: list) -> str:
    return (
        f"Order ID: {run.order_id}\n"
        f"Run trigger: {trigger}\n"
        f"Run started: {run.started_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"Recent activity (up to last 50 events):\n"
        f"{_format_log_entries(log_entries)}\n\n"
        "Review the activity above and take any necessary actions for this order."
    )


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------


async def _execute_tool(
    db: AsyncSession,
    run_id: str,
    name: str,
    inp: dict,
    supervisor: Any,
) -> tuple[str, bool]:
    """Execute a single tool call."""

    # -- Business actions -------------------------------------------------
    entry_type = TOOL_ENTRY_TYPE.get(name)
    if entry_type:
        await _log_entry(db, run_id, entry_type, inp)
        return f"Action '{name}' logged successfully.", False

    # -- update_state -----------------------------------------------------
    if name == "update_state":
        updates = inp.get("state_updates", {})
        if not isinstance(updates, dict):
            return "Error: state_updates must be an object.", False
        await _merge_state(db, run_id, updates)
        await _log_entry(
            db, run_id, "agent_reasoning",
            {"action": "update_state", "updates": updates},
        )
        return f"State updated with {list(updates.keys())}.", False

    # -- set_sleep --------------------------------------------------------
    if name == "set_sleep":
        duration: int = inp.get("duration_minutes", supervisor.default_wake_interval_minutes)
        reason: str = inp.get("reason", "agent requested sleep")
        await _set_sleeping(db, run_id, duration)
        await _log_entry(
            db, run_id, "agent_sleep",
            {"reason": reason, "duration_minutes": duration},
        )
        await db.commit()
        return f"Sleeping for {duration} minutes.", True  # signal: stop loop

    logger.warning("Unknown tool called: %s", name)
    return f"Unknown tool '{name}' — ignored.", False


# ---------------------------------------------------------------------------
# Terminal-state checks
# ---------------------------------------------------------------------------


async def _should_complete(
    run_id: str, run: Any, db: AsyncSession
) -> bool:
    """Return True if the run has reached a natural terminal condition.

    Checks (in order):
    1. Run age exceeded MAX_RUN_AGE_HOURS.
    2. Most recent event_received has event_type='delivered'.
    3. Refund flow complete: a 'refund_requested' event exists AND a
       'payment_confirmed' event occurred *after* it.
    """
    # ── 1. Age check ────────────────────────────────────────────────────
    age_limit = datetime.now(timezone.utc) - timedelta(hours=settings.MAX_RUN_AGE_HOURS)
    if run.started_at.replace(tzinfo=timezone.utc) < age_limit:
        logger.info("run_id=%s exceeded MAX_RUN_AGE_HOURS — completing.", run_id)
        return True

    # ── 2 & 3. Load all event_received entries, oldest first ────────────
    result = await db.execute(
        text("""
            SELECT payload, created_at
            FROM   activity_log
            WHERE  run_id     = :run_id
            AND    entry_type = 'event_received'
            ORDER  BY created_at ASC
        """),
        {"run_id": run_id},
    )
    rows = result.fetchall()
    if not rows:
        return False

    # ── 2. Delivered ────────────────────────────────────────────────────
    latest_payload = rows[-1].payload if isinstance(rows[-1].payload, dict) else {}
    if latest_payload.get("event_type") == "delivered":
        logger.info("run_id=%s 'delivered' event detected — completing.", run_id)
        return True

    # ── 3. Refund flow: refund_requested → payment_confirmed ────────────
    refund_requested_at = None
    for row in rows:
        payload = row.payload if isinstance(row.payload, dict) else {}
        et = payload.get("event_type")
        if et == "refund_requested":
            refund_requested_at = row.created_at
        elif (
            et == "payment_confirmed"
            and refund_requested_at is not None
            and row.created_at > refund_requested_at
        ):
            logger.info(
                "run_id=%s refund flow complete (refund_requested → payment_confirmed) — completing.",
                run_id,
            )
            return True

    return False


# ---------------------------------------------------------------------------
# complete_run
# ---------------------------------------------------------------------------


async def complete_run(run_id: str, db_session: AsyncSession | None = None) -> None:
    """Mark a run as completed and generate a structured final_summary via Gemini."""
    async with _session_scope(db_session) as db:
        # 1. Mark completed
        await db.execute(
            text("""
                UPDATE runs
                SET status       = 'completed',
                    completed_at = NOW()
                WHERE id = :id
                  AND status NOT IN ('completed', 'terminated')
            """),
            {"id": run_id},
        )
        await db.commit()

        # 2. Load full activity log for summarisation
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

        # 3. Ask Gemini for a structured summary
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        summary_prompt = (
            "You are reviewing a completed order supervision run. "
            "Based on the activity log below, produce a JSON summary.\n\n"
            "Return ONLY valid JSON matching this schema exactly:\n"
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
                "summary": raw,
                "actions_taken": [],
                "key_learnings": [],
                "recommendations": [],
            }
        except Exception as exc:
            logger.error("complete_run summary generation failed for %s: %s", run_id, exc)
            final_summary = {
                "summary": "Summary generation failed.",
                "actions_taken": [],
                "key_learnings": [],
                "recommendations": [],
            }

        # 4. Store final_summary
        await db.execute(
            text("UPDATE runs SET final_summary = CAST(:summary AS jsonb) WHERE id = :id"),
            {"id": run_id, "summary": json.dumps(final_summary)},
        )

        # 5. Log final_output
        await _log_entry(db, run_id, "final_output", final_summary)
        await db.commit()

        logger.info("run_id=%s completed. Summary stored.", run_id)


# ---------------------------------------------------------------------------
# Main agent cycle
# ---------------------------------------------------------------------------


async def run_agent_cycle(
    run_id: str,
    trigger: str,
    db_session: AsyncSession | None = None,
) -> None:
    """Load context, invoke the Gemini agentic loop, handle tools, update DB.

    Args:
        run_id:     UUID string of the run.
        trigger:    Human-readable reason for this wake (e.g. 'run_start').
        db_session: Optional existing session; a new one is created if None.
    """
    async with _session_scope(db_session) as db:
        try:
            await _agent_cycle_inner(run_id, trigger, db)
        except Exception as exc:
            logger.exception("Unhandled error in agent cycle for run_id=%s: %s", run_id, exc)
            try:
                await db.rollback()
                # Log the error so it's visible in the activity log
                await _log_entry(
                    db, run_id, "run_interrupted",
                    {"reason": "agent cycle error", "error": str(exc)},
                )
                await db.execute(
                    text("UPDATE runs SET status = 'interrupted' WHERE id = :id"),
                    {"id": run_id},
                )
                await db.commit()
            except Exception:
                pass


async def _agent_cycle_inner(run_id: str, trigger: str, db: AsyncSession) -> None:
    # ------------------------------------------------------------------ #
    # 1. Load run + supervisor + last 50 activity log entries
    # ------------------------------------------------------------------ #
    run_result = await db.execute(
        text("""
            SELECT r.*, s.base_instruction, s.available_actions,
                   s.wake_aggressiveness, s.default_wake_interval_minutes,
                   s.model AS supervisor_model
            FROM   runs r
            JOIN   supervisors s ON r.supervisor_id = s.id
            WHERE  r.id = :id
        """),
        {"id": run_id},
    )
    run_row = run_result.fetchone()
    if run_row is None:
        logger.error("run_agent_cycle: run_id=%s not found", run_id)
        return

    log_result = await db.execute(
        text("""
            SELECT entry_type, payload, created_at
            FROM   activity_log
            WHERE  run_id = :run_id
            ORDER  BY created_at DESC
            LIMIT  50
        """),
        {"run_id": run_id},
    )
    # Reverse so oldest-first for readability in the prompt
    log_entries = list(reversed(log_result.fetchall()))

    # ------------------------------------------------------------------ #
    # 2. Guard: don't run if in a terminal / paused state
    # ------------------------------------------------------------------ #
    if run_row.status in ("terminated", "completed", "paused"):
        logger.info(
            "run_id=%s is in status=%s — skipping agent cycle.",
            run_id, run_row.status,
        )
        return

    # ------------------------------------------------------------------ #
    # 3. Set status = running, log agent_wake
    # ------------------------------------------------------------------ #
    await _set_running(db, run_id)
    await _log_entry(db, run_id, "agent_wake", {"trigger": trigger})
    await db.commit()

    # ------------------------------------------------------------------ #
    # 4–5. Build prompts
    # ------------------------------------------------------------------ #
    system_prompt = _build_system_prompt(run_row, run_row)
    context_message = _build_context_message(run_row, trigger, log_entries)

    # ------------------------------------------------------------------ #
    # 6–7. Agentic loop
    # ------------------------------------------------------------------ #
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    model = run_row.supervisor_model or settings.MAIN_AGENT_MODEL

    from backend.agent.tools import TOOLS
    gemini_tools = [{"function_declarations": TOOLS}]
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=context_message)])
    ]

    for iteration in range(MAX_AGENT_ITERATIONS):
        logger.debug("run_id=%s  agent iteration=%d", run_id, iteration)

        # ── Gemini API call with error handling ───────────────────────
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=gemini_tools,
                    max_output_tokens=2048,
                )
            )
        except Exception as api_exc:
            logger.error(
                "Gemini API error  run_id=%s  iter=%d: %s",
                run_id, iteration, api_exc,
            )
            await _log_entry(
                db, run_id, "agent_reasoning",
                {
                    "error": str(api_exc),
                    "fallback": "agent cycle failed, will retry on next scheduled wake",
                },
            )
            await _set_sleeping(db, run_id, _API_ERROR_SLEEP_MINUTES)
            await db.commit()
            return  # abandon this cycle; scheduler will retry

        candidate = response.candidates[0] if response.candidates else None
        if not candidate or not candidate.content:
            text_part = response.text if hasattr(response, 'text') else ""
            if text_part:
               await _log_entry(db, run_id, "agent_reasoning", {"text": text_part, "iteration": iteration})
            
            duration = run_row.default_wake_interval_minutes
            await _set_sleeping(db, run_id, duration)
            await _log_entry(db, run_id, "agent_sleep", {"reason": "no candidate generated", "duration_minutes": duration})
            await db.commit()
            break
            
        model_content = candidate.content
        contents.append(model_content)

        text_blocks = [p.text for p in model_content.parts if p.text]
        tool_blocks = [p.function_call for p in model_content.parts if p.function_call]

        # Log any inline text as reasoning
        if text_blocks:
            reasoning_text = "\n".join(text_blocks)
            await _log_entry(
                db, run_id, "agent_reasoning",
                {"text": reasoning_text, "iteration": iteration},
            )

        # ---- 8. No tool calls → default sleep -------------------------
        if not tool_blocks:
            duration = run_row.default_wake_interval_minutes
            await _set_sleeping(db, run_id, duration)
            await _log_entry(
                db, run_id, "agent_sleep",
                {
                    "reason": "agent returned with no tool calls",
                    "duration_minutes": duration,
                    "iteration": iteration,
                },
            )
            await db.commit()
            break

        # ---- 7. Process each tool call --------------------------------
        tool_responses = []
        sleep_invoked = False

        for tool_call in tool_blocks:
            # Note: Gemini args is often empty if no params, or dict-like
            inp_args = {k: v for k, v in tool_call.args.items()} if getattr(tool_call, "args", None) else {}
            
            result_text, should_return = await _execute_tool(
                db, run_id, tool_call.name, inp_args, run_row
            )
            
            tool_responses.append(
                types.Part.from_function_response(
                    name=tool_call.name,
                    response={"result": result_text}
                )
            )
            
            if should_return:
                sleep_invoked = True
                break  # set_sleep stops further tool processing

        await db.commit()

        if sleep_invoked:
            return
            
        contents.append(types.Content(role="user", parts=tool_responses))
        
    else:
        # Safety: exceeded MAX_AGENT_ITERATIONS
        logger.warning("run_id=%s hit MAX_AGENT_ITERATIONS (%d)", run_id, MAX_AGENT_ITERATIONS)
        duration = run_row.default_wake_interval_minutes
        await _set_sleeping(db, run_id, duration)
        await _log_entry(
            db, run_id, "agent_sleep",
            {"reason": "max iterations reached", "duration_minutes": duration},
        )
        await db.commit()

    # ------------------------------------------------------------------ #
    # 9. Terminal-completion check (after every cycle that ends in sleep)
    # ------------------------------------------------------------------ #
    # Re-load run to get fresh status post-commit
    fresh = await db.execute(
        text("SELECT * FROM runs WHERE id = :id"), {"id": run_id}
    )
    fresh_run = fresh.fetchone()
    if fresh_run and await _should_complete(run_id, fresh_run, db):
        await complete_run(run_id, db)
