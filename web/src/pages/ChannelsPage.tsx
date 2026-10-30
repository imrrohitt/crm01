import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { useCompany } from '../layout/CompanyLayout'
import type { Channel, ChannelAccount, InstagramConnection, InstagramProfile, WebhookPreview } from '../types'

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
  const [modalOpen, setModalOpen] = useState(false)
  const [appId, setAppId] = useState('')
  const [accessToken, setAccessToken] = useState('')
  const [profile, setProfile] = useState<InstagramProfile | null>(null)
  const [webhook, setWebhook] = useState<WebhookPreview | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

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

  function openConnect() {
    setAppId('')
    setAccessToken('')
    setProfile(null)
    setWebhook(null)
    setFormError(null)
    setModalOpen(true)
  }

  function editCredentials(nextAppId: string, nextToken: string) {
    setAppId(nextAppId)
    setAccessToken(nextToken)
    setProfile(null)
    setWebhook(null)
    setFormError(null)
  }

  async function verifyAccount() {
    setBusy('verify')
    setFormError(null)
    try {
      setProfile(await api.verifyInstagram(company.id, appId.trim(), accessToken.trim()))
      setWebhook(null)
    } catch (e) {
      setProfile(null)
      setFormError(e instanceof ApiError ? e.message : 'Could not verify this Instagram account.')
    } finally {
      setBusy(null)
    }
  }

  async function generateWebhook() {
    setBusy('webhook')
    setFormError(null)
    try {
      setWebhook(await api.previewInstagramWebhook(company.id, appId.trim()))
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : 'Could not generate the webhook.')
    } finally {
      setBusy(null)
    }
  }

  async function connect(event: FormEvent) {
    event.preventDefault()
    if (!profile || !webhook) return
    setBusy('instagram')
    setFormError(null)
    try {
      await api.connectInstagram(company.id, appId.trim(), accessToken.trim(), webhook)
      setModalOpen(false)
      setNotice({ kind: 'ok', text: 'Instagram account connected.' })
      load()
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : 'Could not save the connection.')
    } finally {
      setBusy(null)
    }
  }

  async function copy(value: string) {
    try {
      await navigator.clipboard.writeText(value)
      setNotice({ kind: 'ok', text: 'Copied.' })
    } catch {
      setNotice({ kind: 'error', text: 'Could not copy. Select the value and copy it manually.' })
    }
  }

  async function disconnectConnection(connection: InstagramConnection) {
    if (!window.confirm(`Disconnect Instagram account ${connection.instagram_app_id}?`)) return
    setBusy(connection.id)
    try {
      await api.disconnectInstagram(company.id, connection.id)
      load()
    } catch (e) {
      setNotice({ kind: 'error', text: e instanceof ApiError ? e.message : 'Could not disconnect.' })
    } finally {
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
          const connections = ch.connections ?? []
          const connectedCount = live.length + connections.length
          const atLimit = ch.limit !== null && connectedCount >= ch.limit
          return (
            <section className="card channel-card" key={ch.key} aria-label={ch.name}>
              <header className="channel-head">
                {Logo && <Logo />}
                <div>
                  <h2>{ch.name}</h2>
                  <span className="muted small">
                    {connectedCount} connected{ch.limit !== null ? ` · plan allows ${ch.limit}` : ''}
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

              {connections.map((connection) => (
                <ConnectionDetails key={connection.id} connection={connection} canManage={canManage} busy={busy === connection.id} onCopy={copy} onDisconnect={() => disconnectConnection(connection)} />
              ))}

              {!ch.configured && <p className="muted small">A public webhook URL is not configured on the server yet.</p>}
              {canManage ? (
                <button className="btn btn-primary" disabled={!ch.configured || atLimit || busy === ch.key} onClick={openConnect}>
                  {connections.length ? 'Connect another account' : 'Connect to Instagram'}
                </button>
              ) : (
                <p className="muted small">Ask a company owner or admin to connect channels.</p>
              )}
              {atLimit && canManage && <p className="muted small">Plan limit reached.</p>}
            </section>
          )
        })}
      </div>

      {modalOpen && (
        <div className="modal-backdrop" onClick={() => busy === null && setModalOpen(false)}>
          <form className="modal" role="dialog" aria-modal="true" aria-labelledby="ig-connect-title" onClick={(e) => e.stopPropagation()} onSubmit={connect}>
            <h2 id="ig-connect-title">Connect Instagram</h2>
            <p className="muted small">Enter the Instagram id and access token, verify the profile, then generate the webhook.</p>
            {formError && <div className="alert" role="alert">{formError}</div>}
            <label htmlFor="ig-app-id">Instagram app id</label>
            <input id="ig-app-id" value={appId} onChange={(e) => editCredentials(e.target.value, accessToken)} autoComplete="off" required />
            <label htmlFor="ig-token">Access token</label>
            <textarea id="ig-token" value={accessToken} onChange={(e) => editCredentials(appId, e.target.value)} rows={4} autoComplete="off" required />
            <div className="modal-actions">
              <button type="button" className="btn" disabled={busy !== null} onClick={() => setModalOpen(false)}>Cancel</button>
              <button type="button" className="btn btn-primary" disabled={busy !== null || !appId.trim() || !accessToken.trim()} onClick={verifyAccount}>
                {busy === 'verify' ? 'Verifying…' : 'Verify'}
              </button>
            </div>
            {profile && (
              <div className="profile-found">
                {profile.profile_picture_url ? <img className="avatar-img" src={profile.profile_picture_url} alt="" /> : <span className="avatar">{(profile.username ?? profile.name ?? '?')[0].toUpperCase()}</span>}
                <span className="account-meta">
                  <strong>{profile.name || profile.username || profile.id}</strong>
                  <small className="muted">{profile.username ? `@${profile.username} · ` : ''}Profile found</small>
                </span>
              </div>
            )}
            {profile && !webhook && (
              <button type="button" className="btn btn-primary" disabled={busy !== null} onClick={generateWebhook}>
                {busy === 'webhook' ? 'Generating…' : 'Generate webhook'}
              </button>
            )}
            {webhook && (
              <>
                <label className="small">Webhook URL</label>
                <div className="copy-row">
                  <code>{webhook.webhook_url}</code>
                  <button type="button" className="btn btn-small" onClick={() => copy(webhook.webhook_url)}>Copy</button>
                </div>
                <label className="small">Verify token</label>
                <div className="copy-row">
                  <code>{webhook.webhook_verify_token}</code>
                  <button type="button" className="btn btn-small" onClick={() => copy(webhook.webhook_verify_token)}>Copy</button>
                </div>
                <button type="submit" className="btn btn-primary" disabled={busy !== null}>{busy === 'instagram' ? 'Saving…' : 'Submit'}</button>
              </>
            )}
          </form>
        </div>
      )}
    </div>
  )
}

