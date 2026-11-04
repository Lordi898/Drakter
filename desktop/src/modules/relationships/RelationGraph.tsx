import { ENTITY_TYPE_LABEL, type RelatedItem } from './types'

const MAX_NEIGHBOURS = 12
const SIZE = 280
const CENTER = SIZE / 2
const RADIUS = 100

/** Grafo radial simple: el elemento al centro y hasta 12 vecinos. Los títulos van como texto plano. */
export function RelationGraph({ title, items }: { readonly title: string; readonly items: readonly RelatedItem[] }) {
  const shown = items.slice(0, MAX_NEIGHBOURS)
  const hidden = items.length - shown.length
  const clip = (text: string, n: number) => (text.length > n ? `${text.slice(0, n - 1)}…` : text)

  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      className="mx-auto w-full max-w-[320px] text-plan-line"
      role="img"
      aria-label={`Mapa de relaciones de ${title}: ${shown.length} ${shown.length === 1 ? 'vecino' : 'vecinos'}${hidden > 0 ? ` y ${hidden} más en la lista` : ''}`}
    >
      {shown.map((item, i) => {
        const angle = (2 * Math.PI * i) / shown.length - Math.PI / 2
        const x = CENTER + RADIUS * Math.cos(angle)
        const y = CENTER + RADIUS * Math.sin(angle)
        return (
          <g key={`${item.relationship_id ?? 'v'}-${item.entity_id}-${item.direction}-${i}`}>
            <line
              x1={CENTER} y1={CENTER} x2={x} y2={y}
              stroke="currentColor" strokeWidth="1.25"
              strokeDasharray={item.virtual ? '3 3' : undefined}
              opacity={item.archived ? 0.45 : 1}
            />
            <circle cx={x} cy={y} r="6" fill="var(--card)" stroke="currentColor" strokeWidth="1.25" opacity={item.archived ? 0.45 : 1} />
            <text
              x={x + (Math.cos(angle) >= 0 ? 10 : -10)} y={y + 3}
              textAnchor={Math.cos(angle) >= 0 ? 'start' : 'end'}
              fontSize="9" fill="var(--muted-foreground)"
            >
              {clip(item.entity_title || ENTITY_TYPE_LABEL[item.entity_type], 14)}
            </text>
          </g>
        )
      })}
      <circle cx={CENTER} cy={CENTER} r="14" fill="var(--primary)" />
      <text x={CENTER} y={CENTER + 28} textAnchor="middle" fontSize="10" fontWeight="600" fill="var(--foreground)">
        {clip(title, 22)}
      </text>
    </svg>
  )
}
