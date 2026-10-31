import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { Avatar, relativeTime } from '../components/Avatar'
import { Icon } from '../components/Icon'
import { Composer, ThreadHead, ThreadMessages } from '../components/Thread'
import { useCompany } from '../layout/CompanyLayout'
import type { ConversationDetail, ConversationSummary } from '../types'

type Filter = 'all' | 'needs_reply' | 'replied'

function applyPreview(rows: ConversationSummary[] | null, detail: ConversationDetail, text: string): ConversationSummary[] | null {
  if (!rows) return rows
  const next = rows.map((row) => row.id === detail.id
    ? { ...row, last_message: text, last_direction: 'outbound' as const, last_message_at: detail.last_message_at }
    : row)
  return [...next].sort((a, b) => (b.last_message_at || '').localeCompare(a.last_message_at || ''))
}

function useConversations() {
  const company = useCompany()
  const [rows, setRows] = useState<ConversationSummary[] | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [selected, setSelected] = useState<ConversationDetail | null>(null)
  const [opening, setOpening] = useState(false)
  const [sending, setSending] = useState(false)
  const pending = selected?.messages.some((message) => message.status === 'queued') ?? false

  useEffect(() => {
    api.conversations(company.id).then(setRows).catch((e) => setNotice(e instanceof ApiError ? e.message : 'Could not load conversations.'))
  }, [company.id])

  const open = useCallback(async (id: string) => {
    setNotice(null)
    setOpening(true)
    try {
      setSelected(await api.conversation(company.id, id))
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : 'Could not open this conversation.')
    } finally {
      setOpening(false)
    }
  }, [company.id])

  const send = useCallback(async (text: string) => {
    if (!selected) return
    setSending(true)
    try {
      const detail = await api.sendMessage(company.id, selected.id, text)
      setSelected(detail)
      setRows((current) => applyPreview(current, detail, text))
    } finally {
      setSending(false)
    }
  }, [company.id, selected])

  useEffect(() => {
    if (!selected || !pending) return
    const id = selected.id
    const timer = window.setInterval(async () => {
      try {
        const next = await api.conversation(company.id, id)
        setSelected((current) => (current?.id === id ? next : current))
        const preview = next.messages[next.messages.length - 1]
        if (preview) setRows((current) => applyPreview(current, next, preview.content || ''))
        if (!next.messages.some((message) => message.status === 'queued')) window.clearInterval(timer)
      } catch {
        /* the next tick tries again while the job is still sending */
      }
    }, 1500)
    return () => window.clearInterval(timer)
  }, [company.id, selected, pending])

  return { rows, notice, selected, setSelected, open, opening, send, sending }
}

function useFiltered(rows: ConversationSummary[] | null) {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const counts = useMemo(() => {
    const list = rows ?? []
    const needs = list.filter((r) => r.last_direction === 'inbound').length
    return { all: list.length, needs_reply: needs, replied: list.length - needs }
  }, [rows])
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (rows ?? []).filter((r) => {
      if (filter === 'needs_reply' && r.last_direction !== 'inbound') return false
      if (filter === 'replied' && r.last_direction === 'inbound') return false
      return !q || [r.contact_name, r.contact_username, r.last_message].some((v) => v?.toLowerCase().includes(q))
    })
  }, [rows, query, filter])
  return { query, setQuery, filter, setFilter, counts, filtered }
}

const FILTERS: [Filter, string][] = [['all', 'All'], ['needs_reply', 'Needs reply'], ['replied', 'Replied']]

function FilterChips({ filter, setFilter, counts }: { filter: Filter; setFilter: (f: Filter) => void; counts: Record<Filter, number> }) {
  return (
    <div className="toolbar" style={{ marginBottom: 0 }}>
      {FILTERS.map(([key, label]) => (
        <button key={key} className={`chip-btn ${filter === key ? 'is-active' : ''}`} onClick={() => setFilter(key)}>
          {label} <span className="count">{counts[key]}</span>
        </button>
      ))}
    </div>
  )
}

