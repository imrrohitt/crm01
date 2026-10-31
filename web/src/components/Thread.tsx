import { Avatar, personFacts } from './Avatar'
import { Icon } from './Icon'
import type { ConversationDetail } from '../types'

function dayLabel(value: string): string {
  const d = new Date(value)
  const today = new Date()
  const diff = Math.round((new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime() - new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()) / 86400000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  return d.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })
}

const time = (v: string) => new Date(v).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })

export function ThreadHead({ conversation, onClose }: { conversation: ConversationDetail; onClose?: () => void }) {
  return (
    <div className="chat-head">
      {onClose && (
        <button className="icon-btn" onClick={onClose} aria-label="Back to list"><Icon name="chevronLeft" size={16} /></button>
      )}
      <Avatar large name={conversation.contact_name} src={conversation.contact_profile_picture_url} />
      <span className="account-meta">
        <h2>{conversation.contact_name}</h2>
        <small className="muted">{personFacts(conversation).join(' · ') || 'Instagram user'}</small>
      </span>
      <span className={`badge ${conversation.status === 'open' ? 'badge-success' : 'badge-muted'}`}>{conversation.status}</span>
    </div>
  )
}

export function ThreadMessages({ conversation }: { conversation: ConversationDetail }) {
  let lastDay = ''
  return (
    <div className="chat-body">
      {conversation.messages.length === 0 && <div className="chat-empty"><strong>No messages yet</strong></div>}
      {conversation.messages.map((m) => {
        const day = m.sent_at ? dayLabel(m.sent_at) : ''
        const sep = day && day !== lastDay
        if (day) lastDay = day
        return (
          <div key={m.id} style={{ display: 'contents' }}>
            {sep && <span className="day-sep">{day}</span>}
            <div className={`bubble ${m.direction === 'outbound' ? 'is-out' : 'is-in'}`}>
              {m.content || (m.message_type === 'text' ? '' : `[${m.message_type}]`)}
              {m.sent_at && <small>{time(m.sent_at)}</small>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function Composer() {
  return (
    <div className="composer">
      <input disabled placeholder="Replying from the CRM is coming soon…" aria-label="Reply (coming soon)" />
      <button className="btn btn-primary" disabled><Icon name="send" size={16} />Send</button>
    </div>
  )
}
