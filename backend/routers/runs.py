"""Run lifecycle endpoints."""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.runner import generate_final_summary, run_agent, run_classifier
from backend.db.database import get_db
from backend.models import (
    ActivityLogEntry,
    EventInject,
    InstructionAdd,
    RunCreate,
    RunDetailResponse,
    RunResponse,
)

router = APIRouter(prefix="/api/runs", tags=["runs"])


# ---------------------------------------------------------------------------
# Row-mapping helpers
# ---------------------------------------------------------------------------


def _row_to_run(row, supervisor_name: str | None = None) -> RunResponse:
    return RunResponse(
        id=row.id,
        supervisor_id=row.supervisor_id,
        supervisor_name=supervisor_name or getattr(row, "supervisor_name", None),
        order_id=row.order_id,
        status=row.status,
        current_state=row.current_state if isinstance(row.current_state, dict) else {},
        extra_instructions=list(row.extra_instructions or []),
        next_wake_at=row.next_wake_at,
        started_at=row.started_at,
        completed_at=row.completed_at,
        final_summary=row.final_summary if isinstance(row.final_summary, dict) else None,
        created_at=row.created_at,
    )


def _row_to_log_entry(row) -> ActivityLogEntry:
    return ActivityLogEntry(
        id=row.id,
        run_id=row.run_id,
        entry_type=row.entry_type,
        payload=row.payload if isinstance(row.payload, dict) else {},
        created_at=row.created_at,
    )


# ---------------------------------------------------------------------------
# Shared DB helpers
# ---------------------------------------------------------------------------


async def _get_run_or_404(db: AsyncSession, run_id: UUID):
    result = await db.execute(
        text("""
            SELECT r.*, s.name AS supervisor_name
            FROM runs r
            JOIN supervisors s ON r.supervisor_id = s.id
            WHERE r.id = :id
        """),
        {"id": str(run_id)},
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return row


async def _log_entry(
    db: AsyncSession,
    run_id: str,
    entry_type: str,
    payload: dict,
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


async def _set_run_status(db: AsyncSession, run_id: str, status: str) -> None:
    extra: dict = {}
    if status in ("completed", "terminated"):
        extra["completed_at"] = True  # sentinel; handled below
    await db.execute(
        text("""
            UPDATE runs
            SET    status       = :status,
                   completed_at = CASE
                                    WHEN :mark_complete THEN NOW()
                                    ELSE completed_at
                                  END
            WHERE  id = :id
        """),
        {
            "id": run_id,
            "status": status,
            "mark_complete": status in ("completed", "terminated"),
        },
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(
    body: RunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create a new run, emit run_start event, then trigger the agent."""
    # 1. Insert run record
    result = await db.execute(
        text("""
            INSERT INTO runs (supervisor_id, order_id, current_state, status)
            VALUES (:supervisor_id, :order_id, :current_state, 'running')
            RETURNING *
        """),
        {
            "supervisor_id": str(body.supervisor_id),
            "order_id": body.order_id,
            "current_state": json.dumps(body.initial_context),
        },
    )
    run_row = result.fetchone()
    run_id = str(run_row.id)

    # 2. Log run_start as the first event
    await _log_entry(
        db,
        run_id,
        "event_received",
        {"event_type": "run_start", **body.initial_context},
    )

    await db.commit()

    # 3. Fire agent in background — response goes out immediately
    background_tasks.add_task(run_agent, run_id)

    # Re-query to get supervisor_name via JOIN
    run_detail = await _get_run_or_404(db, run_row.id)
    return _row_to_run(run_detail)


@router.get("", response_model=list[RunResponse])
async def list_runs(db: AsyncSession = Depends(get_db)):
    """List all runs, newest first, with supervisor name."""
    result = await db.execute(
        text("""
            SELECT r.*, s.name AS supervisor_name
            FROM   runs r
            JOIN   supervisors s ON r.supervisor_id = s.id
            ORDER  BY r.created_at DESC
        """)
    )
    return [_row_to_run(row) for row in result.fetchall()]


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """Full run detail including all activity log entries (oldest first)."""
    run_row = await _get_run_or_404(db, run_id)

    log_result = await db.execute(
        text("""
            SELECT * FROM activity_log
            WHERE  run_id = :run_id
            ORDER  BY created_at ASC
        """),
        {"run_id": str(run_id)},
    )
    log_entries = [_row_to_log_entry(r) for r in log_result.fetchall()]

    return RunDetailResponse(
        **_row_to_run(run_row).model_dump(),
        activity_log=log_entries,
    )


@router.post("/{run_id}/events", status_code=202)
async def inject_event(
    run_id: UUID,
    body: EventInject,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Inject an external event into a run; classifier decides whether to wake agent."""
    await _get_run_or_404(db, run_id)  # 404 guard

    payload = {"event_type": body.event_type, **body.payload}
    await _log_entry(db, str(run_id), "event_received", payload)
    await db.commit()

    background_tasks.add_task(run_classifier, str(run_id), payload)
    return Response(status_code=202)


@router.post("/{run_id}/instructions", status_code=200)
async def add_instruction(
    run_id: UUID,
    body: InstructionAdd,
    db: AsyncSession = Depends(get_db),
):
    """Append a human instruction to the run's extra_instructions list."""
    await _get_run_or_404(db, run_id)  # 404 guard

    await db.execute(
        text("""
            UPDATE runs
            SET    extra_instructions = array_append(extra_instructions, :instruction)
            WHERE  id = :id
        """),
        {"id": str(run_id), "instruction": body.instruction},
    )
    await _log_entry(
        db,
        str(run_id),
        "instruction_added",
        {"instruction": body.instruction},
    )
    await db.commit()
    return {"ok": True}


@router.post("/{run_id}/interrupt", status_code=200)
async def interrupt_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """Pause execution by setting status to 'interrupted'."""
    await _get_run_or_404(db, run_id)
    await _set_run_status(db, str(run_id), "interrupted")
    await _log_entry(db, str(run_id), "run_interrupted", {})
    await db.commit()
    return {"ok": True}


@router.post("/{run_id}/resume", status_code=200)
async def resume_run(
    run_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Resume an interrupted or paused run and trigger the agent."""
    await _get_run_or_404(db, run_id)
    await _set_run_status(db, str(run_id), "running")
    await _log_entry(db, str(run_id), "run_resumed", {})
    await db.commit()

    background_tasks.add_task(run_agent, str(run_id))
    return {"ok": True}


@router.post("/{run_id}/terminate", status_code=200)
async def terminate_run(
    run_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Terminate a run and kick off final summary generation."""
    await _get_run_or_404(db, run_id)
    await _set_run_status(db, str(run_id), "terminated")
    await _log_entry(db, str(run_id), "run_terminated", {})
    await db.commit()

    background_tasks.add_task(generate_final_summary, str(run_id))
    return {"ok": True}


@router.post("/{run_id}/pause", status_code=200)
async def pause_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """Pause a run without triggering any agent action."""
    await _get_run_or_404(db, run_id)
    await _set_run_status(db, str(run_id), "paused")
    await _log_entry(db, str(run_id), "run_paused", {})
    await db.commit()
    return {"ok": True}
