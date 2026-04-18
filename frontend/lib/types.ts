export type RunStatus =
  | 'running'
  | 'sleeping'
  | 'paused'
  | 'interrupted'
  | 'completed'
  | 'terminated';

export interface Supervisor {
  id: string;
  name: string;
  base_instruction: string;
  available_actions: string[];
  wake_aggressiveness: 'low' | 'medium' | 'high';
  default_wake_interval_minutes: number;
  model: string;
  created_at: string;
}

export interface FinalSummary {
  summary: string;
  actions_taken: string[];
  key_learnings: string[];
  recommendations: string[];
}

export interface ActivityLogEntry {
  id: string;
  run_id: string;
  entry_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface Run {
  id: string;
  supervisor_id: string;
  supervisor_name?: string | null;
  order_id: string;
  status: RunStatus;
  current_state: Record<string, unknown>;
  extra_instructions: string[];
  next_wake_at?: string | null;
  started_at: string;
  completed_at?: string | null;
  final_summary?: FinalSummary | null;
  created_at: string;
}

export interface RunDetail extends Run {
  activity_log: ActivityLogEntry[];
}
