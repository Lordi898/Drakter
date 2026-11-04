const NODES: ReadonlyArray<readonly [number, number, number]> = [
  [34, 38, 9],
  [92, 22, 6],
  [150, 50, 10],
  [196, 24, 6],
  [64, 98, 7],
  [122, 108, 9],
  [190, 96, 6],
]

const LINKS: ReadonlyArray<string> = [
  'M42 35L87 24',
  'M98 25L142 46',
  'M159 46L191 27',
  'M37 47L61 92',
  'M71 99L113 107',
  'M127 100L146 59',
  'M131 107L185 97',
  'M153 60L188 92',
]

export function RelationshipsDrawing() {
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
      {LINKS.map((d) => (
        <path key={d} d={d} />
      ))}
      {NODES.map(([cx, cy, r]) => (
        <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r={r} />
      ))}
    </svg>
  )
}
