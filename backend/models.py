"""Pydantic request/response models for the order-supervisor API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------


class SupervisorCreate(BaseModel):
    name: str
    base_instruction: str
    available_actions: list[str] = Field(
        default=[
            "message_fulfillment_team",
            "message_payments_team",
            "message_logistics_team",
            "message_customer",
            "create_internal_note",
        ]
    )
    wake_aggressiveness: str = "medium"
    default_wake_interval_minutes: int = 120
    model: str = "gemini-2.5-flash"


class SupervisorResponse(BaseModel):
    id: uuid.UUID
    name: str
    base_instruction: str
    available_actions: list[str]
    wake_aggressiveness: str
    default_wake_interval_minutes: int
    model: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Activity log entry
# ---------------------------------------------------------------------------


class ActivityLogEntry(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    entry_type: str
    payload: dict[str, Any]
    created_at: datetime


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


class RunCreate(BaseModel):
    supervisor_id: uuid.UUID
    order_id: str
    initial_context: dict[str, Any] = {}


class RunResponse(BaseModel):
    id: uuid.UUID
    supervisor_id: uuid.UUID
    supervisor_name: str | None = None  # populated in list / detail queries
    order_id: str
    status: str
    current_state: dict[str, Any]
    extra_instructions: list[str]
    next_wake_at: datetime | None
    started_at: datetime
    completed_at: datetime | None
    final_summary: dict[str, Any] | None
    created_at: datetime


class RunDetailResponse(RunResponse):
    activity_log: list[ActivityLogEntry] = []


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


class EventInject(BaseModel):
    event_type: str
    payload: dict[str, Any] = {}


class InstructionAdd(BaseModel):
    instruction: str


class RunStatusUpdate(BaseModel):
    status: str
