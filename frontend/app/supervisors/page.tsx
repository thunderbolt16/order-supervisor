'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import type { Supervisor } from '@/lib/types';

const WAKE_OPTIONS = ['low', 'medium', 'high'] as const;
const DEFAULT_ACTIONS = [
  'message_fulfillment_team',
  'message_payments_team',
  'message_logistics_team',
  'message_customer',
  'create_internal_note',
];

interface FormState {
  name: string;
  base_instruction: string;
  available_actions: string[];
  wake_aggressiveness: 'low' | 'medium' | 'high';
  default_wake_interval_minutes: number;
  model: string;
}

const BLANK_FORM: FormState = {
  name: '',
  base_instruction: '',
  available_actions: [...DEFAULT_ACTIONS],
  wake_aggressiveness: 'medium',
  default_wake_interval_minutes: 120,
  model: 'claude-sonnet-4-6',
};

export default function SupervisorsPage() {
  const [supervisors, setSupervisors] = useState<Supervisor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<FormState>({ ...BLANK_FORM });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  const fetchSupervisors = async () => {
    try {
      const { data } = await api.get<Supervisor[]>('/api/supervisors');
      setSupervisors(data);
      setError('');
    } catch {
      setError('Failed to load supervisors');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSupervisors(); }, []);

  const toggleAction = (action: string) => {
    setForm(f => ({
      ...f,
      available_actions: f.available_actions.includes(action)
        ? f.available_actions.filter(a => a !== action)
        : [...f.available_actions, action],
    }));
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.available_actions.length === 0) {
      setFormError('Select at least one available action'); return;
    }
    setSubmitting(true); setFormError('');
    try {
      await api.post('/api/supervisors', form);
      setShowForm(false);
      setForm({ ...BLANK_FORM });
      fetchSupervisors();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(msg ?? 'Failed to create supervisor');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="px-6 py-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Supervisors</h1>
          <p className="text-sm text-slate-500 mt-0.5">Reusable agent configurations</p>
        </div>
        <button
          onClick={() => setShowForm(s => !s)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white text-sm
                     font-medium hover:bg-blue-500 transition-all shadow-lg shadow-blue-500/20 active:scale-95"
        >
          {showForm ? '✕ Cancel' : '+ Create Supervisor'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
          {error}
        </div>
      )}

      {/* Create form */}
      {showForm && (
        <form
          onSubmit={submit}
          className="mb-8 border border-slate-700 rounded-2xl overflow-hidden bg-slate-900/60"
        >
          <div className="px-5 py-4 border-b border-slate-800 bg-slate-900/80">
            <h2 className="text-sm font-semibold text-white">New Supervisor</h2>
          </div>
          <div className="px-5 py-5 space-y-5">
            {/* Name */}
            <Field label="Name">
              <input
                type="text" value={form.name} required
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Standard Order Supervisor"
                className={inputCls}
              />
            </Field>

            {/* Base instruction */}
            <Field label="Base Instruction">
              <textarea
                value={form.base_instruction} required rows={5}
                onChange={e => setForm(f => ({ ...f, base_instruction: e.target.value }))}
                placeholder="Describe the agent's goal and personality…"
                className={`${inputCls} resize-none`}
              />
            </Field>

            {/* Available actions */}
            <Field label="Available Actions">
              <div className="grid grid-cols-2 gap-2">
                {DEFAULT_ACTIONS.map(action => (
                  <label key={action} className="flex items-center gap-2.5 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={form.available_actions.includes(action)}
                      onChange={() => toggleAction(action)}
                      className="w-4 h-4 rounded accent-blue-500"
                    />
                    <span className="text-sm text-slate-400 group-hover:text-slate-200 transition-colors">
                      {action.replace(/_/g, ' ')}
                    </span>
                  </label>
                ))}
              </div>
            </Field>

            {/* Two-column row */}
            <div className="grid grid-cols-2 gap-4">
              <Field label="Wake Aggressiveness">
                <select
                  value={form.wake_aggressiveness}
                  onChange={e => setForm(f => ({ ...f, wake_aggressiveness: e.target.value as never }))}
                  className={inputCls}
                >
                  {WAKE_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </Field>
              <Field label="Default Wake Interval (min)">
                <input
                  type="number" min={1} max={1440}
                  value={form.default_wake_interval_minutes}
                  onChange={e => setForm(f => ({ ...f, default_wake_interval_minutes: Number(e.target.value) }))}
                  className={inputCls}
                />
              </Field>
            </div>

            {/* Model */}
            <Field label="Model">
              <input
                type="text" value={form.model}
                onChange={e => setForm(f => ({ ...f, model: e.target.value }))}
                placeholder="claude-sonnet-4-6"
                className={inputCls}
              />
            </Field>

            {formError && (
              <p className="text-sm text-red-400">{formError}</p>
            )}

            <div className="flex gap-3 pt-1">
              <button type="button" onClick={() => setShowForm(false)}
                className="px-4 py-2 rounded-lg border border-slate-700 text-slate-400 text-sm hover:text-white transition-all">
                Cancel
              </button>
              <button type="submit" disabled={submitting}
                className="px-5 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500
                           disabled:opacity-50 transition-all shadow-lg shadow-blue-500/20">
                {submitting ? 'Creating…' : 'Create Supervisor'}
              </button>
            </div>
          </div>
        </form>
      )}

      {/* List */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <div key={i} className="h-28 bg-slate-800/50 rounded-2xl animate-pulse" />)}
        </div>
      ) : supervisors.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 text-center">
          <div className="w-12 h-12 rounded-2xl bg-slate-800 flex items-center justify-center text-2xl mb-3">🤖</div>
          <p className="text-slate-400 font-medium">No supervisors yet</p>
          <p className="text-slate-600 text-sm mt-1">Create one to start supervising orders</p>
        </div>
      ) : (
        <div className="space-y-3">
          {supervisors.map(s => (
            <div key={s.id} className="border border-slate-800 rounded-2xl p-5 bg-slate-900/40 hover:bg-slate-900/70 transition-colors">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <h3 className="font-semibold text-white">{s.name}</h3>
                  <p className="text-xs text-slate-500 mt-0.5 font-mono">{s.model}</p>
                </div>
                <div className="flex flex-wrap gap-2 text-right shrink-0">
                  <Badge color="slate" label={`Wake: ${s.wake_aggressiveness}`} />
                  <Badge color="blue" label={`${s.default_wake_interval_minutes}min interval`} />
                </div>
              </div>
              <p className="text-sm text-slate-400 leading-relaxed line-clamp-2 mb-3">
                {s.base_instruction}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {s.available_actions.map(action => (
                  <span key={action}
                    className="text-xs px-2 py-0.5 rounded-md bg-violet-500/10 text-violet-400 ring-1 ring-violet-500/20">
                    {action.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* helpers */
const inputCls =
  'w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 ' +
  'placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/50 transition-all';

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-400 mb-1.5">{label}</label>
      {children}
    </div>
  );
}

function Badge({ label, color }: { label: string; color: 'slate' | 'blue' }) {
  const cls = color === 'blue'
    ? 'bg-blue-500/10 text-blue-400 ring-blue-500/20'
    : 'bg-slate-700/40 text-slate-400 ring-slate-600/20';
  return (
    <span className={`text-xs px-2.5 py-0.5 rounded-full ring-1 ${cls}`}>{label}</span>
  );
}
