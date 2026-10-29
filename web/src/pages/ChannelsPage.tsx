import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { useCompany } from '../layout/CompanyLayout'
import type { Channel, ChannelAccount } from '../types'

function InstagramLogo({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" role="img" aria-label="Instagram">
      <defs>
        <radialGradient id="ig-grad" cx="30%" cy="107%" r="150%">
          <stop offset="0" stopColor="#fdf497" />
          <stop offset="0.1" stopColor="#fdf497" />
          <stop offset="0.45" stopColor="#fd5949" />
          <stop offset="0.6" stopColor="#d6249f" />
          <stop offset="0.9" stopColor="#285AEB" />
        </radialGradient>
      </defs>
      <rect width="48" height="48" rx="12" fill="url(#ig-grad)" />
      <rect x="12" y="12" width="24" height="24" rx="7" fill="none" stroke="#fff" strokeWidth="2.6" />
      <circle cx="24" cy="24" r="5.6" fill="none" stroke="#fff" strokeWidth="2.6" />
      <circle cx="31.2" cy="16.8" r="1.7" fill="#fff" />
    </svg>
  )
}

const LOGOS: Record<string, (p: { size?: number }) => JSX.Element> = { instagram: InstagramLogo }

export function ChannelsPage() {
  const company = useCompany()
  const [params, setParams] = useSearchParams()
  const [channels, setChannels] = useState<Channel[] | null>(null)
  const [canManage, setCanManage] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)

  const load = useCallback(() => {
    api
      .channels(company.id)
      .then((r) => {
        setChannels(r.channels)
        setCanManage(r.can_manage)
      })
      .catch((e) => setNotice({ kind: 'error', text: e instanceof ApiError ? e.message : 'Could not load channels.' }))
  }, [company.id])

  useEffect(load, [load])

  // Result of the Instagram redirect: ?connected=instagram or ?channel_error=...
  useEffect(() => {
    const connected = params.get('connected')
    const error = params.get('channel_error')
    if (!connected && !error) return
    setNotice(connected ? { kind: 'ok', text: 'Instagram connected successfully.' } : { kind: 'error', text: error ?? '' })
    setParams({}, { replace: true })
  }, [params, setParams])

  async function connect(channel: Channel) {
    setBusy(channel.key)
    setNotice(null)
    try {
      const { authorize_url } = await api.connectInstagram(company.id)
      window.location.href = authorize_url // leave the app and log in on Instagram
    } catch (e) {
      setNotice({ kind: 'error', text: e instanceof ApiError ? e.message : 'Could not start the connection.' })
      setBusy(null)
    }
  }

  async function disconnect(account: ChannelAccount) {
    if (!window.confirm(`Disconnect @${account.username ?? account.platform_account_id}? You can reconnect later.`)) return
    setBusy(account.id)
    try {
      await api.disconnectInstagram(company.id, account.id)
      load()
    } catch (e) {
      setNotice({ kind: 'error', text: e instanceof ApiError ? e.message : 'Could not disconnect.' })
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="page">
      <h1>Channels</h1>
      <p className="muted lead">Connect the channels you talk to your audience on.</p>

      {notice && (
        <div className={notice.kind === 'ok' ? 'alert alert-ok' : 'alert'} role={notice.kind === 'ok' ? 'status' : 'alert'}>
          {notice.text}
        </div>
      )}
      {!channels && !notice && <p className="muted">Loading…</p>}

      <div className="channel-grid">
        {channels?.map((ch) => {
          const Logo = LOGOS[ch.key]
          const live = ch.accounts.filter((a) => a.status !== 'disconnected')
          const atLimit = ch.limit !== null && live.length >= ch.limit
          return (
            <section className="card channel-card" key={ch.key} aria-label={ch.name}>
              <header className="channel-head">
                {Logo && <Logo />}
                <div>
                  <h2>{ch.name}</h2>
                  <span className="muted small">
                    {live.length} connected{ch.limit !== null ? ` · plan allows ${ch.limit}` : ''}
                  </span>
                </div>
              </header>

              {live.length > 0 && (
                <ul className="account-list">
                  {live.map((a) => (
                    <li key={a.id}>
                      {a.profile_picture_url ? <img className="avatar-img" src={a.profile_picture_url} alt="" /> : <span className="avatar">{(a.username ?? '?')[0].toUpperCase()}</span>}
                      <span className="account-meta">
                        <strong>@{a.username ?? a.platform_account_id}</strong>
                        <small className={a.status === 'error' ? 'text-danger' : 'muted'}>
                          {a.status === 'error' ? 'Needs reconnecting' : (a.account_type ?? 'connected').toLowerCase()}
                        </small>
                      </span>
                      {canManage && (
                        <button className="btn btn-small" disabled={busy === a.id} onClick={() => disconnect(a)}>
                          Disconnect
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              )}

              {!ch.configured && <p className="muted small">Instagram is not configured on the server yet.</p>}
              {canManage ? (
                <button className="btn btn-primary" disabled={!ch.configured || atLimit || busy === ch.key} onClick={() => connect(ch)}>
                  {busy === ch.key ? 'Redirecting…' : live.length ? 'Connect another account' : 'Connect to Instagram'}
                </button>
              ) : (
                <p className="muted small">Ask a company owner or admin to connect channels.</p>
              )}
              {atLimit && canManage && <p className="muted small">Plan limit reached.</p>}
            </section>
          )
        })}
      </div>
    </div>
  )
}
