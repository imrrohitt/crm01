import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'

export function LoginPage() {
  const { user, loading, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (!loading && user) return <Navigate to={from?.startsWith('/accounts') ? from : '/accounts/companies'} replace />

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const s = await login(email.trim(), password)
      // The company id goes in the URL: /accounts/companies/<id>
      navigate(from?.startsWith('/accounts') ? from : `/accounts/companies/${s.default_company_id}`, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={onSubmit} noValidate>
        <div className="brand brand-lg">
          <span className="brand-mark">IC</span>
          <span>Insta CRM</span>
        </div>
        <h1>Sign in</h1>
        <p className="muted">Use your work email to continue.</p>

        {error && <div className="alert" role="alert">{error}</div>}

        <label htmlFor="email">Email</label>
        <input id="email" type="email" autoComplete="username" autoFocus required value={email} onChange={(e) => setEmail(e.target.value)} />

        <label htmlFor="password">Password</label>
        <div className="password-row">
          <input id="password" type={show ? 'text' : 'password'} autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          <button type="button" className="link-btn" onClick={() => setShow((s) => !s)}>{show ? 'Hide' : 'Show'}</button>
        </div>

        <button className="btn btn-primary" type="submit" disabled={busy || !email || !password}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </main>
  )
}
