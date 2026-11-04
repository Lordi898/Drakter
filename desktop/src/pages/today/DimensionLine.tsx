import type { TodayProject } from './contract'
import { longDay, shortDay, yearOf } from './format'

export interface DimensionLineProps {
  readonly project: TodayProject
  /** Año de la fecha de la pantalla: el año del objetivo solo se rotula si difiere. */
  readonly currentYear: number | null
}

const LINE_Y = 22

/** Progreso como línea de cota de plano: trazos finales, tramo recorrido y porcentaje rotulado. */
export function DimensionLine({ project, currentYear }: DimensionLineProps) {
  const { progress, target_date: target } = project
  const percent = progress === null ? null : Math.min(100, Math.max(0, progress))
  const targetLabel = target ? shortDay(target, yearOf(target) !== currentYear) : null
  const aria = `Progreso: ${percent === null ? 'sin tareas todavía' : `${percent} %`}${
    target ? `, objetivo ${longDay(target)}` : ''
  }`

  const labelAnchor = percent === null || percent < 10 ? 'start' : percent > 90 ? 'end' : 'middle'
  const labelX = percent === null ? '0' : `${percent}%`

  return (
    <svg
      role="img"
      aria-label={aria}
      width="100%"
      height={targetLabel ? 42 : 30}
      className="block overflow-visible text-foreground"
    >
      <line
        x1="0"
        x2="100%"
        y1={LINE_Y}
        y2={LINE_Y}
        stroke="var(--plan-line)"
        strokeWidth="1"
        strokeDasharray={percent === null ? '4 3' : undefined}
      />
      <line x1="0" x2="0" y1={LINE_Y - 5} y2={LINE_Y + 5} stroke="var(--plan-line)" strokeWidth="1" />
      <line x1="100%" x2="100%" y1={LINE_Y - 5} y2={LINE_Y + 5} stroke="var(--plan-line)" strokeWidth="1" />
      {percent !== null && percent > 0 ? (
        <line x1="0" x2={`${percent}%`} y1={LINE_Y} y2={LINE_Y} stroke="currentColor" strokeWidth="3" />
      ) : null}
      <text
        x={labelX}
        y={13}
        textAnchor={labelAnchor}
        fill="currentColor"
        fontSize="12"
        style={{ fontVariantNumeric: 'tabular-nums' }}
      >
        {percent === null ? 'Sin tareas todavía' : `${percent} %`}
      </text>
      {targetLabel ? (
        <text x="100%" y={39} textAnchor="end" fill="var(--muted-foreground)" fontSize="12">
          {targetLabel}
        </text>
      ) : null}
    </svg>
  )
}
