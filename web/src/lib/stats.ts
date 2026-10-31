const DAY = 86400000

export function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
}

/** Counts per day for the last `days` days (oldest first), plus the day start timestamps. */
export function bucketByDay(values: (string | null | undefined)[], days: number): { days: number[]; counts: number[] } {
  const today = startOfDay(new Date())
  const stamps = Array.from({ length: days }, (_, i) => today - (days - 1 - i) * DAY)
  const counts = stamps.map(() => 0)
  for (const v of values) {
    if (!v) continue
    const t = new Date(v)
    if (Number.isNaN(t.getTime())) continue
    const idx = Math.floor((startOfDay(t) - stamps[0]) / DAY)
    if (idx >= 0 && idx < days) counts[idx]++
  }
  return { days: stamps, counts }
}

export function sum(a: number[]): number {
  return a.reduce((x, y) => x + y, 0)
}

/** % change of the last `n` entries versus the `n` before; null when there is no baseline. */
export function trend(counts: number[], n = 7): number | null {
  const cur = sum(counts.slice(-n))
  const prev = sum(counts.slice(-2 * n, -n))
  if (prev === 0) return cur === 0 ? null : 100
  return Math.round(((cur - prev) / prev) * 100)
}

export function cumulative(a: number[], base = 0): number[] {
  let t = base
  return a.map((v) => (t += v))
}

export function compact(n: number): string {
  return new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(n)
}
