import type { RunStatus } from '@/lib/types';

interface StatusConfig {
  label: string;
  dot: string;
  pill: string;
}

const CONFIG: Record<string, StatusConfig> = {
  running:     { label: 'Running',     dot: 'bg-emerald-400 animate-pulse', pill: 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/25' },
  sleeping:    { label: 'Sleeping',    dot: 'bg-amber-400',                 pill: 'bg-amber-500/10  text-amber-400  ring-amber-500/25'  },
  paused:      { label: 'Paused',      dot: 'bg-slate-400',                 pill: 'bg-slate-500/10  text-slate-400  ring-slate-500/25'  },
  interrupted: { label: 'Interrupted', dot: 'bg-orange-400',                pill: 'bg-orange-500/10 text-orange-400 ring-orange-500/25' },
  completed:   { label: 'Completed',   dot: 'bg-blue-400',                  pill: 'bg-blue-500/10   text-blue-400   ring-blue-500/25'   },
  terminated:  { label: 'Terminated',  dot: 'bg-red-400',                   pill: 'bg-red-500/10    text-red-400    ring-red-500/25'    },
};

interface Props {
  status: string;
  className?: string;
}

export default function StatusBadge({ status, className = '' }: Props) {
  const cfg = CONFIG[status] ?? { label: status, dot: 'bg-slate-400', pill: 'bg-slate-500/10 text-slate-400 ring-slate-500/25' };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ring-1 ${cfg.pill} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}
