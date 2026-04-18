'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import type { Run } from '@/lib/types';
import StatusBadge from '@/components/StatusBadge';
import NewRunModal from '@/components/NewRunModal';

function formatRelative(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  const diff = Date.now() - new Date(dateStr).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return new Date(dateStr).toLocaleDateString();
}

function lastActivity(run: Run): string {
  if (run.status === 'sleeping' && run.next_wake_at) {
    const d = new Date(run.next_wake_at);
    return `Next wake ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  }
  if (run.completed_at) return `Ended ${formatRelative(run.completed_at)}`;
  return `Started ${formatRelative(run.started_at)}`;
}

export default function DashboardPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);

  const fetchRuns = async () => {
    try {
      const { data } = await api.get<Run[]>('/api/runs');
      setRuns(data);
      setError('');
    } catch {
      setError('Failed to fetch runs — retrying…');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
    const id = setInterval(fetchRuns, 5000);
    return () => clearInterval(id);
  }, []);

  const activeCount  = runs.filter(r => r.status === 'running').length;
  const sleepingCount = runs.filter(r => r.status === 'sleeping').length;

  return (
    <div className="px-6 py-6">
      {/* ── Page header ── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Order Runs</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {loading ? 'Loading…' : `${runs.length} total · ${activeCount} running · ${sleepingCount} sleeping`}
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-medium
                     hover:bg-blue-500 transition-all shadow-lg shadow-blue-500/20 active:scale-95"
        >
          <span className="text-base leading-none">+</span>
          New Run
        </button>
      </div>

      {/* ── Error banner ── */}
      {error && (
        <div className="mb-4 flex items-center gap-2 text-sm text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-xl px-4 py-3">
          <span>⚠</span> {error}
        </div>
      )}

      {/* ── Loading skeleton ── */}
      {loading && (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-14 bg-slate-800/50 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {/* ── Empty state ── */}
      {!loading && runs.length === 0 && !error && (
        <div className="flex flex-col items-center justify-center h-64 text-center">
          <div className="w-14 h-14 rounded-2xl bg-slate-800 flex items-center justify-center text-3xl mb-4">📦</div>
          <p className="text-slate-400 font-medium">No runs yet</p>
          <p className="text-slate-600 text-sm mt-1">Click &quot;New Run&quot; to start supervising an order</p>
        </div>
      )}

      {/* ── Runs table ── */}
      {!loading && runs.length > 0 && (
        <div className="border border-slate-800 rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-900/80 border-b border-slate-800">
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Order ID</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Supervisor</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Started</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Last Activity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {runs.map(run => (
                <tr
                  key={run.id}
                  onClick={() => router.push(`/runs/${run.id}`)}
                  className="bg-slate-900/30 hover:bg-slate-800/50 cursor-pointer transition-colors group"
                >
                  <td className="px-5 py-3.5">
                    <span className="font-mono text-slate-200 font-medium group-hover:text-white transition-colors">
                      {run.order_id}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <StatusBadge status={run.status} />
                  </td>
                  <td className="px-5 py-3.5 text-slate-400">
                    {run.supervisor_name ?? '—'}
                  </td>
                  <td className="px-5 py-3.5 text-slate-500 text-xs">
                    {new Date(run.started_at).toLocaleString([], {
                      month: 'short', day: 'numeric',
                      hour: '2-digit', minute: '2-digit',
                    })}
                  </td>
                  <td className="px-5 py-3.5 text-slate-500 text-xs">
                    {lastActivity(run)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── New run modal ── */}
      {showModal && (
        <NewRunModal
          onClose={() => setShowModal(false)}
          onCreated={fetchRuns}
        />
      )}
    </div>
  );
}
