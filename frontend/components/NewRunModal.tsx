'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import type { Supervisor } from '@/lib/types';

interface Props {
  onClose: () => void;
  onCreated: () => void;
}

export default function NewRunModal({ onClose, onCreated }: Props) {
  const [supervisors, setSupervisors] = useState<Supervisor[]>([]);
  const [loadingSupervisors, setLoadingSupervisors] = useState(true);

  const [supervisorId, setSupervisorId] = useState('');
  const [orderId, setOrderId] = useState('');
  const [initialContext, setInitialContext] = useState('{}');
  const [contextError, setContextError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/api/supervisors')
      .then(r => {
        setSupervisors(r.data);
        if (r.data.length > 0) setSupervisorId(r.data[0].id);
      })
      .catch(() => setError('Could not load supervisors'))
      .finally(() => setLoadingSupervisors(false));
  }, []);

  const validateContext = (val: string) => {
    try { JSON.parse(val); setContextError(''); return true; }
    catch { setContextError('Invalid JSON'); return false; }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateContext(initialContext)) return;
    setSubmitting(true);
    setError('');
    try {
      await api.post('/api/runs', {
        supervisor_id: supervisorId,
        order_id: orderId.trim(),
        initial_context: JSON.parse(initialContext),
      });
      onCreated();
      onClose();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? 'Failed to create run');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl shadow-black/50 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-white">Start New Run</h2>
            <p className="text-xs text-slate-500 mt-0.5">Create a supervised run for an order</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors text-lg leading-none">✕</button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-5">
          {/* Supervisor */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Supervisor</label>
            {loadingSupervisors ? (
              <div className="h-10 bg-slate-800 rounded-lg animate-pulse" />
            ) : (
              <select
                value={supervisorId}
                onChange={e => setSupervisorId(e.target.value)}
                required
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200
                           focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
              >
                {supervisors.length === 0 && (
                  <option value="" disabled>No supervisors — create one first</option>
                )}
                {supervisors.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            )}
          </div>

          {/* Order ID */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Order ID</label>
            <input
              type="text"
              value={orderId}
              onChange={e => setOrderId(e.target.value)}
              placeholder="e.g. ORD-2024-00123"
              required
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200
                         placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50
                         focus:border-blue-500/50 transition-all"
            />
          </div>

          {/* Initial context */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Initial Context
              <span className="ml-1.5 text-slate-600 font-normal">(JSON)</span>
            </label>
            <textarea
              value={initialContext}
              onChange={e => { setInitialContext(e.target.value); if (contextError) validateContext(e.target.value); }}
              onBlur={() => validateContext(initialContext)}
              rows={5}
              placeholder='{"customer_tier": "gold", "items": 3}'
              className={`w-full bg-slate-800 border rounded-lg px-3 py-2 text-sm text-slate-200 font-mono
                          placeholder:text-slate-600 focus:outline-none focus:ring-2 transition-all resize-none
                          ${contextError
                            ? 'border-red-500/60 focus:ring-red-500/30'
                            : 'border-slate-700 focus:ring-blue-500/50 focus:border-blue-500/50'}`}
            />
            {contextError && <p className="mt-1 text-xs text-red-400">{contextError}</p>}
          </div>

          {/* API error */}
          {error && (
            <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              <span>⚠</span> {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-medium border border-slate-700 text-slate-400
                         hover:text-white hover:border-slate-600 transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || loadingSupervisors || supervisors.length === 0}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white
                         hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all
                         shadow-lg shadow-blue-500/20"
            >
              {submitting ? 'Creating…' : 'Start Run'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
