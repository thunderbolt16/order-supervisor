'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import api from '@/lib/api';
import type { RunDetail, FinalSummary } from '@/lib/types';
import StatusBadge from '@/components/StatusBadge';
import ActivityLogEntryComponent from '@/components/ActivityLogEntry';

/* ────────── helpers ────────── */
const EVENT_TYPES = [
  'order_created', 'payment_confirmed', 'payment_failed',
  'shipment_created', 'shipment_delayed', 'delivered',
  'refund_requested', 'customer_message_received',
  'no_update_for_n_hours', 'custom',
];

function Panel({ title, children, defaultOpen = true }: {
  title: string; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-slate-800 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-900/60 hover:bg-slate-800/60 transition-colors"
      >
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">{title}</span>
        <span className="text-slate-600 text-sm">{open ? '▲' : '▼'}</span>
      </button>
      {open && <div className="px-4 py-4 bg-slate-900/20">{children}</div>}
    </div>
  );
}

/* ────────── Final Summary Banner ────────── */
function FinalSummaryBanner({ summary }: { summary: FinalSummary }) {
  return (
    <div className="border border-blue-500/30 bg-blue-500/5 rounded-2xl p-5 mb-5">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-blue-400 text-lg">✦</span>
        <h2 className="text-sm font-semibold text-blue-300 uppercase tracking-wider">Final Summary</h2>
      </div>
      <p className="text-slate-200 text-sm leading-relaxed mb-4">{summary.summary}</p>
      {summary.actions_taken.length > 0 && (
        <Section title="Actions Taken" items={summary.actions_taken} color="text-emerald-400" />
      )}
      {summary.key_learnings.length > 0 && (
        <Section title="Key Learnings" items={summary.key_learnings} color="text-amber-400" />
      )}
      {summary.recommendations.length > 0 && (
        <Section title="Recommendations" items={summary.recommendations} color="text-violet-400" />
      )}
    </div>
  );
}

