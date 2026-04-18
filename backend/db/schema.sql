-- =============================================================================
-- order-supervisor schema
-- =============================================================================

-- Table 1: supervisor configurations (templates)
CREATE TABLE IF NOT EXISTS supervisors (
  id                            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name                          TEXT        NOT NULL,
  base_instruction              TEXT        NOT NULL,
  available_actions             TEXT[]      NOT NULL DEFAULT ARRAY[
    'message_fulfillment_team',
    'message_payments_team',
    'message_logistics_team',
    'message_customer',
    'create_internal_note'
  ],
  wake_aggressiveness           TEXT        NOT NULL DEFAULT 'medium'
                                  CHECK (wake_aggressiveness IN ('low', 'medium', 'high')),
  default_wake_interval_minutes INTEGER     NOT NULL DEFAULT 120,
  model                         TEXT        NOT NULL DEFAULT 'gemini-2.5-flash',
  created_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table 2: one run per order
CREATE TABLE IF NOT EXISTS runs (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  supervisor_id     UUID        NOT NULL REFERENCES supervisors(id),
  order_id          TEXT        NOT NULL,
  status            TEXT        NOT NULL DEFAULT 'running'
                      CHECK (status IN (
                        'running', 'sleeping', 'paused',
                        'interrupted', 'completed', 'terminated'
                      )),
  current_state     JSONB       NOT NULL DEFAULT '{}',
  extra_instructions TEXT[]     NOT NULL DEFAULT ARRAY[]::TEXT[],
  next_wake_at      TIMESTAMPTZ,
  started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at      TIMESTAMPTZ,
  final_summary     JSONB,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table 3: unified activity log — every event, action, decision in one place
CREATE TABLE IF NOT EXISTS activity_log (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id     UUID        NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  entry_type TEXT        NOT NULL CHECK (entry_type IN (
    'event_received',
    'classifier_decision',
    'agent_wake',
    'agent_sleep',
    'agent_reasoning',
    'action_message_fulfillment_team',
    'action_message_payments_team',
    'action_message_logistics_team',
    'action_message_customer',
    'action_create_internal_note',
    'instruction_added',
    'run_interrupted',
    'run_paused',
    'run_resumed',
    'run_terminated',
    'run_completed',
    'final_output'
  )),
  payload    JSONB       NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_activity_log_run_id
  ON activity_log(run_id);

CREATE INDEX IF NOT EXISTS idx_runs_status_wake
  ON runs(status, next_wake_at)
  WHERE status = 'sleeping';
