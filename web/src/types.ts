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

export interface Session {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
  companies: Company[]
  default_company_id: string | null
}
