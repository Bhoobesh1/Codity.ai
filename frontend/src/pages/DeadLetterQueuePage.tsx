import { useState } from 'react'
import { Link } from 'react-router-dom'
import { usePolling } from '../hooks/usePolling'
import { api } from '../services/api'
import type { Job, Page, Project, Queue } from '../types/api'
import { Card, EmptyState, ErrorBanner, PageHeader } from '../components/ui'

/**
 * There's no single "list all DLQ jobs across every queue" backend
 * endpoint, so this page walks the user's projects -> queues -> DLQ
 * jobs per queue and merges the results client-side. Fine at this
 * project's scale; a dedicated aggregate endpoint would be the right
 * fix if the number of queues grew large.
 */
export function DeadLetterQueuePage() {
  const [retryingId, setRetryingId] = useState<string | null>(null)

  const { data: projectsPage } = usePolling<Page<Project>>(
    () => api.get('/projects?page=1&page_size=100'),
    15000,
  )

  const { data: dlqJobs, error, refetch } = usePolling<Array<Job & { queueName: string }>>(
    async () => {
      if (!projectsPage) return []
      const allQueues: Queue[] = []
      for (const project of projectsPage.items) {
        const queuesPage = await api.get<Page<Queue>>(
          `/projects/${project.id}/queues?page=1&page_size=100`,
        )
        allQueues.push(...queuesPage.items)
      }
      const results: Array<Job & { queueName: string }> = []
      for (const queue of allQueues) {
        const jobsPage = await api.get<Page<Job>>(
          `/queues/${queue.id}/jobs?page=1&page_size=50&status=dead_letter`,
        )
        results.push(...jobsPage.items.map((j) => ({ ...j, queueName: queue.name })))
      }
      return results
    },
    6000,
    [projectsPage],
  )

  async function retryJob(jobId: string) {
    setRetryingId(jobId)
    try {
      await api.post(`/jobs/${jobId}/retry`)
      await refetch()
    } finally {
      setRetryingId(null)
    }
  }

  return (
    <div>
      <PageHeader
        title="Dead Letter Queue"
        subtitle="Jobs that exhausted their retries -- inspect and manually retry them"
      />
      {error && <ErrorBanner message={error} />}
      {dlqJobs && dlqJobs.length === 0 && (
        <EmptyState message="Nothing in the Dead Letter Queue right now." />
      )}

      <div className="space-y-3">
        {dlqJobs?.map((job) => (
          <Card key={job.id}>
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <Link to={`/jobs/${job.id}`} className="font-medium text-slate-900 hover:underline">
                    {job.name}
                  </Link>
                  <span className="text-xs text-slate-400">in {job.queueName}</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Failed after {job.retry_count} retries · last attempt{' '}
                  {new Date(job.updated_at).toLocaleString()}
                </p>
              </div>
              <button
                onClick={() => retryJob(job.id)}
                disabled={retryingId === job.id}
                className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50"
              >
                {retryingId === job.id ? 'Retrying…' : 'Retry'}
              </button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
