import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { Icon } from '../components/Icon'
import { Logo } from '../components/Logo'
import { Scene } from '../components/Scene'

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
      <section className="login-hero">
        <Scene variant="hero" />
        <div className="brand brand-lg">
          <Logo size={38} />
          <span className="brand-name">insta<b>.crm</b></span>
        </div>
        <div className="hero-copy">
          <span className="eyebrow">Instagram relationship platform</span>
          <h2>Every DM, <em>a relationship</em> worth keeping.</h2>
          <p>One shared workspace for your team to track every contact, conversation and lead from Instagram.</p>
          <ul className="login-points">
            {['Unified inbox for all connected accounts', 'Contacts synced automatically', 'Role-based access for your whole team'].map((t) => (
              <li key={t}><span className="tick"><Icon name="check" size={14} /></span>{t}</li>
            ))}
          </ul>
        </div>
        <small>© {new Date().getFullYear()} insta.crm</small>
      </section>

      <section className="login-panel">
        <form className="login-card" onSubmit={onSubmit} noValidate>
          <h1>Welcome back</h1>
          <p className="muted">Sign in to your workspace to continue.</p>

          {error && <div className="alert" role="alert">{error}</div>}

          <label htmlFor="email">Email</label>
          <div className="field">
            <Icon name="mail" size={17} />
            <input id="email" type="email" placeholder="you@company.com" autoComplete="username" autoFocus required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>

          <label htmlFor="password">Password</label>
          <div className="field">
            <Icon name="lock" size={17} />
            <input id="password" type={show ? 'text' : 'password'} placeholder="••••••••" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
            <button type="button" className="link-btn" onClick={() => setShow((s) => !s)} aria-label={show ? 'Hide password' : 'Show password'}>
              <Icon name={show ? 'eyeOff' : 'eye'} size={17} />
            </button>
          </div>

          <button className="btn btn-primary" type="submit" disabled={busy || !email || !password}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </section>
    </main>
  )
}
