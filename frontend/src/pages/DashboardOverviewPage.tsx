import { usePolling } from '../hooks/usePolling'
import { api } from '../services/api'
import type { DashboardMetrics, Worker } from '../types/api'
import { Card, ErrorBanner, PageHeader, StatTile } from '../components/ui'
import { StatusBadge } from '../components/StatusBadge'

export function DashboardOverviewPage() {
  const { data: metrics, error: metricsError } = usePolling<DashboardMetrics>(
    () => api.get('/metrics/dashboard'),
    5000,
  )
  const { data: workers, error: workersError } = usePolling<Worker[]>(
    () => api.get('/workers'),
    5000,
  )

  return (
    <div>
      <PageHeader title="Overview" subtitle="System-wide health and job activity" />

      {metricsError && <ErrorBanner message={metricsError} />}

      {metrics && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <StatTile label="Total jobs" value={metrics.total_jobs} />
            <StatTile label="Completed" value={metrics.completed_jobs} />
            <StatTile label="Failed" value={metrics.failed_jobs} />
            <StatTile label="Retried" value={metrics.retried_jobs} />
            <StatTile label="Dead letter" value={metrics.dead_letter_jobs} />
            <StatTile
              label="Avg. duration"
              value={
                metrics.average_execution_time_ms != null
                  ? `${Math.round(metrics.average_execution_time_ms)}ms`
                  : '—'
              }
            />
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
            <StatTile label="Active workers" value={metrics.active_workers} />
            <StatTile label="Unhealthy workers" value={metrics.unhealthy_workers} />
            <StatTile label="Total workers" value={metrics.total_workers} />
          </div>
        </>
      )}

      <div className="mt-8">
        <h3 className="mb-3 text-sm font-semibold text-slate-900">Workers</h3>
        {workersError && <ErrorBanner message={workersError} />}
        <Card>
          {workers && workers.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-500">
                  <th className="pb-2 font-medium">Name</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Jobs running</th>
                  <th className="pb-2 font-medium">Last heartbeat</th>
                </tr>
              </thead>
              <tbody>
                {workers.map((w) => (
                  <tr key={w.id} className="border-b border-slate-50 last:border-0">
                    <td className="py-2 text-slate-800">{w.name}</td>
                    <td className="py-2">
                      <StatusBadge status={w.status} />
                    </td>
                    <td className="py-2 text-slate-600">
                      {w.current_job_count}/{w.max_concurrency}
                    </td>
                    <td className="py-2 text-slate-500">
                      {w.last_heartbeat_at ? new Date(w.last_heartbeat_at).toLocaleTimeString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-slate-500">No workers have registered yet.</p>
          )}
        </Card>
      </div>
    </div>
  )
}