function Section({ title, items, color }: { title: string; items: string[]; color: string }) {
  return (
    <div className="mb-3 last:mb-0">
      <p className={`text-xs font-semibold uppercase tracking-wider mb-1.5 ${color}`}>{title}</p>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-sm text-slate-300">
            <span className={`mt-0.5 ${color} shrink-0`}>›</span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ────────── Main Page ────────── */
export default function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const logEndRef = useRef<HTMLDivElement>(null);

  /* Right-panel state */
  const [eventType, setEventType] = useState(EVENT_TYPES[0]);
  const [eventPayload, setEventPayload] = useState('{}');
  const [sendingEvent, setSendingEvent] = useState(false);
  const [eventMsg, setEventMsg] = useState('');

  const [instruction, setInstruction] = useState('');
  const [sendingInstruction, setSendingInstruction] = useState(false);
  const [instrMsg, setInstrMsg] = useState('');

  const [ctrlMsg, setCtrlMsg] = useState('');
  const [termConfirm, setTermConfirm] = useState(false);

  /* ── Fetch ── */
  const fetchRun = useCallback(async () => {
    try {
      const { data } = await api.get<RunDetail>(`/api/runs/${id}`);
      setRun(data);
      setError('');
    } catch {
      setError('Failed to load run');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchRun();
    const iv = setInterval(fetchRun, 3000);
    return () => clearInterval(iv);
  }, [fetchRun]);

  /* Auto-scroll log to bottom */
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [run?.activity_log?.length]);

  /* ── Actions ── */
  const sendEvent = async () => {
    try { JSON.parse(eventPayload); } catch { setEventMsg('❌ Invalid JSON payload'); return; }
    setSendingEvent(true); setEventMsg('');
    try {
      await api.post(`/api/runs/${id}/events`, {
        event_type: eventType,
        payload: JSON.parse(eventPayload),
      });
      setEventMsg('✓ Event sent');
      setTimeout(() => setEventMsg(''), 3000);
    } catch { setEventMsg('❌ Failed to send event'); }
    finally { setSendingEvent(false); }
  };

  const addInstruction = async () => {
    if (!instruction.trim()) return;
    setSendingInstruction(true); setInstrMsg('');
    try {
      await api.post(`/api/runs/${id}/instructions`, { instruction: instruction.trim() });
      setInstruction('');
      setInstrMsg('✓ Instruction added');
      setTimeout(() => setInstrMsg(''), 3000);
      fetchRun();
    } catch { setInstrMsg('❌ Failed to add instruction'); }
    finally { setSendingInstruction(false); }
  };

  const runControl = async (action: string) => {
    setCtrlMsg(''); setTermConfirm(false);
    try {
      await api.post(`/api/runs/${id}/${action}`);
      setCtrlMsg(`✓ ${action.replace('_', ' ')} done`);
      setTimeout(() => setCtrlMsg(''), 4000);
      fetchRun();
    } catch { setCtrlMsg(`❌ Failed to ${action}`); }
  };

  /* ── Render ── */
  if (loading) {
    return (
      <div className="px-6 py-6 space-y-3">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-12 bg-slate-800/50 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="px-6 py-12 text-center">
        <p className="text-red-400 mb-4">{error || 'Run not found'}</p>
        <button onClick={() => router.push('/')} className="text-sm text-blue-400 hover:underline">
          ← Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="px-6 py-5 h-[calc(100vh-3.5rem)] flex flex-col overflow-hidden">
      {/* ── Run Header ── */}
      <div className="flex items-center gap-4 mb-4 shrink-0">
        <button onClick={() => router.push('/')} className="text-slate-600 hover:text-slate-300 transition-colors text-sm">
          ← Back
        </button>
        <h1 className="text-xl font-bold text-white font-mono">{run.order_id}</h1>
        <StatusBadge status={run.status} />
        {run.supervisor_name && (
          <span className="text-xs text-slate-500 bg-slate-800 px-2.5 py-1 rounded-full">
            {run.supervisor_name}
          </span>
        )}
        <span className="text-xs text-slate-600 ml-auto">
          Started {new Date(run.started_at).toLocaleString()}
        </span>
      </div>

      {/* ── 70/30 Layout ── */}
      <div className="flex-1 grid grid-cols-[1fr_380px] gap-5 overflow-hidden">

        {/* ── Left: Activity Log ── */}
        <div className="flex flex-col overflow-hidden border border-slate-800 rounded-2xl">
          {/* Final summary if completed */}
          {run.status === 'completed' && run.final_summary && (
            <div className="shrink-0 px-4 pt-4">
              <FinalSummaryBanner summary={run.final_summary} />
            </div>
          )}

          <div className="px-4 py-3 border-b border-slate-800 shrink-0 flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Activity Log</p>
            <span className="text-xs text-slate-600">{run.activity_log.length} entries</span>
          </div>

          <div className="flex-1 overflow-y-auto">
            {run.activity_log.length === 0 ? (
              <p className="text-center text-slate-600 py-12 text-sm">No activity yet</p>
            ) : (
              <div className="px-2 py-2">
                {run.activity_log.map(entry => (
                  <ActivityLogEntryComponent key={entry.id} entry={entry} />
                ))}
              </div>
            )}
            <div ref={logEndRef} />
          </div>
        </div>

        {/* ── Right: Controls ── */}
        <div className="overflow-y-auto flex flex-col gap-4 pb-2">

          {/* Panel 1: Current State */}
          <Panel title="Current State" defaultOpen={false}>
            <pre className="text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
              {JSON.stringify(run.current_state, null, 2)}
            </pre>
          </Panel>

          {/* Panel 2: Inject Event */}
          <Panel title="Inject Event">
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Event Type</label>
                <select
                  value={eventType}
                  onChange={e => setEventType(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200
                             focus:outline-none focus:ring-2 focus:ring-blue-500/40 transition-all"
                >
                  {EVENT_TYPES.map(t => (
                    <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Payload (JSON)</label>
                <textarea
                  value={eventPayload}
                  onChange={e => setEventPayload(e.target.value)}
                  rows={3}
                  placeholder="{}"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono
                             text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/40 transition-all resize-none"
                />
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={sendEvent}
                  disabled={sendingEvent}
                  className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500
                             disabled:opacity-50 transition-all"
                >
                  {sendingEvent ? 'Sending…' : 'Send Event'}
                </button>
                {eventMsg && <span className={`text-xs ${eventMsg.startsWith('✓') ? 'text-emerald-400' : 'text-red-400'}`}>{eventMsg}</span>}
              </div>
            </div>
          </Panel>

          {/* Panel 3: Add Instruction */}
          <Panel title="Add Instruction">
            <div className="space-y-3">
              <textarea
                value={instruction}
                onChange={e => setInstruction(e.target.value)}
                rows={3}
                placeholder="e.g. Escalate if payment not confirmed within 2 hours"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200
                           placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-teal-500/40 transition-all resize-none"
              />
              <div className="flex items-center gap-3">
                <button
                  onClick={addInstruction}
                  disabled={sendingInstruction || !instruction.trim()}
                  className="px-4 py-2 rounded-lg bg-teal-600 text-white text-sm font-medium hover:bg-teal-500
                             disabled:opacity-50 transition-all"
                >
                  {sendingInstruction ? 'Adding…' : 'Add Instruction'}
                </button>
                {instrMsg && <span className={`text-xs ${instrMsg.startsWith('✓') ? 'text-emerald-400' : 'text-red-400'}`}>{instrMsg}</span>}
              </div>
              {run.extra_instructions.length > 0 && (
                <div className="mt-2 space-y-1.5">
                  <p className="text-xs text-slate-600 uppercase tracking-wider">Active</p>
                  {run.extra_instructions.map((instr, i) => (
                    <div key={i} className="flex gap-2 text-xs text-slate-400 bg-slate-800/60 rounded-lg px-3 py-2">
                      <span className="text-teal-600 shrink-0 mt-0.5">›</span>
                      <span>{instr}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Panel>

          {/* Panel 4: Run Controls */}
          <Panel title="Run Controls">
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <CtrlBtn
                  label="Interrupt"
                  color="amber"
                  onClick={() => runControl('interrupt')}
                  disabled={['completed', 'terminated', 'interrupted'].includes(run.status)}
                />
                <CtrlBtn
                  label="Pause"
                  color="slate"
                  onClick={() => runControl('pause')}
                  disabled={['completed', 'terminated', 'paused'].includes(run.status)}
                />
                <CtrlBtn
                  label="Resume"
                  color="emerald"
                  onClick={() => runControl('resume')}
                  disabled={['running', 'completed', 'terminated'].includes(run.status)}
                />
                <CtrlBtn
                  label="Terminate"
                  color="red"
                  onClick={() => setTermConfirm(true)}
                  disabled={['completed', 'terminated'].includes(run.status)}
                />
              </div>

              {/* Terminate confirmation */}
              {termConfirm && (
                <div className="border border-red-500/30 bg-red-500/5 rounded-xl p-3 text-sm">
                  <p className="text-red-300 mb-3">Terminate this run? This cannot be undone.</p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => runControl('terminate')}
                      className="flex-1 py-1.5 rounded-lg bg-red-600 text-white text-xs font-medium hover:bg-red-500 transition-all"
                    >
                      Yes, terminate
                    </button>
                    <button
                      onClick={() => setTermConfirm(false)}
                      className="flex-1 py-1.5 rounded-lg border border-slate-700 text-slate-400 text-xs hover:text-white transition-all"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {ctrlMsg && (
                <p className={`text-xs text-center ${ctrlMsg.startsWith('✓') ? 'text-emerald-400' : 'text-red-400'}`}>
                  {ctrlMsg}
                </p>
              )}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

/* ── Tiny control button ── */
function CtrlBtn({
  label, color, onClick, disabled,
}: {
  label: string; color: 'amber' | 'slate' | 'emerald' | 'red';
  onClick: () => void; disabled: boolean;
}) {
  const base = 'py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed border';
  const colors = {
    amber:   'border-amber-500/30   bg-amber-500/10   text-amber-400   hover:bg-amber-500/20',
    slate:   'border-slate-600/30   bg-slate-700/20   text-slate-400   hover:bg-slate-700/40',
    emerald: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20',
    red:     'border-red-500/30     bg-red-500/10     text-red-400     hover:bg-red-500/20',
  };
  return (
    <button onClick={onClick} disabled={disabled} className={`${base} ${colors[color]}`}>
      {label}
    </button>
  );
}
