export function CalendarDrawing() {
  const columns = [40, 70, 100, 130, 160, 190]
  const rows = [38, 56, 74, 92, 110]
  return (
    <svg
      width="220"
      height="130"
      viewBox="0 0 220 130"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.25"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="10" y="10" width="200" height="110" rx="3" />
      <path d="M10 28H210" />
      <path d="M40 10V120" />
      {columns.slice(1).map((x) => (
        <path key={x} d={`M${x} 20V120`} />
      ))}
      {rows.map((y) => (
        <path key={y} d={`M10 ${y}H210`} strokeDasharray="2 3" />
      ))}
      <path d="M62 10V4M158 10V4" />
    </svg>
  )
}
