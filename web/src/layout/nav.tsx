import type { ReactNode } from 'react'

export interface NavItem {
  path: string // '' = home
  label: string
  feature?: string // shown only when this plan feature is enabled
  icon: ReactNode
}

const svg = (d: string) => (
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={d} />
  </svg>
)

export const NAV: NavItem[] = [
  { path: '', label: 'Home', icon: svg('M3 11l9-8 9 8M5 10v10h14V10') },
  { path: 'inbox', label: 'Inbox', feature: 'inbox', icon: svg('M4 4h16v12H8l-4 4V4z') },
  { path: 'contacts', label: 'Contacts', feature: 'contacts', icon: svg('M16 11a4 4 0 10-8 0 4 4 0 008 0zM4 21c0-4 4-6 8-6s8 2 8 6') },
  { path: 'conversations', label: 'Conversations', feature: 'inbox', icon: svg('M4 5h16v10H8l-4 4V5z') },
  { path: 'leads', label: 'Leads', feature: 'leads', icon: svg('M3 4h18l-7 9v6l-4 2v-8L3 4z') },
  { path: 'campaigns', label: 'Campaigns', feature: 'campaigns', icon: svg('M3 11v2l14 6V5L3 11zM17 8a4 4 0 010 8') },
  { path: 'automation', label: 'Automation', feature: 'automation', icon: svg('M13 2L4 14h7l-1 8 9-12h-7l1-8z') },
  { path: 'analytics', label: 'Analytics', feature: 'analytics', icon: svg('M4 20V10M10 20V4M16 20v-8M22 20H2') },
  { path: 'channels', label: 'Channels', icon: svg('M5 12a7 7 0 0114 0M8.5 12a3.5 3.5 0 017 0M12 12v.01M6 20h12') },
  { path: 'team', label: 'Team', icon: svg('M17 20v-2a4 4 0 00-4-4H7a4 4 0 00-4 4v2M10 10a4 4 0 100-8 4 4 0 000 8zM21 20v-2a4 4 0 00-3-3.9') },
  { path: 'settings', label: 'Settings', icon: svg('M12 15a3 3 0 100-6 3 3 0 000 6zM19 12a7 7 0 00-.1-1.2l2-1.5-2-3.4-2.3 1a7 7 0 00-2-1.2L14 3h-4l-.6 2.7a7 7 0 00-2 1.2l-2.3-1-2 3.4 2 1.5A7 7 0 005 12c0 .4 0 .8.1 1.2l-2 1.5 2 3.4 2.3-1a7 7 0 002 1.2L10 21h4l.6-2.7a7 7 0 002-1.2l2.3 1 2-3.4-2-1.5c.1-.4.1-.8.1-1.2z') },
]