/** Chat-style inbox: list on the left, open thread on the right. */
export function InboxPage() {
  const { rows, notice, selected, setSelected, open, opening, send, sending } = useConversations()
  const { query, setQuery, filter, setFilter, counts, filtered } = useFiltered(rows)
  const [params] = useSearchParams()
  const wanted = params.get('c')

  useEffect(() => {
    if (wanted) open(wanted)
  }, [wanted, open])

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Inbox</h1>
          <p className="muted lead">Every Instagram DM thread in one place.</p>
        </div>
      </div>
      {notice && <div className="alert" role="alert">{notice}</div>}
      <div className={`inbox-shell ${selected ? 'has-selection' : ''}`}>
        <div className="inbox-list">
          <div className="inbox-list-head">
            <label className="search">
              <Icon name="search" size={16} />
              <input type="search" placeholder="Search conversations…" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search conversations" />
            </label>
            <FilterChips filter={filter} setFilter={setFilter} counts={counts} />
          </div>
          <div className="inbox-scroll">
            {!rows && [0, 1, 2, 3, 4].map((i) => <div key={i} className="skeleton" style={{ height: 60, margin: 6 }} />)}
            {rows && filtered.length === 0 && (
              <div className="empty"><Icon name="inboxEmpty" size={32} /><strong>{rows.length ? 'Nothing here' : 'No conversations yet'}</strong><p>{rows.length ? 'No threads match this filter.' : 'Enable contact sync on the Contacts page to import your DMs.'}</p></div>
            )}
            {filtered.map((r) => {
              const unread = r.last_direction === 'inbound'
              return (
                <button key={r.id} className={`thread-item ${selected?.id === r.id ? 'is-active' : ''} ${unread ? 'is-unread' : ''}`} onClick={() => open(r.id)}>
                  <Avatar large name={r.contact_name} src={r.contact_profile_picture_url} />
                  <span className="row-main">
                    <strong>{r.contact_name}</strong>
                    <small>{r.last_direction === 'outbound' ? 'You: ' : ''}{r.last_message || 'No text'}</small>
                  </span>
                  <span className="row-side">
                    {relativeTime(r.last_message_at)}
                    {unread && <span className="dot" aria-label="Needs reply" />}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        <section className="chat" aria-label="Messages">
          {!selected ? (
            <div className="chat-empty">
              <Icon name="message" size={44} />
              <strong>{opening ? 'Opening…' : 'Select a conversation'}</strong>
              <span>Pick a thread on the left to read the messages.</span>
            </div>
          ) : (
            <>
              <ThreadHead conversation={selected} onClose={() => setSelected(null)} />
              <ThreadMessages conversation={selected} />
              <Composer onSend={send} sending={sending} />
            </>
          )}
        </section>
      </div>
    </div>
  )
}

/** Table view of all threads; clicking one opens the messages in a drawer. */
export function ConversationsPage() {
  const { rows, notice, selected, setSelected, open, send, sending } = useConversations()
  const { query, setQuery, filter, setFilter, counts, filtered } = useFiltered(rows)

  useEffect(() => {
    if (!selected) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setSelected(null)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected, setSelected])

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Conversations</h1>
          <p className="muted lead">DM threads for contacts synced from Instagram.</p>
        </div>
      </div>
      {notice && <div className="alert" role="alert">{notice}</div>}

      <div className="toolbar">
        <label className="search">
          <Icon name="search" size={16} />
          <input type="search" placeholder="Search by name, username or message…" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search conversations" />
        </label>
        <FilterChips filter={filter} setFilter={setFilter} counts={counts} />
      </div>

      <section className="card table-card">
        {!rows ? (
          <div style={{ padding: 20, display: 'grid', gap: 10 }}>{[0, 1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 48 }} />)}</div>
        ) : filtered.length === 0 ? (
          <div className="empty">
            <Icon name="message" size={38} />
            <strong>{rows.length ? 'No conversations match' : 'No conversations yet'}</strong>
            <p>{rows.length ? 'Try a different search or filter.' : 'Enable contact sync on the Contacts page to import your DMs.'}</p>
          </div>
        ) : (
          <div className="table-scroll">
            <table className="table">
              <thead><tr><th>Contact</th><th>Last message</th><th>Status</th><th>Updated</th></tr></thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.id} onClick={() => open(r.id)} tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && open(r.id)}>
                    <td>
                      <div className="cell-person">
                        <Avatar name={r.contact_name} src={r.contact_profile_picture_url} />
                        <span className="row-main"><strong>{r.contact_name}</strong><small>{r.contact_username ? `@${r.contact_username}` : 'Instagram user'}</small></span>
                      </div>
                    </td>
                    <td style={{ maxWidth: 380 }}><div className="row-main"><small style={{ color: 'var(--text-2)' }}>{r.last_direction === 'outbound' ? 'You: ' : ''}{r.last_message || 'No text'}</small></div></td>
                    <td>{r.last_direction === 'inbound' ? <span className="badge badge-warn">Needs reply</span> : <span className="badge badge-success">Replied</span>}</td>
                    <td className="muted">{relativeTime(r.last_message_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selected && (
        <>
          <div className="drawer-backdrop" onClick={() => setSelected(null)} />
          <aside className="drawer" role="dialog" aria-modal="true" aria-label="Conversation">
            <div className="drawer-head">
              Conversation
              <button className="icon-btn" onClick={() => setSelected(null)} aria-label="Close"><Icon name="x" size={16} /></button>
            </div>
            <div className="drawer-body flush">
              <ThreadHead conversation={selected} />
              <ThreadMessages conversation={selected} />
              <Composer onSend={send} sending={sending} />
            </div>
          </aside>
        </>
      )}
    </div>
  )
}
