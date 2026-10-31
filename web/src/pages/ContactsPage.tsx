import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'
import { Avatar, formatWhen, personFacts } from '../components/Avatar'
import { useCompany } from '../layout/CompanyLayout'
import type { CrmContact, SyncAccount } from '../types'

export function ContactsPage() {
  const company = useCompany()
  const [accounts, setAccounts] = useState<SyncAccount[] | null>(null)
  const [contacts, setContacts] = useState<CrmContact[] | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)
  const [selected, setSelected] = useState<CrmContact | null>(null)
  const canManage = company.roles.includes('owner') || company.roles.includes('admin')

  const load = useCallback(() => {
    api
      .contacts(company.id)
      .then((data) => {
        setAccounts(data.accounts)
        setContacts(data.contacts)
      })
      .catch((e) => setNotice({ kind: 'error', text: e instanceof ApiError ? e.message : 'Could not load contacts.' }))
  }, [company.id])

  useEffect(load, [load])

  useEffect(() => {
    if (!selected) return
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setSelected(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected])

  async function enable(account: SyncAccount) {
    setBusy(account.id)
    setNotice(null)
    try {
      await api.enableContactSync(company.id, account.id)
      setNotice({ kind: 'ok', text: 'Sync started. Contacts and conversations will appear as the background job finishes.' })
      load()
    } catch (e) {
      setNotice({ kind: 'error', text: e instanceof ApiError ? e.message : 'Could not start sync.' })
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="page">
      <h1>Contacts</h1>
      <p className="muted lead">People who have sent a DM to a connected Instagram account.</p>
      {notice && <div className={notice.kind === 'ok' ? 'alert alert-ok' : 'alert'} role={notice.kind === 'ok' ? 'status' : 'alert'}>{notice.text}</div>}
      {!accounts && !notice && <p className="muted">Loading…</p>}

      <section className="card" aria-label="Instagram sync">
        <h2>Instagram</h2>
        {accounts && accounts.length === 0 && <p className="muted small">Connect an Instagram account in Channels first.</p>}
        <ul className="account-list">
          {accounts?.map((account) => (
            <li key={account.id}>
              <Avatar large name={account.name || account.username || 'I'} src={account.profile_picture_url} />
              <span className="account-meta">
                <strong>{account.name || account.username || account.instagram_app_id}</strong>
                <small className="muted">{account.username ? `@${account.username}` : account.instagram_app_id}</small>
                <small className="muted">{syncLabel(account)}</small>
              </span>
              {canManage && (
                <button className="btn btn-primary btn-small" disabled={busy === account.id} onClick={() => enable(account)}>
                  {busy === account.id ? 'Starting…' : account.contact_sync_enabled ? 'Sync again' : 'Enable sync'}
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>

      <ul className="account-list contact-list">
        {contacts?.map((contact) => {
          const name = contact.display_name || contact.username || contact.platform_user_id
          return (
            <li key={contact.id}>
              <button type="button" className="contact-open" onClick={() => setSelected(contact)}>
                <Avatar large name={name} src={contact.profile_picture_url} />
                <span className="account-meta">
                  <strong>{name}</strong>
                  <small className="muted">{personFacts(contact).join(' · ') || 'Instagram DM'}</small>
                  <small className="muted">{[formatWhen(contact.last_interaction_at), contact.platform_user_id].filter(Boolean).join(' · ')}</small>
                </span>
              </button>
            </li>
          )
        })}
      </ul>
      {contacts && contacts.length === 0 && <p className="muted">No contacts yet. Enable sync on the Instagram account above.</p>}
      {selected && <ContactModal contact={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

function ContactModal({ contact, onClose }: { contact: CrmContact; onClose: () => void }) {
  const name = contact.display_name || contact.username || 'Instagram user'
  const rows: [string, string][] = [
    ['Name', contact.display_name || '—'],
    ['Username', contact.username ? `@${contact.username}` : '—'],
    ['Instagram user id', contact.platform_user_id],
    ['Source', contact.source || '—'],
    ['Followers', contact.follower_count == null ? 'Not returned by Instagram' : contact.follower_count.toLocaleString()],
    ['Verified', yesNo(contact.is_verified_user)],
    ['Follows you', yesNo(contact.follows_you)],
    ['You follow', yesNo(contact.you_follow)],
    ['Last message', formatWhen(contact.last_interaction_at) || '—'],
    ['First seen', formatWhen(contact.first_seen_at) || '—'],
    ['Saved at', formatWhen(contact.created_at) || '—'],
    ['Last fetched', formatWhen(contact.fetched_at || contact.updated_at) || '—'],
  ]
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal contact-modal" role="dialog" aria-modal="true" aria-labelledby="contact-dialog-title" onClick={(event) => event.stopPropagation()}>
        <div className="contact-hero">
          <Avatar xl name={name} src={contact.profile_picture_url} />
          <span className="account-meta">
            <h2 id="contact-dialog-title">{name}</h2>
            <small className="muted">{contact.username ? `@${contact.username}` : 'No username'}</small>
          </span>
        </div>
        {!contact.profile_picture_url && <p className="muted small">Instagram did not return a profile photo for this user.</p>}
        <dl className="detail-grid">
          {rows.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        <div className="modal-actions">
          <button type="button" className="btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}

function yesNo(value: boolean): string {
  return value ? 'Yes' : 'No'
}

function syncLabel(account: SyncAccount): string {
  if (account.sync_status === 'failed') return account.sync_error || 'Sync failed'
  if (account.sync_status === 'running' || account.sync_status === 'queued') return 'Syncing in the background'
  if (account.sync_status === 'synced') return 'Synced'
  return 'Sync is off'
}
