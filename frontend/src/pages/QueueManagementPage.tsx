import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { usePolling } from '../hooks/usePolling'
import { api, ApiRequestError } from '../services/api'
import type { Page, Project, Queue } from '../types/api'
import { Card, EmptyState, ErrorBanner, PageHeader } from '../components/ui'
import { StatusBadge } from '../components/StatusBadge'

export function QueueManagementPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [showNewQueue, setShowNewQueue] = useState(false)

  const { data: project } = usePolling<Project>(() => api.get(`/projects/${projectId}`), 15000, [
    projectId,
  ])
  const {
    data: queuesPage,
    error,
    refetch,
  } = usePolling<Page<Queue>>(
    () => api.get(`/projects/${projectId}/queues?page=1&page_size=50`),
    4000,
    [projectId],
  )

  async function togglePause(queue: Queue) {
    const action = queue.is_paused ? 'resume' : 'pause'
    await api.post(`/queues/${queue.id}/${action}`)
    refetch()
  }

  return (
    <div>
      <PageHeader
        title={project ? project.name : 'Project'}
        subtitle="Queues in this project"
        action={
          <button
            onClick={() => setShowNewQueue((v) => !v)}
            className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
          >
            New queue
          </button>
        }
      />

      {showNewQueue && projectId && (
        <NewQueueForm
          projectId={projectId}
          onDone={() => {
            setShowNewQueue(false)
            refetch()
          }}
        />
      )}

      {error && <ErrorBanner message={error} />}
      {queuesPage && queuesPage.items.length === 0 && (
        <EmptyState message="No queues yet. Create one to start submitting jobs." />
      )}

      <div className="space-y-3">
        {queuesPage?.items.map((queue) => (
          <Card key={queue.id}>
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <Link to={`/queues/${queue.id}/jobs`} className="font-medium text-slate-900 hover:underline">
                    {queue.name}
                  </Link>
                  {queue.is_paused && <StatusBadge status="stopped" />}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  priority {queue.priority} · concurrency {queue.concurrency_limit} · retry{' '}
                  {queue.retry_policy?.strategy ?? 'default'}
                </p>
              </div>
              <div className="flex gap-2">
                <Link
                  to={`/queues/${queue.id}/jobs`}
                  className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  View jobs
                </Link>
                <button
                  onClick={() => togglePause(queue)}
                  className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  {queue.is_paused ? 'Resume' : 'Pause'}
                </button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

function NewQueueForm({ projectId, onDone }: { projectId: string; onDone: () => void }) {
  const [name, setName] = useState('')
  const [concurrency, setConcurrency] = useState(5)
  const [strategy, setStrategy] = useState<'fixed' | 'linear' | 'exponential'>('exponential')
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    try {
      await api.post(`/projects/${projectId}/queues`, {
        name,
        concurrency_limit: concurrency,
        retry_policy: { strategy },
      })
      onDone()
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Failed to create queue.')
    }
  }

  return (
    <Card className="mb-4">
      <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-600">Queue name</label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600">Concurrency limit</label>
          <input
            type="number"
            min={1}
            value={concurrency}
            onChange={(e) => setConcurrency(Number(e.target.value))}
            className="mt-1 w-24 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600">Retry strategy</label>
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value as typeof strategy)}
            className="mt-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          >
            <option value="fixed">Fixed</option>
            <option value="linear">Linear</option>
            <option value="exponential">Exponential</option>
          </select>
        </div>
        <button type="submit" className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white">
          Create
        </button>
      </form>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </Card>
  )
}
