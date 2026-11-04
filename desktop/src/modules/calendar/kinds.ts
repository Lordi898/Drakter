import type { OccurrenceKind } from './types'

export interface KindStyle {
  readonly label: string
  /** Clases del bloque: el tipo se distingue por color, trazo y no solo por tono. */
  readonly chip: string
  readonly dot: string
}

export const KIND_STYLES: Readonly<Record<OccurrenceKind, KindStyle>> = {
  event: {
    label: 'Evento',
    chip: 'border-plan-line bg-plan-line/20 text-foreground',
    dot: 'bg-plan-line'
  },
  reminder: {
    label: 'Recordatorio',
    chip: 'border-ambar border-l-4 bg-ambar/15 text-foreground',
    dot: 'bg-ambar'
  },
  work_session: {
    label: 'Sesión de trabajo',
    chip: 'border-success bg-success/20 text-foreground',
    dot: 'bg-success'
  },
  time_block: {
    label: 'Bloque de tiempo',
    chip: 'border-dashed border-warning bg-warning/10 text-foreground',
    dot: 'bg-warning'
  },
  class: {
    label: 'Clase',
    chip: 'border-border bg-muted text-muted-foreground',
    dot: 'bg-muted-foreground'
  }
}

export const STATUS_LABELS: Readonly<Record<string, string>> = {
  tentative: 'Provisional',
  confirmed: 'Confirmado',
  cancelled: 'Cancelado',
  planned: 'Planificado',
  in_progress: 'En curso',
  done: 'Hecho',
  skipped: 'Omitido'
}
