import { useCompany } from '../layout/CompanyLayout'

export function HomePage() {
  const company = useCompany()
  const { subscription } = company
  const features = Object.entries(subscription.features)

  return (
    <div className="page">
      <h1>Welcome to Insta CRM</h1>
      <p className="muted lead">
        {company.user.full_name ? `Hi ${company.user.full_name}, you` : 'You'} are working in <strong>{company.name}</strong>.
      </p>

      <section className="cards">
        <div className="card">
          <h2>Company</h2>
          <dl>
            <dt>Name</dt><dd>{company.name}</dd>
            <dt>Company ID</dt><dd><code>{company.id}</code></dd>
            <dt>Your role</dt><dd>{company.roles.join(', ') || '—'}</dd>
          </dl>
        </div>
        <div className="card">
          <h2>Subscription</h2>
          <dl>
            <dt>Plan</dt><dd>{subscription.plan ?? '—'}</dd>
            <dt>Status</dt><dd>{subscription.status ?? '—'}</dd>
            <dt>Access</dt><dd>{subscription.has_access ? 'Enabled' : 'Disabled'}</dd>
          </dl>
        </div>
      </section>

      <section className="card">
        <h2>Enabled features</h2>
        <ul className="chips">
          {features.map(([code, value]) => (
            <li key={code} className={value === false ? 'chip is-off' : 'chip'}>
              {code.replace(/_/g, ' ')}
              {typeof value === 'number' && <b>{value}</b>}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
