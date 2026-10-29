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

export interface Session {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
  companies: Company[]
  default_company_id: string | null
}
