import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, setSessionExpiredHandler, tokens } from '../api/client'
import type { Company, Session, User } from '../types'

interface AuthState {
  user: User | null
  companies: Company[]
  loading: boolean
  login: (email: string, password: string) => Promise<Session>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState<boolean>(() => tokens.access !== null)

  const logout = useCallback(() => {
    tokens.clear()
    setUser(null)
    setCompanies([])
  }, [])

  useEffect(() => {
    setSessionExpiredHandler(logout)
    if (!tokens.access) return
    api
      .me()
      .then((r) => {
        setUser(r.user)
        setCompanies(r.companies)
      })
      .catch(() => tokens.clear())
      .finally(() => setLoading(false))
  }, [logout])

  const login = useCallback(async (email: string, password: string) => {
    const s = await api.login(email, password)
    tokens.set(s.access_token, s.refresh_token)
    setUser(s.user)
    setCompanies(s.companies)
    return s
  }, [])

  const value = useMemo(() => ({ user, companies, loading, login, logout }), [user, companies, loading, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
