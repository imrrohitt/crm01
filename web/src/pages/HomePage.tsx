import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { Avatar, relativeTime } from '../components/Avatar'
import { AreaChart, Donut, Sparkline } from '../components/charts'
import { Icon, type IconName } from '../components/Icon'
import { Scene } from '../components/Scene'
import { bucketByDay, compact, cumulative, sum, trend } from '../lib/stats'
import { useCompany } from '../layout/CompanyLayout'
import type { ConversationSummary, CrmContact, SyncAccount } from '../types'

function Delta({ value }: { value: number | null }) {
  if (value === null) return <span className="delta delta-flat">— vs last 7d</span>
  const cls = value > 0 ? 'delta-up' : value < 0 ? 'delta-down' : 'delta-flat'
  return (
    <span className={`delta ${cls}`}>
      {value !== 0 && <Icon name={value > 0 ? 'arrowUp' : 'arrowDown'} size={12} />}
      {Math.abs(value)}% <span style={{ fontWeight: 500, opacity: .75 }}>vs last 7d</span>
    </span>
  )
}

function Kpi({ label, value, icon, tone, spark, delta, color }: { label: string; value: string; icon: IconName; tone?: string; spark: number[]; delta: number | null; color: string }) {
  return (
    <div className="card kpi">
      <div className="kpi-top">
        <span className={`kpi-icon ${tone ?? ''}`}><Icon name={icon} size={19} /></span>
        <Sparkline values={spark} color={color} />
      </div>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
      <div className="kpi-foot"><Delta value={delta} /></div>
    </div>
  )
}

