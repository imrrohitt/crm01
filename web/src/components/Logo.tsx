/** insta.crm emblem: a faceted chat bubble with a signal spark. */
export function Logo({ size = 34 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" role="img" aria-label="insta.crm">
      <defs>
        <linearGradient id="lg-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#2a1f66" />
          <stop offset="1" stopColor="#0d0a24" />
        </linearGradient>
        <linearGradient id="lg-b" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#b9a4ff" />
          <stop offset=".55" stopColor="#7a55ff" />
          <stop offset="1" stopColor="#ff5fa8" />
        </linearGradient>
        <linearGradient id="lg-hi" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity=".55" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
      </defs>
      <rect width="40" height="40" rx="11" fill="url(#lg-bg)" />
      <rect x=".5" y=".5" width="39" height="39" rx="10.5" fill="none" stroke="#fff" strokeOpacity=".14" />
      <path d="M11 11.5h18a4 4 0 014 4v8.5a4 4 0 01-4 4H19.5L13 32.5V28h-2a4 4 0 01-4-4v-8.5a4 4 0 014-4z" fill="url(#lg-b)" />
      <path d="M11 11.5h18a4 4 0 014 4v3H7v-3a4 4 0 014-4z" fill="url(#lg-hi)" />
      <circle cx="14.5" cy="19.8" r="1.7" fill="#fff" />
      <circle cx="20" cy="19.8" r="1.7" fill="#fff" />
      <circle cx="25.5" cy="19.8" r="1.7" fill="#fff" />
      <path d="M33 6.5l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z" fill="#ffd9a8" />
    </svg>
  )
}
