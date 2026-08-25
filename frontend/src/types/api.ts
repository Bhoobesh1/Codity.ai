export interface User {
  id: string
  email: string
  full_name: string
  is_active: boolean
}

export interface Organization {
  id: string
  name: string
  slug: string
  role: string
}

export interface Project {
  id: string
  organization_id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export type RetryStrategy = 'fixed' | 'linear' | 'exponential'

export interface RetryPolicy {
  id: string
  strategy: RetryStrategy
  base_delay_seconds: number
  max_delay_seconds: number
  max_retries: number
}

export interface Queue {
  id: string
  project_id: string
  name: string
  priority: number
  concurrency_limit: number
  is_paused: boolean
  retry_policy: RetryPolicy | null
  created_at: string
  updated_at: string
}

export interface QueueStats {
  queue_id: string
  total_jobs: number
  queued: number
  running: number
  completed: number
  failed: number
  retrying: number
  dead_letter: number
}

export type JobType = 'immediate' | 'delayed' | 'scheduled' | 'recurring' | 'batch'
export type JobStatus =
  | 'queued'
  | 'scheduled'
  | 'claimed'
  | 'running'
  | 'completed'
  | 'failed'
  | 'retrying'
  | 'dead_letter'

export interface Job {
  id: string
  queue_id: string
  name: string
  job_type: JobType
  payload: Record<string, unknown>
  priority: number
  status: JobStatus
  scheduled_at: string
  retry_count: number
  max_retries: number
  batch_id: string | null
  claimed_by: string | null
  claimed_at: string | null
  created_at: string
  updated_at: string
}

export type ExecutionStatus = 'running' | 'succeeded' | 'failed'

export interface JobExecution {
  id: string
  job_id: string
  worker_id: string | null
  retry_attempt: number
  status: ExecutionStatus
  started_at: string
  ended_at: string | null
  duration_ms: number | null
  error_message: string | null
}

export type WorkerStatus = 'idle' | 'busy' | 'unhealthy' | 'stopped'

export interface Worker {
  id: string
  name: string
  hostname: string | null
  max_concurrency: number
  status: WorkerStatus
  last_heartbeat_at: string | null
  current_job_count: number
  created_at: string
}

export interface ScheduledJob {
  id: string
  queue_id: string
  name: string
  cron_expression: string
  payload: Record<string, unknown>
  is_active: boolean
  next_run_at: string | null
  last_run_at: string | null
  created_at: string
  updated_at: string
}

export interface DashboardMetrics {
  total_jobs: number
  completed_jobs: number
  failed_jobs: number
  retried_jobs: number
  dead_letter_jobs: number
  active_workers: number
  unhealthy_workers: number
  total_workers: number
  average_execution_time_ms: number | null
  queue_throughput: Record<string, number>
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface ApiError {
  error: {
    code: string
    message: string
  }
}
