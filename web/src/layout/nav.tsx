import type { IconName } from '../components/Icon'

export interface NavItem {
  path: string // '' = home
  label: string
  feature?: string // shown only when this plan feature is enabled
  icon: IconName
  group: 'main' | 'grow' | 'workspace'
}

export const NAV: NavItem[] = [
  { path: '', label: 'Dashboard', icon: 'home', group: 'main' },
  { path: 'inbox', label: 'Inbox', feature: 'inbox', icon: 'inbox', group: 'main' },
  { path: 'contacts', label: 'Contacts', feature: 'contacts', icon: 'users', group: 'main' },
  { path: 'conversations', label: 'Conversations', feature: 'inbox', icon: 'message', group: 'main' },
  { path: 'leads', label: 'Leads', feature: 'leads', icon: 'funnel', group: 'grow' },
  { path: 'campaigns', label: 'Campaigns', feature: 'campaigns', icon: 'megaphone', group: 'grow' },
  { path: 'automation', label: 'Automation', feature: 'automation', icon: 'bolt', group: 'grow' },
  { path: 'analytics', label: 'Analytics', feature: 'analytics', icon: 'chart', group: 'grow' },
  { path: 'channels', label: 'Channels', icon: 'radio', group: 'workspace' },
  { path: 'team', label: 'Team', icon: 'userPlus', group: 'workspace' },
  { path: 'settings', label: 'Settings', icon: 'settings', group: 'workspace' },
]

export const GROUP_LABEL: Record<NavItem['group'], string> = { main: 'Workspace', grow: 'Grow', workspace: 'Manage' }
