import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { getToken } from '../services/api'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { loading } = useAuth()

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-slate-500">Loading…</div>
  }

  if (!getToken()) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
