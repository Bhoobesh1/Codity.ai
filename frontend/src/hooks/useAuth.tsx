import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, clearToken, getToken, setToken } from '../services/api'
import type { User } from '../types/api'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

interface TokenResponse {
  access_token: string
  token_type: string
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchCurrentUser = useCallback(async () => {
    // There's no GET /me endpoint yet, so we treat "has a valid token
    // and /organizations doesn't 401" as "logged in". We store the
    // logged-in user's basic info at login/register time instead.
    const stored = localStorage.getItem('scheduler_user')
    if (getToken() && stored) {
      setUser(JSON.parse(stored))
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchCurrentUser()
  }, [fetchCurrentUser])

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<TokenResponse>('/auth/login', { email, password })
    setToken(res.access_token)
    // We don't have the user's profile from /login, so store what we know.
    const fallbackUser: User = { id: '', email, full_name: email, is_active: true }
    localStorage.setItem('scheduler_user', JSON.stringify(fallbackUser))
    setUser(fallbackUser)
  }, [])

  const register = useCallback(async (email: string, password: string, fullName: string) => {
    const newUser = await api.post<User>('/auth/register', {
      email,
      password,
      full_name: fullName,
    })
    const res = await api.post<TokenResponse>('/auth/login', { email, password })
    setToken(res.access_token)
    localStorage.setItem('scheduler_user', JSON.stringify(newUser))
    setUser(newUser)
  }, [])

  const logout = useCallback(() => {
    clearToken()
    localStorage.removeItem('scheduler_user')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
