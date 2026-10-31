function hue(name: string): number {
  let h = 0
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % 360
  return h
}

export function Avatar({ name, src, large = false, xl = false }: { name: string; src?: string | null; large?: boolean; xl?: boolean }) {
  const size = xl ? 'avatar-xl' : large ? 'avatar-lg' : ''
  if (src) return <img className={`avatar-img ${size}`.trim()} src={src} alt="" referrerPolicy="no-referrer" />
  const h = hue(name || '?')
  return (
    <span className={`avatar ${size}`.trim()} style={{ background: `linear-gradient(135deg, hsl(${h} 72% 56%), hsl(${(h + 45) % 360} 72% 48%))` }}>
      {(name || '?').replace(/^@/, '')[0]?.toUpperCase()}
    </span>
  )
}

export function formatWhen(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
}

/** "5m ago", "3h ago", "Yesterday", "12 Mar". */
export function relativeTime(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const mins = Math.round((Date.now() - date.getTime()) / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days}d ago`
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: date.getFullYear() === new Date().getFullYear() ? undefined : 'numeric' })
}

export function personFacts(person: {
  username?: string | null
  follower_count?: number | null
  is_verified_user?: boolean
  follows_you?: boolean
  you_follow?: boolean
}): string[] {
  const facts: string[] = []
  if (person.username) facts.push(`@${person.username}`)
  if (person.follower_count != null) facts.push(`${person.follower_count.toLocaleString()} followers`)
  if (person.is_verified_user) facts.push('Verified')
  if (person.follows_you) facts.push('Follows you')
  if (person.you_follow) facts.push('You follow')
  return facts
}
