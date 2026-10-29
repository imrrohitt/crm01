import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { lastCompany } from '../layout/CompanyLayout'

/** /accounts/companies -> /accounts/companies/<id> (last used company, else the first one). */
export function CompanyRedirect() {
  const { companies, logout } = useAuth()
  const remembered = lastCompany.get()
  const target = companies.find((c) => c.id === remembered) ?? companies[0]
  if (!target) {
    return (
      <div className="screen-center">
        <p>You are not a member of any company yet.</p>
        <button className="btn" onClick={logout}>Sign out</button>
      </div>
    )
  }
  return <Navigate to={`/accounts/companies/${target.id}`} replace />
}
