import { useState } from 'react'

export interface Series {
  label: string
  color: string
  values: number[]
}

function smooth(points: [number, number][]): string {
  if (points.length < 2) return ''
  let d = `M${points[0][0]},${points[0][1]}`
  for (let i = 1; i < points.length; i++) {
    const [x0, y0] = points[i - 1]
    const [x1, y1] = points[i]
    const cx = (x0 + x1) / 2
    d += ` C${cx},${y0} ${cx},${y1} ${x1},${y1}`
  }
  return d
}

export function Sparkline({ values, color = 'var(--primary)' }: { values: number[]; color?: string }) {
  const w = 96
  const h = 32
  const max = Math.max(1, ...values)
  const pts: [number, number][] = values.map((v, i) => [(i / Math.max(1, values.length - 1)) * w, h - 3 - (v / max) * (h - 8)])
  const line = smooth(pts)
  return (
    <svg className="sparkline" viewBox={`0 0 ${w} ${h}`} width={w} height={h} aria-hidden="true">
      <path d={`${line} L${w},${h} L0,${h} Z`} fill={color} opacity=".12" />
      <path d={line} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export function AreaChart({ days, series }: { days: number[]; series: Series[] }) {
  const W = 640
  const H = 240
  const pad = { l: 34, r: 10, t: 12, b: 26 }
  const iw = W - pad.l - pad.r
  const ih = H - pad.t - pad.b
  const rawMax = Math.max(1, ...series.flatMap((s) => s.values))
  const step = rawMax <= 4 ? 1 : Math.ceil(rawMax / 4)
  const max = step * Math.ceil(rawMax / step)
  const [hover, setHover] = useState<number | null>(null)
  const n = days.length
  const x = (i: number) => pad.l + (i / Math.max(1, n - 1)) * iw
  const y = (v: number) => pad.t + ih - (v / max) * ih
  const ticks = Array.from({ length: max / step + 1 }, (_, i) => i * step)
  const fmt = (t: number) => new Date(t).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })

  function onMove(e: React.MouseEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect()
    const px = ((e.clientX - rect.left) / rect.width) * W
    setHover(Math.max(0, Math.min(n - 1, Math.round(((px - pad.l) / iw) * (n - 1)))))
  }

  return (
    <div className="chart-wrap">
      <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Activity chart" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        <defs>
          {series.map((s, i) => (
            <linearGradient key={i} id={`area-${i}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor={s.color} stopOpacity=".28" />
              <stop offset="1" stopColor={s.color} stopOpacity="0" />
            </linearGradient>
          ))}
        </defs>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} className="chart-grid" />
            <text x={pad.l - 8} y={y(t) + 4} textAnchor="end" className="chart-label">{t}</text>
          </g>
        ))}
        {[0, Math.floor((n - 1) / 3), Math.floor(((n - 1) * 2) / 3), n - 1].map((i) => (
          <text key={i} x={x(i)} y={H - 6} textAnchor={i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle'} className="chart-label">{fmt(days[i])}</text>
        ))}
        {series.map((s, i) => {
          const pts = s.values.map((v, j) => [x(j), y(v)] as [number, number])
          const line = smooth(pts)
          return (
            <g key={s.label}>
              <path d={`${line} L${x(n - 1)},${y(0)} L${x(0)},${y(0)} Z`} fill={`url(#area-${i})`} />
              <path d={line} fill="none" stroke={s.color} strokeWidth="2.4" strokeLinecap="round" />
            </g>
          )
        })}
        {hover !== null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={pad.t} y2={pad.t + ih} className="chart-cursor" />
            {series.map((s) => (
              <circle key={s.label} cx={x(hover)} cy={y(s.values[hover])} r="4.5" fill="var(--surface)" stroke={s.color} strokeWidth="2.4" />
            ))}
          </g>
        )}
      </svg>
      {hover !== null && (
        <div className="chart-tip" style={{ left: `${(x(hover) / W) * 100}%` }}>
          <strong>{fmt(days[hover])}</strong>
          {series.map((s) => (
            <span key={s.label}><i style={{ background: s.color }} />{s.label}<b>{s.values[hover]}</b></span>
          ))}
        </div>
      )}
      <div className="chart-legend">
        {series.map((s) => (
          <span key={s.label}><i style={{ background: s.color }} />{s.label}</span>
        ))}
      </div>
    </div>
  )
}

export interface Slice {
  label: string
  value: number
  color: string
}

export function Donut({ slices, center, caption }: { slices: Slice[]; center: string; caption: string }) {
  const total = slices.reduce((a, s) => a + s.value, 0)
  const r = 52
  const c = 2 * Math.PI * r
  let offset = 0
  return (
    <div className="donut">
      <svg viewBox="0 0 140 140" width="160" height="160" role="img" aria-label={caption}>
        <circle cx="70" cy="70" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="16" />
        {total > 0 &&
          slices.map((s) => {
            const len = (s.value / total) * c
            const el = (
              <circle key={s.label} cx="70" cy="70" r={r} fill="none" stroke={s.color} strokeWidth="16" strokeDasharray={`${Math.max(0, len - 2)} ${c - Math.max(0, len - 2)}`} strokeDashoffset={-offset} transform="rotate(-90 70 70)" strokeLinecap="butt" />
            )
            offset += len
            return el
          })}
        <text x="70" y="68" textAnchor="middle" className="donut-num">{center}</text>
        <text x="70" y="86" textAnchor="middle" className="chart-label">{caption}</text>
      </svg>
      <ul className="donut-legend">
        {slices.map((s) => (
          <li key={s.label}>
            <i style={{ background: s.color }} />
            <span>{s.label}</span>
            <b>{s.value}</b>
          </li>
        ))}
      </ul>
    </div>
  )
}
