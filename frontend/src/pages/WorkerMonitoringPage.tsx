import { usePolling } from '../hooks/usePolling'
import { api } from '../services/api'
import type { Worker } from '../types/api'
import { Card, EmptyState, ErrorBanner, PageHeader } from '../components/ui'
import { StatusBadge } from '../components/StatusBadge'

export function WorkerMonitoringPage() {
  const { data: workers, error } = usePolling<Worker[]>(() => api.get('/workers'), 3000)

  const healthy = workers?.filter((w) => w.status === 'idle' || w.status === 'busy') ?? []
  const unhealthy = workers?.filter((w) => w.status === 'unhealthy') ?? []
  const stopped = workers?.filter((w) => w.status === 'stopped') ?? []

  return (
    <div>
      <PageHeader title="Workers" subtitle="Live status of every worker process" />
      {error && <ErrorBanner message={error} />}

      <div className="mb-6 grid grid-cols-3 gap-4">
        <Card>
          <p className="text-xs font-medium uppercase text-slate-500">Healthy</p>
          <p className="mt-1 text-xl font-semibold text-emerald-600">{healthy.length}</p>
        </Card>
        <Card>
          <p className="text-xs font-medium uppercase text-slate-500">Unhealthy</p>
          <p className="mt-1 text-xl font-semibold text-red-600">{unhealthy.length}</p>
        </Card>
        <Card>
          <p className="text-xs font-medium uppercase text-slate-500">Stopped</p>
          <p className="mt-1 text-xl font-semibold text-slate-500">{stopped.length}</p>
        </Card>
      </div>

      {workers && workers.length === 0 && (
        <EmptyState message="No workers have registered yet. Start one with `python -m app.workers.worker`." />
      )}

      <Card>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-500">
              <th className="pb-2 font-medium">Name</th>
              <th className="pb-2 font-medium">Host</th>
              <th className="pb-2 font-medium">Status</th>
              <th className="pb-2 font-medium">Running jobs</th>
              <th className="pb-2 font-medium">Last heartbeat</th>
            </tr>
          </thead>
          <tbody>
            {workers?.map((w) => (
              <tr key={w.id} className="border-b border-slate-50 last:border-0">
                <td className="py-2 font-medium text-slate-800">{w.name}</td>
                <td className="py-2 text-slate-600">{w.hostname ?? '—'}</td>
                <td className="py-2">
                  <StatusBadge status={w.status} />
                </td>
                <td className="py-2 text-slate-600">
                  {w.current_job_count} / {w.max_concurrency}
                </td>
                <td className="py-2 text-slate-500">
                  {w.last_heartbeat_at ? new Date(w.last_heartbeat_at).toLocaleString() : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
