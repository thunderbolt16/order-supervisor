"""Gemini tool definitions in Anthropic tool-use format."""

from __future__ import annotations

TOOLS: list[dict] = [
    # ------------------------------------------------------------------
    # Business-action tools (logged to activity_log)
    # ------------------------------------------------------------------
    {
        "name": "message_fulfillment_team",
        "description": (
            "Send a message to the fulfillment team about an issue or update "
            "related to this order (e.g. packing errors, warehouse holds)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to send to the fulfillment team.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Priority level of the message.",
                },
            },
            "required": ["message", "priority"],
        },
    },
    {
        "name": "message_payments_team",
        "description": (
            "Send a message to the payments team about a payment issue "
            "(e.g. failed charge, refund request, fraud flag)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to send to the payments team.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Priority level of the message.",
                },
            },
            "required": ["message", "priority"],
        },
    },
    {
        "name": "message_logistics_team",
        "description": (
            "Send a message to the logistics / shipping team about a delivery issue "
            "(e.g. carrier delay, wrong address, failed delivery attempt)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to send to the logistics team.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Priority level of the message.",
                },
            },
            "required": ["message", "priority"],
        },
    },
    {
        "name": "message_customer",
        "description": (
            "Send a proactive update or response to the customer about their order status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to send to the customer.",
                },
                "channel": {
                    "type": "string",
                    "enum": ["email", "sms", "push", "in_app"],
                    "description": "Communication channel to use.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Priority level of the message.",
                },
            },
            "required": ["message", "channel", "priority"],
        },
    },
    {
        "name": "create_internal_note",
        "description": (
            "Create an internal note visible to operations staff. "
            "Use this to document reasoning, flag edge cases, or leave context for humans."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "note": {
                    "type": "string",
                    "description": "The content of the internal note.",
                },
                "category": {
                    "type": "string",
                    "enum": [
                        "observation",
                        "decision",
                        "escalation",
                        "risk_flag",
                        "other",
                    ],
                    "description": "Category that best describes the note.",
                },
            },
            "required": ["note", "category"],
        },
    },
    # ------------------------------------------------------------------
    # Agent lifecycle tools
    # ------------------------------------------------------------------
    {
        "name": "set_sleep",
        "description": (
            "Put the supervisor to sleep for a specified duration. "
            "Call this when no immediate action is needed and you want to check back later. "
            "Calling this tool ends the current agent cycle."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "duration_minutes": {
                    "type": "integer",
                    "description": "How many minutes to sleep before the next wake.",
                    "minimum": 1,
                    "maximum": 1440,
                },
                "reason": {
                    "type": "string",
                    "description": "Brief reason for sleeping (shown in the activity log).",
                },
            },
            "required": ["duration_minutes", "reason"],
        },
    },
    {
        "name": "update_state",
        "description": (
            "Merge key-value pairs into the run's persistent current_state. "
            "Use this to track order progress, flags, or any information you need "
            "to remember across wake cycles."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "state_updates": {
                    "type": "object",
                    "description": (
                        "A dict of key-value pairs to merge into current_state. "
                        "Existing keys are overwritten; unmentioned keys are preserved."
                    ),
                },
            },
            "required": ["state_updates"],
        },
    },
]

# Lookup for mapping tool names to activity_log entry_type
TOOL_ENTRY_TYPE: dict[str, str] = {
    "message_fulfillment_team": "action_message_fulfillment_team",
    "message_payments_team": "action_message_payments_team",
    "message_logistics_team": "action_message_logistics_team",
    "message_customer": "action_message_customer",
    "create_internal_note": "action_create_internal_note",
}
