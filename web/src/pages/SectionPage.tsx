import { useParams } from 'react-router-dom'
import { Scene } from '../components/Scene'

export function SectionPage() {
  const { section = '' } = useParams()
  const title = section.charAt(0).toUpperCase() + section.slice(1)
  return (
    <div className="page">
      <div className="page-head"><h1>{title}</h1></div>
      <section className="card">
        <div className="empty">
          <Scene variant="mini" />
          <strong>{title} is coming soon</strong>
          <p>We are working on this section. It will appear here as soon as it is ready.</p>
        </div>
      </section>
    </div>
  )
}
