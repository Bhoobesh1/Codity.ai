import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { usePolling } from '../hooks/usePolling'
import { api, ApiRequestError } from '../services/api'
import type { Job, JobStatus, Page, Queue } from '../types/api'
import { Card, EmptyState, ErrorBanner, PageHeader } from '../components/ui'
import { StatusBadge } from '../components/StatusBadge'

const STATUS_FILTERS: (JobStatus | 'all')[] = [
  'all',
  'queued',
  'running',
  'completed',
  'failed',
  'retrying',
  'dead_letter',
]

export function JobExplorerPage() {
  const { queueId } = useParams<{ queueId: string }>()
  const [statusFilter, setStatusFilter] = useState<JobStatus | 'all'>('all')
  const [showNewJob, setShowNewJob] = useState(false)

  const { data: queue } = usePolling<Queue>(() => api.get(`/queues/${queueId}`), 15000, [queueId])

  const query =
    statusFilter === 'all'
      ? `/queues/${queueId}/jobs?page=1&page_size=50`
      : `/queues/${queueId}/jobs?page=1&page_size=50&status=${statusFilter}`

  const {
    data: jobsPage,
    error,
    refetch,
  } = usePolling<Page<Job>>(() => api.get(query), 3000, [queueId, statusFilter])

  return (
    <div>
      <PageHeader
        title={queue ? `Jobs in ${queue.name}` : 'Jobs'}
        subtitle="Submit and monitor jobs in this queue"
        action={
          <button
            onClick={() => setShowNewJob((v) => !v)}
            className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
          >
            Submit job
          </button>
        }
      />

      {showNewJob && queueId && (
        <NewJobForm
          queueId={queueId}
          onDone={() => {
            setShowNewJob(false)
            refetch()
          }}
        />
      )}

      <div className="mb-4 flex gap-2">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              statusFilter === s
                ? 'bg-slate-900 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {s.replace('_', ' ')}
          </button>
        ))}
      </div>

      {error && <ErrorBanner message={error} />}
      {jobsPage && jobsPage.items.length === 0 && <EmptyState message="No jobs match this filter." />}

      <Card>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-500">
              <th className="pb-2 font-medium">Name</th>
              <th className="pb-2 font-medium">Type</th>
              <th className="pb-2 font-medium">Status</th>
              <th className="pb-2 font-medium">Retries</th>
              <th className="pb-2 font-medium">Scheduled</th>
            </tr>
          </thead>
          <tbody>
            {jobsPage?.items.map((job) => (
              <tr key={job.id} className="border-b border-slate-50 last:border-0">
                <td className="py-2">
                  <Link to={`/jobs/${job.id}`} className="font-medium text-slate-800 hover:underline">
                    {job.name}
                  </Link>
                </td>
                <td className="py-2 text-slate-600">{job.job_type}</td>
                <td className="py-2">
                  <StatusBadge status={job.status} />
                </td>
                <td className="py-2 text-slate-600">
                  {job.retry_count}/{job.max_retries}
                </td>
                <td className="py-2 text-slate-500">{new Date(job.scheduled_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}

function NewJobForm({ queueId, onDone }: { queueId: string; onDone: () => void }) {
  const [name, setName] = useState('echo')
  const [jobType, setJobType] = useState<'immediate' | 'delayed'>('immediate')
  const [delaySeconds, setDelaySeconds] = useState(60)
  const [payload, setPayload] = useState('{}')
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    let parsedPayload: unknown
    try {
      parsedPayload = JSON.parse(payload)
    } catch {
      setError('Payload must be valid JSON.')
      return
    }
    try {
      await api.post(`/queues/${queueId}/jobs`, {
        name,
        job_type: jobType,
        payload: parsedPayload,
        ...(jobType === 'delayed' ? { delay_seconds: delaySeconds } : {}),
      })
      onDone()
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Failed to submit job.')
    }
  }

  return (
    <Card className="mb-4">
      <form onSubmit={submit} className="space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-600">Handler name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600">Type</label>
            <select
              value={jobType}
              onChange={(e) => setJobType(e.target.value as typeof jobType)}
              className="mt-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
            >
              <option value="immediate">Immediate</option>
              <option value="delayed">Delayed</option>
            </select>
          </div>
          {jobType === 'delayed' && (
            <div>
              <label className="block text-xs font-medium text-slate-600">Delay (seconds)</label>
              <input
                type="number"
                min={0}
                value={delaySeconds}
                onChange={(e) => setDelaySeconds(Number(e.target.value))}
                className="mt-1 w-28 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
              />
            </div>
          )}
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600">Payload (JSON)</label>
          <textarea
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
            rows={3}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-1.5 font-mono text-xs"
          />
        </div>
        <button type="submit" className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white">
          Submit
        </button>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </form>
    </Card>
  )
}
