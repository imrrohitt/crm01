import { createContext, useContext, useEffect, useState } from 'react'
import { Navigate, Outlet, useParams } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import type { CompanyDetail } from '../types'
import { Sidebar } from './Sidebar'

export const lastCompany = {
  get(): string | null {
    try {
      return localStorage.getItem('icrm.company')
    } catch {
      return null
    }
  },
  set(id: string) {
    try {
      localStorage.setItem('icrm.company', id)
    } catch {
      /* ignore */
    }
  },
}

const CompanyContext = createContext<CompanyDetail | null>(null)

export function useCompany(): CompanyDetail {
  const c = useContext(CompanyContext)
  if (!c) throw new Error('useCompany must be used inside CompanyLayout')
  return c
}

export function CompanyLayout() {
  const { companyId = '' } = useParams()
  const [company, setCompany] = useState<CompanyDetail | null>(null)
  const [error, setError] = useState<'notfound' | 'failed' | null>(null)

  useEffect(() => {
    let cancelled = false
    setCompany(null)
    setError(null)
    api
      .company(companyId)
      .then((c) => {
        if (cancelled) return
        setCompany(c)
        lastCompany.set(c.id)
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof ApiError && e.status === 404 ? 'notfound' : 'failed')
      })
    return () => {
      cancelled = true
    }
  }, [companyId])

  if (error === 'notfound') return <Navigate to="/accounts/companies" replace />
  if (error === 'failed') return <div className="screen-center">Could not load this company. Please refresh.</div>
  if (!company) return <div className="screen-center">Loading…</div>

  return (
    <CompanyContext.Provider value={company}>
      <div className="app-shell">
        <Sidebar />
        <div className="main-area">
          <header className="topbar">
            <span className="topbar-company">{company.name}</span>
            <span className="muted">{company.subscription.plan ? `${company.subscription.plan} plan` : 'No plan'}</span>
          </header>
          <main className="content">
            <Outlet />
          </main>
        </div>
      </div>
    </CompanyContext.Provider>
  )
}
