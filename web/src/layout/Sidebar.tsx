import { useEffect, useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useCompany } from './CompanyLayout'
import { NAV } from './nav'

function useCollapsed(): [boolean, () => void] {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      const stored = localStorage.getItem('icrm.sidebar')
      return stored ? stored === 'collapsed' : window.innerWidth <= 720
    } catch {
      return false
    }
  })
  useEffect(() => {
    try {
      localStorage.setItem('icrm.sidebar', collapsed ? 'collapsed' : 'open')
    } catch {
      /* ignore */
    }
  }, [collapsed])
  return [collapsed, () => setCollapsed((c) => !c)]
}

export function Sidebar() {
  const company = useCompany()
  const { companies, user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, toggle] = useCollapsed()
  const base = `/accounts/companies/${company.id}`
  const features = company.subscription.features
  const items = NAV.filter((n) => !n.feature || features[n.feature])
  const initials = (user?.full_name ?? user?.email ?? '?').slice(0, 1).toUpperCase()

  function switchCompany(id: string) {
    const section = location.pathname.replace(base, '')
    navigate(`/accounts/companies/${id}${section}`)
  }

  return (
    <aside className={`sidebar ${collapsed ? 'is-collapsed' : ''}`} aria-label="Primary">
      <div className="sidebar-head">
        <div className="brand">
          <span className="brand-mark">IC</span>
          {!collapsed && <span>Insta CRM</span>}
        </div>
        <button className="icon-btn" onClick={toggle} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} aria-expanded={!collapsed}>
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d={collapsed ? 'M9 6l6 6-6 6' : 'M15 6l-6 6 6 6'} />
          </svg>
        </button>
      </div>

      {!collapsed && companies.length > 1 && (
        <select className="company-switch" value={company.id} onChange={(e) => switchCompany(e.target.value)} aria-label="Switch company">
          {companies.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      )}

      <nav className="nav">
        {items.map((n) => (
          <NavLink
            key={n.path}
            to={n.path ? `${base}/${n.path}` : base}
            end={n.path === ''}
            className={({ isActive }) => `nav-item ${isActive ? 'is-active' : ''}`}
            title={collapsed ? n.label : undefined}
          >
            {n.icon}
            {!collapsed && <span>{n.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-foot">
        <div className="user-chip" title={collapsed ? (user?.full_name ?? user?.email) : undefined}>
          <span className="avatar">{initials}</span>
          {!collapsed && (
            <span className="user-meta">
              <strong>{user?.full_name ?? user?.email}</strong>
              <small>{company.roles.join(', ')}</small>
            </span>
          )}
        </div>
        <button className="nav-item signout" onClick={() => { logout(); navigate('/login', { replace: true }) }} title="Sign out">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
          </svg>
          {!collapsed && <span>Sign out</span>}
        </button>
      </div>
    </aside>
  )
}