function ConnectionDetails({ connection, canManage, busy, onCopy, onDisconnect }: {
  connection: InstagramConnection
  canManage: boolean
  busy: boolean
  onCopy: (value: string) => void
  onDisconnect: () => void
}) {
  return (
    <div className="connection-box">
      <div className="connection-head">
        {connection.profile_picture_url ? <img className="avatar-img" src={connection.profile_picture_url} alt="" /> : <span className="avatar">{(connection.username ?? connection.name ?? '?')[0].toUpperCase()}</span>}
        <span className="account-meta">
          <strong>{connection.name || connection.username || connection.instagram_app_id}</strong>
          <small className="muted">{connection.username ? `@${connection.username} · ` : ''}Connected</small>
        </span>
        {canManage && (
          <button className="btn btn-small" disabled={busy} onClick={onDisconnect}>Disconnect</button>
        )}
      </div>
      <label className="small">Webhook URL</label>
      <div className="copy-row">
        <code>{connection.webhook_url}</code>
        <button type="button" className="btn btn-small" onClick={() => onCopy(connection.webhook_url)}>Copy</button>
      </div>
      <label className="small">Verify token</label>
      <div className="copy-row">
        <code>{connection.webhook_verify_token}</code>
        <button type="button" className="btn btn-small" onClick={() => onCopy(connection.webhook_verify_token)}>Copy</button>
      </div>
    </div>
  )
}
