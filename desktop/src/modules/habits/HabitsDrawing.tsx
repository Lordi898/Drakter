const COLUMNS = 7
const COLUMN_WIDTH = 26
const GRID_LEFT = 19

export function HabitsDrawing() {
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
      {/* Regla de días */}
      <rect x="8" y="14" width="204" height="24" rx="2" />
      {Array.from({ length: COLUMNS * 2 + 1 }, (_, i) => {
        const x = 8 + i * 13
        const tall = i % 2 === 0
        return <path key={i} d={`M${x} 14v${tall ? 9 : 5}`} />
      })}
      {/* Filas de casillas vacías */}
      {[54, 82, 110].map((y) =>
        Array.from({ length: COLUMNS }, (_, c) => (
          <rect key={`${y}-${c}`} x={GRID_LEFT + c * COLUMN_WIDTH} y={y - 8} width="16" height="16" rx="2" />
        )),
      )}
      {/* Línea de cota */}
      <path d="M8 124h204M8 121v6M212 121v6" strokeDasharray="3 3" />
    </svg>
  )
}
