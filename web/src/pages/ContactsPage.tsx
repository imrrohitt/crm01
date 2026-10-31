import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, ApiError } from '../api/client'
import { Avatar, formatWhen, relativeTime } from '../components/Avatar'
import { Icon } from '../components/Icon'
import { useCompany } from '../layout/CompanyLayout'
import type { CrmContact, SyncAccount } from '../types'

type Filter = 'all' | 'verified' | 'follows_you' | 'you_follow' | 'photo'
type SortKey = 'recent' | 'newest' | 'name' | 'followers'
const PAGE_SIZE = 15

const nameOf = (c: CrmContact) => c.display_name || c.username || c.platform_user_id

function exportCsv(rows: CrmContact[]) {
  const head = ['Name', 'Username', 'Instagram ID', 'Followers', 'Verified', 'Follows you', 'You follow', 'Last interaction', 'First seen']
  const esc = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const lines = rows.map((c) => [c.display_name, c.username, c.platform_user_id, c.follower_count, c.is_verified_user, c.follows_you, c.you_follow, c.last_interaction_at, c.first_seen_at].map(esc).join(','))
  const blob = new Blob([[head.map(esc).join(','), ...lines].join('\n')], { type: 'text/csv' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'contacts.csv'
  a.click()
  URL.revokeObjectURL(a.href)
}

export function ContactsPage() {
  const company = useCompany()
  const [accounts, setAccounts] = useState<SyncAccount[] | null>(null)
  const [contacts, setContacts] = useState<CrmContact[] | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)
  const [selected, setSelected] = useState<CrmContact | null>(null)
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const [sort, setSort] = useState<SortKey>('recent')
  const [page, setPage] = useState(1)
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
  useEffect(() => setPage(1), [query, filter, sort])

  useEffect(() => {
    if (!selected) return
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && setSelected(null)
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

  const counts = useMemo(() => {
    const list = contacts ?? []
    return {
      all: list.length,
      verified: list.filter((c) => c.is_verified_user).length,
      follows_you: list.filter((c) => c.follows_you).length,
      you_follow: list.filter((c) => c.you_follow).length,
      photo: list.filter((c) => c.profile_picture_url).length,
    }
  }, [contacts])

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    const list = (contacts ?? []).filter((c) => {
      if (filter === 'verified' && !c.is_verified_user) return false
      if (filter === 'follows_you' && !c.follows_you) return false
      if (filter === 'you_follow' && !c.you_follow) return false
      if (filter === 'photo' && !c.profile_picture_url) return false
      return !q || [c.display_name, c.username, c.platform_user_id].some((v) => v?.toLowerCase().includes(q))
    })
    const time = (v: string | null) => (v ? new Date(v).getTime() : 0)
    list.sort((a, b) =>
      sort === 'name' ? nameOf(a).localeCompare(nameOf(b))
        : sort === 'followers' ? (b.follower_count ?? -1) - (a.follower_count ?? -1)
        : sort === 'newest' ? time(b.first_seen_at) - time(a.first_seen_at)
        : time(b.last_interaction_at) - time(a.last_interaction_at),
    )
    return list
  }, [contacts, query, filter, sort])

  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE))
  const view = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  const FILTERS: [Filter, string][] = [['all', 'All'], ['verified', 'Verified'], ['follows_you', 'Follows you'], ['you_follow', 'You follow'], ['photo', 'With photo']]

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Contacts</h1>
          <p className="muted lead">People who have sent a DM to a connected Instagram account.</p>
        </div>
        <div className="page-actions">
          <button className="btn" disabled={!rows.length} onClick={() => exportCsv(rows)}><Icon name="download" size={16} />Export CSV</button>
        </div>
      </div>

      {notice && <div className={notice.kind === 'ok' ? 'alert alert-ok' : 'alert'} role={notice.kind === 'ok' ? 'status' : 'alert'}>{notice.text}</div>}

      <section className="card" aria-label="Instagram sync" style={{ marginBottom: 16 }}>
        <div className="card-head">
          <div>
            <h2>Instagram sync</h2>
            <p className="muted small">Import DM contacts from your connected accounts.</p>
          </div>
        </div>
        {!accounts && <div className="skeleton" style={{ height: 56 }} />}
        {accounts && accounts.length === 0 && <p className="muted small" style={{ margin: 0 }}>Connect an Instagram account in Channels first.</p>}
        <ul className="account-list">
          {accounts?.map((account) => (
            <li key={account.id}>
              <Avatar large name={account.name || account.username || 'I'} src={account.profile_picture_url} />
              <span className="account-meta">
                <strong>{account.name || account.username || account.instagram_app_id}</strong>
                <small className="muted">{account.username ? `@${account.username}` : account.instagram_app_id} · {syncLabel(account)}</small>
              </span>
              <span className={`badge ${account.sync_status === 'synced' ? 'badge-success' : account.sync_status === 'failed' ? 'badge-warn' : 'badge-muted'}`}>{account.sync_status === 'synced' ? 'Synced' : account.sync_status === 'failed' ? 'Failed' : account.contact_sync_enabled ? 'Syncing' : 'Off'}</span>
              {canManage && (
                <button className="btn btn-primary btn-small" disabled={busy === account.id} onClick={() => enable(account)}>
                  <Icon name="refresh" size={14} />
                  {busy === account.id ? 'Starting…' : account.contact_sync_enabled ? 'Sync again' : 'Enable sync'}
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>

      <div className="toolbar">
        <label className="search">
          <Icon name="search" size={16} />
          <input type="search" placeholder="Search name, username or ID…" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search contacts" />
        </label>
        <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)} aria-label="Sort contacts">
          <option value="recent">Recently active</option>
          <option value="newest">Newest first</option>
          <option value="name">Name A–Z</option>
          <option value="followers">Most followers</option>
        </select>
      </div>
      <div className="toolbar">
        {FILTERS.map(([key, label]) => (
          <button key={key} className={`chip-btn ${filter === key ? 'is-active' : ''}`} onClick={() => setFilter(key)}>
            {label} <span className="count">{counts[key]}</span>
          </button>
        ))}
      </div>

      <section className="card table-card">
        {!contacts ? (
          <div style={{ padding: 20, display: 'grid', gap: 10 }}>{[0, 1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 48 }} />)}</div>
        ) : rows.length === 0 ? (
          <div className="empty">
            <Icon name="users" size={38} />
            <strong>{contacts.length === 0 ? 'No contacts yet' : 'No contacts match'}</strong>
            <p>{contacts.length === 0 ? 'Enable sync on a connected Instagram account to import people who messaged you.' : 'Try a different search or clear the filters.'}</p>
          </div>
        ) : (
          <>
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr><th>Contact</th><th>Followers</th><th>Relationship</th><th>Last active</th><th>First seen</th></tr>
                </thead>
                <tbody>
                  {view.map((c) => (
                    <tr key={c.id} onClick={() => setSelected(c)} tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && setSelected(c)}>
                      <td>
                        <div className="cell-person">
                          <Avatar name={nameOf(c)} src={c.profile_picture_url} />
                          <span className="row-main">
                            <strong>{nameOf(c)}{c.is_verified_user && <> <Icon name="verified" size={14} className="verified" /></>}</strong>
                            <small>{c.username ? `@${c.username}` : c.platform_user_id}</small>
                          </span>
                        </div>
                      </td>
                      <td>{c.follower_count == null ? <span className="muted">—</span> : c.follower_count.toLocaleString()}</td>
                      <td>
                        <div className="badges">
                          {c.is_verified_user && <span className="badge badge-info">Verified</span>}
                          {c.follows_you && <span className="badge badge-success">Follows you</span>}
                          {c.you_follow && <span className="badge badge-primary">You follow</span>}
                          {!c.is_verified_user && !c.follows_you && !c.you_follow && <span className="badge badge-muted">DM only</span>}
                        </div>
                      </td>
                      <td title={formatWhen(c.last_interaction_at)}>{relativeTime(c.last_interaction_at)}</td>
                      <td className="muted" title={formatWhen(c.first_seen_at)}>{relativeTime(c.first_seen_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pager">
              <span>Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, rows.length)} of {rows.length}</span>
              <div className="pager-btns">
                <button className="btn btn-small" disabled={page <= 1} onClick={() => setPage(page - 1)}><Icon name="chevronLeft" size={14} />Prev</button>
                <button className="btn btn-small" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next<Icon name="chevronRight" size={14} /></button>
              </div>
            </div>
          </>
        )}
      </section>

      {selected && <ContactDrawer contact={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

function ContactDrawer({ contact, onClose }: { contact: CrmContact; onClose: () => void }) {
  const name = nameOf(contact)
  const yes = (v: boolean) => <span className={`badge ${v ? 'badge-success' : 'badge-muted'}`}>{v ? 'Yes' : 'No'}</span>
  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label="Contact details">
        <div className="drawer-head">
          Contact details
          <button className="icon-btn" onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
        </div>
        <div className="drawer-body">
          <div className="profile-hero">
            <Avatar xl name={name} src={contact.profile_picture_url} />
            <h2>{name}{contact.is_verified_user && <Icon name="verified" size={18} className="verified" />}</h2>
            <span className="muted">{contact.username ? `@${contact.username}` : 'No username'}</span>
          </div>
          <div className="profile-stats">
            <div><b>{contact.follower_count == null ? '—' : contact.follower_count.toLocaleString()}</b><span>Followers</span></div>
            <div><b>{relativeTime(contact.last_interaction_at)}</b><span>Last active</span></div>
            <div><b>{relativeTime(contact.first_seen_at)}</b><span>First seen</span></div>
          </div>
          <dl className="detail-grid">
            <div><dt>Instagram user ID</dt><dd><code>{contact.platform_user_id}</code></dd></div>
            <div><dt>Source</dt><dd>{contact.source || '—'}</dd></div>
            <div><dt>Verified</dt><dd>{yes(contact.is_verified_user)}</dd></div>
            <div><dt>Follows you</dt><dd>{yes(contact.follows_you)}</dd></div>
            <div><dt>You follow</dt><dd>{yes(contact.you_follow)}</dd></div>
            <div><dt>Last message</dt><dd>{formatWhen(contact.last_interaction_at) || '—'}</dd></div>
            <div><dt>First seen</dt><dd>{formatWhen(contact.first_seen_at) || '—'}</dd></div>
            <div><dt>Last fetched</dt><dd>{formatWhen(contact.fetched_at || contact.updated_at) || '—'}</dd></div>
          </dl>
          {!contact.profile_picture_url && <p className="muted small">Instagram did not return a profile photo for this user.</p>}
        </div>
      </aside>
    </>
  )
}

function syncLabel(account: SyncAccount): string {
  if (account.sync_status === 'failed') return account.sync_error || 'Sync failed'
  if (account.sync_status === 'running' || account.sync_status === 'queued') return 'Syncing in the background'
  if (account.sync_status === 'synced') return account.last_synced_at ? `Last synced ${relativeTime(account.last_synced_at)}` : 'Synced'
  return 'Sync is off'
}
