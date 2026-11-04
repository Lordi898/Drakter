export function TasksDrawing() {
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
      focusable="false"
    >
      {/* hoja */}
      <rect x="10" y="8" width="200" height="114" rx="3" />
      {/* renglón 1 */}
      <rect x="24" y="22" width="12" height="12" rx="1.5" />
      <path d="M28 28l2.5 2.5L35 25" />
      <path d="M46 28h110" />
      {/* subtarea 1 */}
      <path d="M30 38v22h18" />
      <rect x="52" y="54" width="12" height="12" rx="1.5" />
      <path d="M74 60h84" />
      {/* subtarea anidada */}
      <path d="M58 70v22h18" />
      <rect x="80" y="86" width="12" height="12" rx="1.5" />
      <path d="M102 92h56" />
      {/* renglón 2 */}
      <rect x="24" y="106" width="12" height="12" rx="1.5" />
      <path d="M46 112h90" />
      {/* guía de margen */}
      <path d="M176 8v114" strokeDasharray="3 4" />
    </svg>
  )
}
