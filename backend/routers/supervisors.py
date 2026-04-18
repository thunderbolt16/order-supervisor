"""Supervisor CRUD endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.models import SupervisorCreate, SupervisorResponse

router = APIRouter(prefix="/api/supervisors", tags=["supervisors"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_supervisor(row) -> SupervisorResponse:
    return SupervisorResponse(
        id=row.id,
        name=row.name,
        base_instruction=row.base_instruction,
        available_actions=list(row.available_actions),
        wake_aggressiveness=row.wake_aggressiveness,
        default_wake_interval_minutes=row.default_wake_interval_minutes,
        model=row.model,
        created_at=row.created_at,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=SupervisorResponse, status_code=201)
async def create_supervisor(
    body: SupervisorCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("""
            INSERT INTO supervisors
                (name, base_instruction, available_actions,
                 wake_aggressiveness, default_wake_interval_minutes, model)
            VALUES
                (:name, :base_instruction, :available_actions,
                 :wake_aggressiveness, :default_wake_interval_minutes, :model)
            RETURNING *
        """),
        {
            "name": body.name,
            "base_instruction": body.base_instruction,
            "available_actions": body.available_actions,
            "wake_aggressiveness": body.wake_aggressiveness,
            "default_wake_interval_minutes": body.default_wake_interval_minutes,
            "model": body.model,
        },
    )
    return _row_to_supervisor(result.fetchone())


@router.get("", response_model=list[SupervisorResponse])
async def list_supervisors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM supervisors ORDER BY created_at DESC")
    )
    return [_row_to_supervisor(row) for row in result.fetchall()]


@router.get("/{supervisor_id}", response_model=SupervisorResponse)
async def get_supervisor(
    supervisor_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("SELECT * FROM supervisors WHERE id = :id"),
        {"id": str(supervisor_id)},
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    return _row_to_supervisor(row)
