import { useState } from 'react'
import { Link } from 'react-router-dom'
import { usePolling } from '../hooks/usePolling'
import { api, ApiRequestError } from '../services/api'
import type { Organization, Page, Project } from '../types/api'
import { Card, EmptyState, ErrorBanner, PageHeader } from '../components/ui'

export function ProjectsPage() {
  const { data: orgs, refetch: refetchOrgs } = usePolling<Organization[]>(
    () => api.get('/organizations'),
    10000,
  )
  const { data: projectsPage, error, refetch: refetchProjects } = usePolling<Page<Project>>(
    () => api.get('/projects?page=1&page_size=50'),
    6000,
  )

  const [showNewOrg, setShowNewOrg] = useState(false)
  const [showNewProject, setShowNewProject] = useState(false)

  return (
    <div>
      <PageHeader
        title="Projects"
        subtitle="Organizations and the projects within them"
        action={
          <div className="flex gap-2">
            <button
              onClick={() => setShowNewOrg((v) => !v)}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              New organization
            </button>
            <button
              onClick={() => setShowNewProject((v) => !v)}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
            >
              New project
            </button>
          </div>
        }
      />

      {showNewOrg && (
        <NewOrgForm
          onDone={() => {
            setShowNewOrg(false)
            refetchOrgs()
          }}
        />
      )}
      {showNewProject && orgs && (
        <NewProjectForm
          orgs={orgs}
          onDone={() => {
            setShowNewProject(false)
            refetchProjects()
          }}
        />
      )}

      {error && <ErrorBanner message={error} />}

      {projectsPage && projectsPage.items.length === 0 && (
        <EmptyState message="No projects yet. Create an organization, then a project, to get started." />
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {projectsPage?.items.map((project) => {
          const org = orgs?.find((o) => o.id === project.organization_id)
          return (
            <Link key={project.id} to={`/projects/${project.id}`}>
              <Card className="h-full transition-shadow hover:shadow-md">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                  {org?.name ?? 'Organization'}
                </p>
                <h3 className="mt-1 font-semibold text-slate-900">{project.name}</h3>
                {project.description && (
                  <p className="mt-1 text-sm text-slate-500 line-clamp-2">{project.description}</p>
                )}
              </Card>
            </Link>
          )
        })}
      </div>
    </div>
  )
}

function NewOrgForm({ onDone }: { onDone: () => void }) {
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    try {
      await api.post('/organizations', { name })
      onDone()
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Failed to create organization.')
    }
  }

  return (
    <Card className="mb-4">
      <form onSubmit={submit} className="flex items-end gap-3">
        <div className="flex-1">
          <label className="block text-xs font-medium text-slate-600">Organization name</label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          />
        </div>
        <button type="submit" className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white">
          Create
        </button>
      </form>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </Card>
  )
}

function NewProjectForm({ orgs, onDone }: { orgs: Organization[]; onDone: () => void }) {
  const [name, setName] = useState('')
  const [organizationId, setOrganizationId] = useState(orgs[0]?.id ?? '')
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    try {
      await api.post('/projects', { organization_id: organizationId, name })
      onDone()
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Failed to create project.')
    }
  }

  if (orgs.length === 0) {
    return (
      <Card className="mb-4">
        <p className="text-sm text-slate-500">Create an organization first.</p>
      </Card>
    )
  }

  return (
    <Card className="mb-4">
      <form onSubmit={submit} className="flex items-end gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-600">Organization</label>
          <select
            value={organizationId}
            onChange={(e) => setOrganizationId(e.target.value)}
            className="mt-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          >
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-xs font-medium text-slate-600">Project name</label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          />
        </div>
        <button type="submit" className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white">
          Create
        </button>
      </form>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </Card>
  )
}
