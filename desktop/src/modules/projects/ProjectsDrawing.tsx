export function ProjectsDrawing() {
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
      {/* Marco de la hoja */}
      <rect x="4" y="4" width="212" height="122" />
      {/* Línea de avance: tramo recorrido continuo, resto a trazos */}
      <path d="M24 78 H92" />
      <path d="M92 78 H196" strokeDasharray="4 4" />
      {/* Hito alcanzado: marca sobre la línea */}
      <path d="M24 70 V86" />
      {/* Hitos sin completar: rombos vacíos */}
      <path d="M92 68 L102 78 L92 88 L82 78 Z" />
      <path d="M144 68 L154 78 L144 88 L134 78 Z" />
      <path d="M196 68 L206 78 L196 88 L186 78 Z" />
      {/* Cotas sobre los hitos */}
      <path d="M24 46 H196" />
      <path d="M24 42 V50 M92 42 V50 M144 42 V50 M196 42 V50" />
      {/* Cuerda de referencia inferior */}
      <path d="M24 108 H196" strokeDasharray="1 5" />
    </svg>
  )
}
