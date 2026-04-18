"""Event triage classifier — fast call to a cheap model to decide whether to wake the agent."""

from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types

from backend.config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a triage classifier for an order management AI. "
    "Given an order run's current state and an incoming event, decide if the main "
    "supervisor agent should be woken immediately. "
    'Respond ONLY with valid JSON: {"should_wake": true/false, "reason": "brief reason", "urgency": "low/medium/high"}'
)

_DEFAULT_WAKE = {
    "should_wake": True,
    "reason": "classifier error — defaulting to wake",
    "urgency": "medium",
}


async def classify_event(run: dict, event: dict, supervisor: dict) -> dict:
    """Return a classification dict indicating whether the agent should be woken.

    Args:
        run:        Run record fields (status, current_state, order_id, …)
        event:      The incoming event payload (always includes event_type)
        supervisor: Supervisor config (wake_aggressiveness, …)

    Returns:
        {"should_wake": bool, "reason": str, "urgency": "low"|"medium"|"high"}
    """
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    user_message = (
        f"Run status: {run.get('status', 'unknown')}\n"
        f"Wake aggressiveness: {supervisor.get('wake_aggressiveness', 'medium')}\n"
        f"Current state:\n{json.dumps(run.get('current_state', {}), indent=2)}\n\n"
        f"Incoming event:\n"
        f"  Type: {event.get('event_type', 'unknown')}\n"
        f"  Payload:\n{json.dumps(event, indent=2)}"
    )

    try:
        response = await client.aio.models.generate_content(
            model=settings.CLASSIFIER_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                max_output_tokens=256,
                response_mime_type="application/json",
            )
        )
        raw = response.text.strip()
        # Be lenient: find the first {...} block in the response
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError(f"No JSON object found in classifier response: {raw!r}")
        result = json.loads(raw[start:end])
        # Ensure required keys are present
        result.setdefault("should_wake", True)
        result.setdefault("reason", "")
        result.setdefault("urgency", "medium")
        return result
    except Exception as exc:
        logger.error("classify_event failed (run_id=%s): %s", run.get("id"), exc)
        return dict(_DEFAULT_WAKE)
