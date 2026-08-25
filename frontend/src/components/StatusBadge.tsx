const COLORS: Record<string, string> = {
  // Job statuses
  queued: 'bg-slate-100 text-slate-700',
  scheduled: 'bg-blue-100 text-blue-700',
  claimed: 'bg-amber-100 text-amber-700',
  running: 'bg-blue-100 text-blue-700',
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
  retrying: 'bg-amber-100 text-amber-700',
  dead_letter: 'bg-red-200 text-red-800',
  succeeded: 'bg-emerald-100 text-emerald-700',
  // Worker statuses
  idle: 'bg-slate-100 text-slate-700',
  busy: 'bg-blue-100 text-blue-700',
  unhealthy: 'bg-red-100 text-red-700',
  stopped: 'bg-slate-200 text-slate-600',
}

export function StatusBadge({ status }: { status: string }) {
  const classes = COLORS[status] ?? 'bg-slate-100 text-slate-700'
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${classes}`}>
      {status.replace('_', ' ')}
    </span>
  )
}
