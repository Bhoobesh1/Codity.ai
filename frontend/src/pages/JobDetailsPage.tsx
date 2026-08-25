import { useParams } from 'react-router-dom'
import { usePolling } from '../hooks/usePolling'
import { api } from '../services/api'
import type { Job, JobExecution } from '../types/api'
import { Card, EmptyState, ErrorBanner, PageHeader } from '../components/ui'
import { StatusBadge } from '../components/StatusBadge'

export function JobDetailsPage() {
  const { jobId } = useParams<{ jobId: string }>()

  const { data: job, error, refetch } = usePolling<Job>(() => api.get(`/jobs/${jobId}`), 3000, [
    jobId,
  ])
  const { data: executions } = usePolling<JobExecution[]>(
    () => api.get(`/jobs/${jobId}/executions`),
    3000,
    [jobId],
  )

  async function retry() {
    await api.post(`/jobs/${jobId}/retry`)
    refetch()
  }

  if (error) return <ErrorBanner message={error} />
  if (!job) return <p className="text-sm text-slate-500">Loading…</p>

  return (
    <div>
      <PageHeader
        title={job.name}
        subtitle={`Job ${job.id}`}
        action={
          job.status === 'dead_letter' ? (
            <button
              onClick={retry}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
            >
              Retry from DLQ
            </button>
          ) : undefined
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-slate-900">Details</h3>
          <dl className="space-y-2 text-sm">
            <Row label="Status">
              <StatusBadge status={job.status} />
            </Row>
            <Row label="Type" value={job.job_type} />
            <Row label="Priority" value={String(job.priority)} />
            <Row label="Retries" value={`${job.retry_count} / ${job.max_retries}`} />
            <Row label="Scheduled at" value={new Date(job.scheduled_at).toLocaleString()} />
            <Row label="Claimed by" value={job.claimed_by ?? '—'} />
          </dl>
        </Card>

        <Card>
          <h3 className="mb-3 text-sm font-semibold text-slate-900">Payload</h3>
          <pre className="overflow-x-auto rounded-md bg-slate-50 p-3 text-xs text-slate-700">
            {JSON.stringify(job.payload, null, 2)}
          </pre>
        </Card>
      </div>

      <div className="mt-6">
        <h3 className="mb-3 text-sm font-semibold text-slate-900">Execution history</h3>
        {executions && executions.length === 0 && <EmptyState message="This job hasn't run yet." />}
        <div className="space-y-3">
          {executions?.map((ex) => (
            <Card key={ex.id}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-800">Attempt {ex.retry_attempt + 1}</span>
                    <StatusBadge status={ex.status} />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {new Date(ex.started_at).toLocaleString()}
                    {ex.duration_ms != null && ` · ${ex.duration_ms}ms`}
                  </p>
                </div>
              </div>
              {ex.error_message && (
                <p className="mt-2 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
                  {ex.error_message}
                </p>
              )}
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}

function Row({ label, value, children }: { label: string; value?: string; children?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-800">{children ?? value}</dd>
    </div>
  )
}
