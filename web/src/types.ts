export interface User {
  id: string
  email: string
  full_name: string | null
  avatar_url: string | null
}

export interface Company {
  id: string
  name: string
  slug: string
  roles: string[]
  job_title: string | null
}

export interface SubscriptionSummary {
  has_access: boolean
  plan: string | null
  status: string | null
  features: Record<string, boolean | number | string>
}

export interface CompanyDetail extends Company {
  user: User
  subscription: SubscriptionSummary
}

export interface ChannelAccount {
  id: string
  platform: string
  platform_account_id: string
  username: string | null
  account_type: string | null
  status: 'connected' | 'disconnected' | 'error'
  profile_picture_url: string | null
  connected_at: string
}

export interface InstagramProfile {
  id: string
  username: string | null
  name: string | null
  profile_picture_url: string | null
}

export interface WebhookPreview {
  id: string
  webhook_url: string
  webhook_verify_token: string
}

export interface InstagramConnection {
  id: string
  instagram_app_id: string
  username: string | null
  name: string | null
  profile_picture_url: string | null
  webhook_url: string
  webhook_verify_token: string
  status: string
  created_at: string
}

export interface Channel {
  key: string
  name: string
  configured: boolean
  limit: number | null
  accounts: ChannelAccount[]
  connections?: InstagramConnection[]
}

export interface ChannelsResponse {
  channels: Channel[]
  can_manage: boolean
}

export interface SyncAccount {
  id: string
  instagram_app_id: string
  username: string | null
  name: string | null
  profile_picture_url: string | null
  contact_sync_enabled: boolean
  sync_status: string
  sync_error: string | null
  last_synced_at: string | null
}

export interface ProfileFacts {
  follower_count: number | null
  is_verified_user: boolean
  follows_you: boolean
  you_follow: boolean
}

export interface CrmContact extends ProfileFacts {
  id: string
  platform_user_id: string
  username: string | null
  display_name: string | null
  profile_picture_url: string | null
  source: string
  first_seen_at: string | null
  last_interaction_at: string | null
  created_at: string | null
  updated_at: string | null
  fetched_at: string | null
}

export interface ConversationSummary extends ProfileFacts {
  id: string
  contact_id: string
  contact_name: string
  contact_username: string | null
  contact_profile_picture_url: string | null
  contact_platform_user_id: string | null
  status: string
  last_message_at: string | null
  last_message: string | null
  last_direction: string | null
}

export interface ConversationMessage {
  id: string
  direction: 'inbound' | 'outbound'
  content: string | null
  message_type: string
  sent_at: string | null
}

export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[]
}

export interface Session {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
  companies: Company[]
  default_company_id: string | null
}
