import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
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
  const body = useRef<HTMLDivElement>(null)
  let lastDay = ''
  useEffect(() => {
    const node = body.current
    if (node) node.scrollTop = node.scrollHeight
  }, [conversation.messages])
  return (
    <div className="chat-body" ref={body}>
      {conversation.messages.length === 0 && <div className="chat-empty"><strong>No messages yet</strong></div>}
      {conversation.messages.map((m) => {
        const day = m.sent_at ? dayLabel(m.sent_at) : ''
        const sep = day && day !== lastDay
        if (day) lastDay = day
        const note = m.status === 'queued' ? 'Sending…' : m.status === 'failed' ? (m.send_error || 'Not sent') : m.sent_at ? time(m.sent_at) : ''
        return (
          <div key={m.id} style={{ display: 'contents' }}>
            {sep && <span className="day-sep">{day}</span>}
            <div className={`bubble ${m.direction === 'outbound' ? 'is-out' : 'is-in'} ${m.status === 'failed' ? 'is-failed' : ''}`}>
              {m.content || (m.message_type === 'text' ? '' : `[${m.message_type}]`)}
              {note && <small>{note}</small>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function Composer({ onSend, sending }: { onSend: (text: string) => Promise<void>; sending: boolean }) {
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const value = text.trim()
    if (!value || sending) return
    setError(null)
    try {
      await onSend(value)
      setText('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not send this message.')
    }
  }

  return (
    <form className="composer" onSubmit={submit}>
      {error && <p className="composer-error" role="alert">{error}</p>}
      <input
        value={text}
        maxLength={1000}
        placeholder="Write a message…"
        aria-label="Message"
        disabled={sending}
        onChange={(event) => setText(event.target.value)}
      />
      <button className="btn btn-primary" type="submit" disabled={sending || !text.trim()}>
        <Icon name="send" size={16} />{sending ? 'Sending' : 'Send'}
      </button>
    </form>
  )
}
