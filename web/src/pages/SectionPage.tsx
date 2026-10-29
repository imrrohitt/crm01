import { useParams } from 'react-router-dom'

export function SectionPage() {
  const { section = '' } = useParams()
  const title = section.charAt(0).toUpperCase() + section.slice(1)
  return (
    <div className="page">
      <h1>{title}</h1>
      <p className="muted lead">This section is coming soon.</p>
    </div>
  )
}
