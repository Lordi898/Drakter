import { WEEK_DAYS } from './rrule'
import type { HabitStatistics } from './types'

function Figure({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-md border border-border bg-card p-3">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="type-display mt-1 text-2xl text-foreground">{value}</dd>
      {hint ? <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  )
}

const days = (n: number) => `${n} ${n === 1 ? 'día' : 'días'}`

export function HabitStats({ stats }: { readonly stats: HabitStatistics }) {
  const rate = stats.completion_rate === null ? 'sin datos' : `${Math.round(stats.completion_rate * 100)} %`
  const byDay = new Map(stats.by_weekday.map((w) => [w.weekday, w]))
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Figure label="Cumplimiento" value={rate} hint={`${stats.done} hechos de ${stats.scheduled} programados`} />
        <Figure label="Racha actual" value={days(stats.current_streak)} />
        <Figure label="Mejor racha" value={days(stats.best_streak)} />
        <Figure
          label="Sin registrar"
          value={String(stats.unrecorded)}
          hint={`${stats.skipped} saltados, ${stats.missed} no hechos`}
        />
      </dl>
      <div>
        <h4 className="mb-2 text-sm font-medium text-foreground">Por día de la semana</h4>
        <ul className="flex flex-col gap-1.5">
          {WEEK_DAYS.map((d) => {
            const w = byDay.get(d.iso)
            const scheduled = w?.scheduled ?? 0
            const done = w?.done ?? 0
            const pct = scheduled > 0 ? (done / scheduled) * 100 : 0
            return (
              <li key={d.code} className="flex items-center gap-3 text-sm">
                <span className="w-20 shrink-0 text-muted-foreground">{d.name}</span>
                <div
                  role="img"
                  aria-label={scheduled > 0 ? `${done} de ${scheduled} hechos` : 'sin días programados'}
                  className="h-2 flex-1 overflow-hidden rounded-full bg-muted"
                >
                  <div className="h-full bg-success" style={{ width: `${pct}%` }} />
                </div>
                <span className="w-16 shrink-0 text-right tabular-nums text-muted-foreground">
                  {scheduled > 0 ? `${done}/${scheduled}` : '—'}
                </span>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
