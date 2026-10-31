export function Avatar({ name, src, large = false, xl = false }: { name: string; src?: string | null; large?: boolean; xl?: boolean }) {
  const size = xl ? 'avatar-xl' : large ? 'avatar-lg' : ''
  if (src) return <img className={`avatar-img ${size}`.trim()} src={src} alt="" referrerPolicy="no-referrer" />
  return <span className={`avatar ${size}`.trim()}>{(name || '?')[0]?.toUpperCase()}</span>
}

export function formatWhen(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
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