export function HomePage() {
  const company = useCompany()
  const base = `/accounts/companies/${company.id}`
  const [contacts, setContacts] = useState<CrmContact[] | null>(null)
  const [accounts, setAccounts] = useState<SyncAccount[]>([])
  const [conversations, setConversations] = useState<ConversationSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [range, setRange] = useState<14 | 30>(30)

  useEffect(() => {
    api.contacts(company.id).then((d) => { setContacts(d.contacts); setAccounts(d.accounts) }).catch((e) => setError(e instanceof ApiError ? e.message : 'Could not load contacts.'))
    api.conversations(company.id).then(setConversations).catch((e) => setError(e instanceof ApiError ? e.message : 'Could not load conversations.'))
  }, [company.id])

  const stats = useMemo(() => {
    if (!contacts || !conversations) return null
    const newContacts = bucketByDay(contacts.map((c) => c.first_seen_at ?? c.created_at), 30)
    const activity = bucketByDay(conversations.map((c) => c.last_message_at), 30)
    const awaiting = conversations.filter((c) => c.last_direction === 'inbound').length
    const replied = conversations.length - awaiting
    const rate = conversations.length ? Math.round((replied / conversations.length) * 100) : 0
    const growth = cumulative(newContacts.counts, contacts.length - sum(newContacts.counts))
    return { newContacts, activity, awaiting, replied, rate, growth }
  }, [contacts, conversations])

  const features = company.subscription.features
  const igLimit = typeof features.instagram_accounts === 'number' ? features.instagram_accounts : null
  const first = (company.user.full_name ?? '').split(' ')[0]
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
  const loading = !stats && !error
  const days = range

  return (
    <div className="page">
      <section className="banner">
        <div className="banner-copy">
          <span className="eyebrow">{new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })}</span>
          <h1>{greeting}{first ? <>, <em>{first}</em></> : ''}</h1>
          <p>
            {stats && contacts && conversations
              ? <><b>{stats.awaiting}</b> {stats.awaiting === 1 ? 'conversation is' : 'conversations are'} waiting on you across <b>{contacts.length}</b> {contacts.length === 1 ? 'contact' : 'contacts'} in <b>{company.name}</b>.</>
              : <>Loading your latest Instagram activity…</>}
          </p>
          <div className="banner-actions">
            <Link className="btn btn-light" to={`${base}/inbox`}><Icon name="inbox" size={16} />Open inbox</Link>
            <Link className="btn btn-ghost-dark" to={`${base}/channels`}><Icon name="radio" size={16} />Channels</Link>
          </div>
        </div>
        <Scene variant="banner" />
      </section>

      {error && <div className="alert" role="alert">{error}</div>}

      {loading ? (
        <div className="kpi-grid">{[0, 1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 150 }} />)}</div>
      ) : (
        stats && contacts && conversations && (
          <>
            <div className="kpi-grid">
              <Kpi label="Total contacts" value={compact(contacts.length)} icon="users" spark={stats.growth.slice(-14)} delta={trend(stats.newContacts.counts)} color="#6d4aff" />
              <Kpi label="Conversations" value={compact(conversations.length)} icon="message" tone="tone-pink" spark={stats.activity.counts.slice(-14)} delta={trend(stats.activity.counts)} color="#db2777" />
              <Kpi label="Awaiting your reply" value={compact(stats.awaiting)} icon="clock" tone="tone-amber" spark={stats.activity.counts.slice(-14)} delta={null} color="#d97706" />
              <Kpi label="Reply rate" value={`${stats.rate}%`} icon="check" tone="tone-green" spark={stats.activity.counts.slice(-14)} delta={null} color="#16a34a" />
            </div>

            <div className="grid-2">
              <section className="card" aria-label="Activity">
                <div className="card-head">
                  <div>
                    <h2>Activity</h2>
                    <p className="muted small">New contacts and active conversations per day</p>
                  </div>
                  <div className="segmented" role="group" aria-label="Range">
                    {([14, 30] as const).map((r) => (
                      <button key={r} className={range === r ? 'is-active' : ''} onClick={() => setRange(r)}>{r}d</button>
                    ))}
                  </div>
                </div>
                <AreaChart
                  days={stats.newContacts.days.slice(-days)}
                  series={[
                    { label: 'New contacts', color: '#6d4aff', values: stats.newContacts.counts.slice(-days) },
                    { label: 'Active conversations', color: '#db2777', values: stats.activity.counts.slice(-days) },
                  ]}
                />
              </section>

              <section className="card" aria-label="Reply status">
                <div className="card-head">
                  <div>
                    <h2>Conversation status</h2>
                    <p className="muted small">Who spoke last</p>
                  </div>
                </div>
                <Donut
                  center={String(conversations.length)}
                  caption="threads"
                  slices={[
                    { label: 'Awaiting your reply', value: stats.awaiting, color: '#f59e0b' },
                    { label: 'You replied', value: stats.replied, color: '#6d4aff' },
                  ]}
                />
              </section>
            </div>

            <div className="grid-2">
              <section className="card" aria-label="Recent conversations">
                <div className="card-head">
                  <h2>Recent conversations</h2>
                  <Link className="link-btn" to={`${base}/inbox`}>View all</Link>
                </div>
                {conversations.length === 0 ? (
                  <div className="empty">
                    <Icon name="inboxEmpty" size={36} />
                    <strong>No conversations yet</strong>
                    <p>Connect an Instagram account and enable contact sync to import your DMs.</p>
                  </div>
                ) : (
                  <ul className="mini-list">
                    {conversations.slice(0, 6).map((c) => (
                      <li key={c.id}>
                        <Link className="row-btn" to={`${base}/inbox?c=${c.id}`}>
                          <Avatar name={c.contact_name} src={c.contact_profile_picture_url} />
                          <span className="row-main">
                            <strong>{c.contact_name}</strong>
                            <small>{c.last_direction === 'outbound' ? 'You: ' : ''}{c.last_message || 'No text'}</small>
                          </span>
                          <span className="row-side">
                            {relativeTime(c.last_message_at)}
                            {c.last_direction === 'inbound' && <span className="badge badge-warn">Needs reply</span>}
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <div style={{ display: 'grid', gap: 16, alignContent: 'start' }}>
                <section className="card" aria-label="Connected accounts">
                  <div className="card-head">
                    <h2>Instagram accounts</h2>
                    <Link className="link-btn" to={`${base}/channels`}>Manage</Link>
                  </div>
                  {igLimit !== null && (
                    <div className="usage">
                      <div className="usage-top"><span>Plan usage</span><b>{accounts.length} / {igLimit}</b></div>
                      <div className="bar"><i style={{ width: `${Math.min(100, (accounts.length / igLimit) * 100)}%` }} /></div>
                    </div>
                  )}
                  {accounts.length === 0 ? (
                    <p className="muted small">No account connected yet.</p>
                  ) : (
                    <ul className="mini-list">
                      {accounts.map((a) => (
                        <li key={a.id} className="row-btn" style={{ cursor: 'default' }}>
                          <Avatar name={a.name || a.username || 'I'} src={a.profile_picture_url} />
                          <span className="row-main">
                            <strong>{a.name || a.username || a.instagram_app_id}</strong>
                            <small>{a.username ? `@${a.username}` : a.instagram_app_id}</small>
                          </span>
                          <span className={`badge ${a.sync_status === 'synced' ? 'badge-success' : a.sync_status === 'failed' ? 'badge-warn' : 'badge-muted'}`}>
                            {a.sync_status === 'synced' ? 'Synced' : a.sync_status === 'failed' ? 'Failed' : a.contact_sync_enabled ? 'Syncing' : 'Sync off'}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                <section className="card" aria-label="Plan">
                  <div className="card-head">
                    <h2>Your plan</h2>
                    <span className="pill pill-primary">{company.subscription.plan ?? 'none'}</span>
                  </div>
                  <ul className="chips">
                    {Object.entries(features).map(([code, value]) => (
                      <li key={code} className={value === false ? 'chip is-off' : 'chip'}>
                        {code.replace(/_/g, ' ')}
                        {typeof value === 'number' && <b>{value}</b>}
                      </li>
                    ))}
                  </ul>
                </section>
              </div>
            </div>
          </>
        )
      )}
    </div>
  )
}
