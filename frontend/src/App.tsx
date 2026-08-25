import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './hooks/useAuth'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Layout } from './components/Layout'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { DashboardOverviewPage } from './pages/DashboardOverviewPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { QueueManagementPage } from './pages/QueueManagementPage'
import { JobExplorerPage } from './pages/JobExplorerPage'
import { JobDetailsPage } from './pages/JobDetailsPage'
import { WorkerMonitoringPage } from './pages/WorkerMonitoringPage'
import { DeadLetterQueuePage } from './pages/DeadLetterQueuePage'
import { MetricsPage } from './pages/MetricsPage'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<DashboardOverviewPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/projects/:projectId" element={<QueueManagementPage />} />
            <Route path="/queues/:queueId/jobs" element={<JobExplorerPage />} />
            <Route path="/jobs/:jobId" element={<JobDetailsPage />} />
            <Route path="/workers" element={<WorkerMonitoringPage />} />
            <Route path="/dead-letter-queue" element={<DeadLetterQueuePage />} />
            <Route path="/metrics" element={<MetricsPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
