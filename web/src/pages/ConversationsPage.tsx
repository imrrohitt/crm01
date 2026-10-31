import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'
import { Avatar, formatWhen, personFacts } from '../components/Avatar'
import { useCompany } from '../layout/CompanyLayout'
import type { ConversationDetail, ConversationSummary } from '../types'

export function ConversationsPage() {
  const company = useCompany()
  const [rows, setRows] = useState<ConversationSummary[] | null>(null)
  const [selected, setSelected] = useState<ConversationDetail | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(() => {
    api
      .conversations(company.id)
      .then(setRows)
      .catch((e) => setNotice(e instanceof ApiError ? e.message : 'Could not load conversations.'))
  }, [company.id])

  useEffect(load, [load])

  async function open(row: ConversationSummary) {
    setNotice(null)
    try {
      setSelected(await api.conversation(company.id, row.id))
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : 'Could not open this conversation.')
    }
  }

  return (
    <div className="page">
      <h1>Conversations</h1>
      <p className="muted lead">DM threads for contacts synced from Instagram.</p>
      {notice && <div className="alert" role="alert">{notice}</div>}
      {!rows && !notice && <p className="muted">Loading…</p>}
      <div className="conversation-layout">
        <ul className="account-list">
          {rows?.map((row) => (
            <li key={row.id}>
              <button className={`conversation-pick ${selected?.id === row.id ? 'is-active' : ''}`} onClick={() => open(row)}>
                <Avatar name={row.contact_name} src={row.contact_profile_picture_url} />
                <span className="account-meta">
                  <strong>{row.contact_name}</strong>
                  <small className="muted">{row.contact_username ? `@${row.contact_username}` : 'Instagram user'}</small>
                  <small className="muted">{row.last_message || 'No text'}{row.last_message_at ? ` · ${formatWhen(row.last_message_at)}` : ''}</small>
                </span>
              </button>
            </li>
          ))}
        </ul>
        <section className="card thread" aria-label="Messages">
          {!selected && <p className="muted">Select a conversation.</p>}
          {selected && (
            <>
              <div className="thread-head">
                <Avatar large name={selected.contact_name} src={selected.contact_profile_picture_url} />
                <span className="account-meta">
                  <h2>{selected.contact_name}</h2>
                  <small className="muted">{personFacts(selected).join(' · ')}</small>
                </span>
              </div>
              <ol className="thread-list">
                {selected.messages.map((message) => (
                  <li key={message.id} className={message.direction === 'outbound' ? 'is-out' : 'is-in'}>
                    <span>{message.content || (message.message_type === 'text' ? '' : 'Attachment')}</span>
                    {message.sent_at && <small>{formatWhen(message.sent_at)}</small>}
                  </li>
                ))}
              </ol>
            </>
          )}
        </section>
      </div>
      {rows && rows.length === 0 && <p className="muted">No conversations yet. Enable contact sync first.</p>}
    </div>
  )
}
