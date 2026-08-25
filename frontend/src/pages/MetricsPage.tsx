import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { usePolling } from '../hooks/usePolling'
import { api } from '../services/api'
import type { DashboardMetrics } from '../types/api'
import { Card, ErrorBanner, PageHeader, StatTile } from '../components/ui'

export function MetricsPage() {
  const { data: metrics, error } = usePolling<DashboardMetrics>(
    () => api.get('/metrics/dashboard'),
    5000,
  )

  const throughputData = metrics
    ? Object.entries(metrics.queue_throughput).map(([queueId, count]) => ({
        queue: queueId.slice(0, 8),
        completed: count,
      }))
    : []

  return (
    <div>
      <PageHeader title="Metrics & System Health" subtitle="Throughput and reliability at a glance" />
      {error && <ErrorBanner message={error} />}

      {metrics && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatTile label="Total jobs" value={metrics.total_jobs} />
            <StatTile
              label="Success rate"
              value={
                metrics.total_jobs > 0
                  ? `${Math.round((metrics.completed_jobs / metrics.total_jobs) * 100)}%`
                  : '—'
              }
            />
            <StatTile
              label="Avg. execution time"
              value={
                metrics.average_execution_time_ms != null
                  ? `${Math.round(metrics.average_execution_time_ms)}ms`
                  : '—'
              }
            />
            <StatTile label="Dead lettered" value={metrics.dead_letter_jobs} />
          </div>

          <div className="mt-6">
            <Card>
              <h3 className="mb-4 text-sm font-semibold text-slate-900">
                Queue throughput (completed jobs, last 24h)
              </h3>
              {throughputData.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={throughputData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="queue" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="completed" fill="#0f172a" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-slate-500">No completed jobs in the last 24 hours yet.</p>
              )}
            </Card>
          </div>

          <div className="mt-6 grid grid-cols-3 gap-4">
            <StatTile label="Active workers" value={metrics.active_workers} />
            <StatTile label="Unhealthy workers" value={metrics.unhealthy_workers} />
            <StatTile label="Retried jobs" value={metrics.retried_jobs} />
          </div>
        </>
      )}
    </div>
  )
}
