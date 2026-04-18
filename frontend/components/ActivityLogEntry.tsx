import type { ActivityLogEntry } from '@/lib/types';

/* ------------------------------------------------------------------ */
/* Entry-type → display config                                          */
/* ------------------------------------------------------------------ */

interface PillConfig {
  label: string;
  classes: string;
}

const PILL: Record<string, PillConfig> = {
  event_received:                   { label: 'Event',             classes: 'bg-blue-500/15   text-blue-300   ring-blue-500/25'   },
  classifier_decision:             { label: 'Classifier',         classes: 'bg-cyan-500/15   text-cyan-300   ring-cyan-500/25'   },
  agent_wake:                      { label: 'Agent Woke',         classes: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/25' },
  agent_sleep:                     { label: 'Agent Sleeping',     classes: 'bg-slate-500/15  text-slate-300  ring-slate-500/25'  },
  agent_reasoning:                 { label: 'Reasoning',          classes: 'bg-amber-500/15  text-amber-300  ring-amber-500/25'  },
  action_message_fulfillment_team: { label: 'Action: Fulfillment',classes: 'bg-violet-500/15 text-violet-300 ring-violet-500/25' },
  action_message_payments_team:    { label: 'Action: Payments',   classes: 'bg-violet-500/15 text-violet-300 ring-violet-500/25' },
  action_message_logistics_team:   { label: 'Action: Logistics',  classes: 'bg-violet-500/15 text-violet-300 ring-violet-500/25' },
  action_message_customer:         { label: 'Action: Customer',   classes: 'bg-violet-500/15 text-violet-300 ring-violet-500/25' },
  action_create_internal_note:     { label: 'Action: Note',       classes: 'bg-violet-500/15 text-violet-300 ring-violet-500/25' },
  instruction_added:               { label: 'Instruction Added',  classes: 'bg-teal-500/15   text-teal-300   ring-teal-500/25'   },
  run_interrupted:                 { label: 'Interrupted',        classes: 'bg-orange-500/15 text-orange-300 ring-orange-500/25' },
  run_paused:                      { label: 'Paused',             classes: 'bg-slate-500/15  text-slate-300  ring-slate-500/25'  },
  run_resumed:                     { label: 'Resumed',            classes: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/25' },
  run_terminated:                  { label: 'Terminated',         classes: 'bg-red-500/15    text-red-300    ring-red-500/25'    },
  run_completed:                   { label: 'Completed',          classes: 'bg-blue-500/15   text-blue-300   ring-blue-500/25'   },
  final_output:                    { label: 'Final Summary',      classes: 'bg-indigo-500/15 text-indigo-300 ring-indigo-500/25' },
};

function pillFor(entryType: string): PillConfig {
  return (
    PILL[entryType] ?? {
      label: entryType.replace(/_/g, ' '),
      classes: 'bg-slate-500/15 text-slate-300 ring-slate-500/25',
    }
  );
}

/* ------------------------------------------------------------------ */
/* Payload renderer                                                     */
/* ------------------------------------------------------------------ */

function PayloadContent({ type, payload }: { type: string; payload: Record<string, unknown> }) {
  // Agent reasoning — show the full text
  if (type === 'agent_reasoning' && payload.text) {
    return <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{String(payload.text)}</p>;
  }

  // Event received — show event type prominently + rest as key-value
  if (type === 'event_received') {
    const { event_type, ...rest } = payload;
    return (
      <div className="space-y-1">
        <p className="text-sm font-medium text-slate-200">{String(event_type ?? 'unknown')}</p>
        {Object.entries(rest).map(([k, v]) => (
          <p key={k} className="text-xs text-slate-500 font-mono">
            {k}: <span className="text-slate-400">{JSON.stringify(v)}</span>
          </p>
        ))}
      </div>
    );
  }

  // Business action — message / note is highlighted
  if (type.startsWith('action_message_')) {
    return (
      <div className="space-y-1">
        {!!payload.message && <p className="text-sm text-slate-300">&quot;{String(payload.message)}&quot;</p>}
        <div className="flex gap-3 text-xs text-slate-500">
          {!!payload.priority && <span>priority: {String(payload.priority)}</span>}
          {!!payload.channel  && <span>channel: {String(payload.channel)}</span>}
        </div>
      </div>
    );
  }

  if (type === 'action_create_internal_note') {
    return (
      <div className="space-y-1">
        {!!payload.note && <p className="text-sm text-slate-300 italic">&quot;{String(payload.note)}&quot;</p>}
        {!!payload.category && <p className="text-xs text-slate-500">category: {String(payload.category)}</p>}
      </div>
    );
  }

  // Agent sleep
  if (type === 'agent_sleep') {
    return (
      <p className="text-sm text-slate-400">
        {String(payload.reason ?? 'Going to sleep')}
        {payload.duration_minutes != null && (
          <span className="ml-2 text-slate-500">· {String(payload.duration_minutes)} min</span>
        )}
      </p>
    );
  }

  // Agent wake
  if (type === 'agent_wake') {
    return <p className="text-sm text-slate-400">Trigger: <span className="text-slate-300">{String(payload.trigger ?? 'unknown')}</span></p>;
  }

  // Classifier decision
  if (type === 'classifier_decision') {
    return (
      <div className="flex flex-wrap gap-3 text-sm">
        <span className={payload.should_wake ? 'text-amber-400 font-medium' : 'text-slate-400'}>
          {payload.should_wake ? '⚡ Wake agent' : '💤 Stay asleep'}
        </span>
        {!!payload.reason && <span className="text-slate-400">{String(payload.reason)}</span>}
        {!!payload.urgency && (
          <span className="text-xs text-slate-500 self-center">[{String(payload.urgency)} urgency]</span>
        )}
      </div>
    );
  }

  // Instruction added
  if (type === 'instruction_added') {
    return <p className="text-sm text-slate-300">&quot;{String(payload.instruction ?? '')}&quot;</p>;
  }

  // Final output — show summary line only (full view is in the summary panel)
  if (type === 'final_output') {
    return <p className="text-sm text-slate-300 line-clamp-2">{String(payload.summary ?? 'Summary generated')}</p>;
  }

  // Fallback: compact JSON
  if (Object.keys(payload).length === 0) return null;
  return (
    <pre className="text-xs text-slate-400 font-mono overflow-x-auto whitespace-pre-wrap">
      {JSON.stringify(payload, null, 2)}
    </pre>
  );
}

/* ------------------------------------------------------------------ */
/* Public component                                                     */
/* ------------------------------------------------------------------ */

interface Props {
  entry: ActivityLogEntry;
}

export default function ActivityLogEntryComponent({ entry }: Props) {
  const pill = pillFor(entry.entry_type);
  const ts = new Date(entry.created_at);
  const timeStr = ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const dateStr = ts.toLocaleDateString([], { month: 'short', day: 'numeric' });

  return (
    <div className="flex gap-3 py-3 px-4 rounded-lg hover:bg-slate-800/40 transition-colors group">
      {/* Timeline dot */}
      <div className="flex flex-col items-center pt-1 shrink-0">
        <div className={`w-2 h-2 rounded-full ring-1 ${pill.classes}`} />
        <div className="w-px flex-1 bg-slate-800 mt-1.5" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pb-3">
        <div className="flex items-center gap-2 flex-wrap mb-1.5">
          <span className={`inline-flex px-2 py-0.5 rounded-md text-xs font-medium ring-1 ${pill.classes}`}>
            {pill.label}
          </span>
          <span className="text-xs text-slate-600 group-hover:text-slate-500 transition-colors">
            {dateStr} · {timeStr}
          </span>
        </div>
        <PayloadContent type={entry.entry_type} payload={entry.payload} />
      </div>
    </div>
  );
}
