import { useEffect, useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Avatar } from '../components/Avatar'
import { Icon } from '../components/Icon'
import { Logo } from '../components/Logo'
import { useCompany } from './CompanyLayout'
import { GROUP_LABEL, NAV, type NavItem } from './nav'

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
  const groups = (['main', 'grow', 'workspace'] as NavItem['group'][]).map((g) => ({ g, items: items.filter((n) => n.group === g) })).filter((x) => x.items.length)
  const displayName = user?.full_name ?? user?.email ?? '?'

  function switchCompany(id: string) {
    const section = location.pathname.replace(base, '')
    navigate(`/accounts/companies/${id}${section}`)
  }

  return (
    <aside className={`sidebar ${collapsed ? 'is-collapsed' : ''}`} aria-label="Primary">
      <div className="sidebar-head">
        <div className="brand">
          <Logo size={34} />
          {!collapsed && <span className="brand-name">insta<b>.crm</b></span>}
        </div>
        <button className="icon-btn" onClick={toggle} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} aria-expanded={!collapsed}>
          <Icon name={collapsed ? 'chevronRight' : 'chevronLeft'} size={16} />
        </button>
      </div>

      {!collapsed && companies.length > 1 && (
        <div className="company-switch-wrap">
          <select className="company-switch" value={company.id} onChange={(e) => switchCompany(e.target.value)} aria-label="Switch company">
            {companies.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <Icon name="chevronDown" size={14} />
        </div>
      )}

      <nav className="nav">
        {groups.map(({ g, items: list }) => (
          <div className="nav-group" key={g}>
            {!collapsed && <span className="nav-label">{GROUP_LABEL[g]}</span>}
            {list.map((n) => (
              <NavLink
                key={n.path}
                to={n.path ? `${base}/${n.path}` : base}
                end={n.path === ''}
                className={({ isActive }) => `nav-item ${isActive ? 'is-active' : ''}`}
                title={collapsed ? n.label : undefined}
              >
                <Icon name={n.icon} size={19} />
                {!collapsed && <span>{n.label}</span>}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-foot">
        <div className="user-chip" title={collapsed ? displayName : undefined}>
          <Avatar name={displayName} src={user?.avatar_url} />
          {!collapsed && (
            <span className="user-meta">
              <strong>{displayName}</strong>
              <small>{company.roles.join(', ')}</small>
            </span>
          )}
          <button className="icon-btn icon-btn-ghost" onClick={() => { logout(); navigate('/login', { replace: true }) }} title="Sign out" aria-label="Sign out">
            <Icon name="logout" size={16} />
          </button>
        </div>
      </div>
    </aside>
  )
}
