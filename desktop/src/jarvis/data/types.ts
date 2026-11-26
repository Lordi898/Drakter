/**
 * Contrato de datos de las interfaces Jarvis (J1; lo implementa D1 en `jarvis/data/**`).
 *
 * Instantáneas de los datos REST del Workspace, adaptadas de los hooks de `modules/*` y de
 * `pages/today` (W2): mismo origen de verdad, sin peticiones ni caché propias. Lo que ya vive en
 * stores (chat, estado del agente, trabajos, avisos, confirmaciones, voz, niveles de audio) lo leen
 * las interfaces directamente de `stores/*` y `voice/levels.ts`; no pasa por aquí.
 *
 * Todo texto que venga de aquí es dato no confiable: se pinta como texto plano, nunca como HTML.
 */
import type { AuditEvent } from '@/modules/activity/types'
import type { AgendaItem } from '@/modules/calendar/types'
import type { Habit, HabitHistoryDay } from '@/modules/habits/types'
import type { MemoryBackendStatus } from '@/modules/memory/types'
import type { Project } from '@/modules/projects/types'
import type { EntityType, RelationshipOut } from '@/modules/relationships/types'
import type { Folder, IndexStatus, ResourceSummary } from '@/modules/storage/types'
import type { Subject, TimetableEntry } from '@/modules/subjects/types'
import type { Task } from '@/modules/tasks/types'
import type { TodayResponse } from '@/pages/today/contract'

/** `offline`: el servicio local no responde. Con `error` u `offline`, `data` conserva lo último bueno. */
export type SnapshotStatus = 'loading' | 'ready' | 'offline' | 'error'

export interface Snapshot<T> {
  readonly status: SnapshotStatus
  /** Último dato bueno (también durante una recarga o tras un fallo); `null` si nunca llegó. */
  readonly data: T | null
  /** Texto corto en español para mostrar; `null` si no hay error. */
  readonly error: string | null
  /** `Date.now()` del último dato bueno. */
  readonly updatedAt: number | null
  readonly reload: () => void
}

/** Nombre visible de una entidad del Workspace (para etiquetar nodos del grafo). */
export interface EntityName {
  readonly name: string
  readonly type: EntityType
}

/** Recuento de `index_status` sobre una muestra de recursos, NO sobre el total del almacén. */
export interface ResourceIndexSample {
  readonly counts: Readonly<Record<IndexStatus, number>>
  /** Recursos contados (los de `resources`). */
  readonly sample: number
}

/**
 * Temas disponibles. «Hoy» y las fechas van en la zona del usuario (ajuste `default_timezone`; si
 * no hay, la del sistema) y cambian solas a medianoche.
 */
export interface JarvisData {
  /** `GET /today` en la zona del usuario. */
  readonly today: Snapshot<TodayResponse>
  /** Tareas abiertas (`pending`, `in_progress`, `on_hold`), sin archivadas; como mucho 200. */
  readonly tasks: Snapshot<readonly Task[]>
  /** Proyectos sin terminar (`planned`, `active`, `paused`), sin archivados; como mucho 200. */
  readonly projects: Snapshot<readonly Project[]>
  /** Hábitos sin archivar. */
  readonly habits: Snapshot<readonly Habit[]>
  /** Agenda expandida de [hoy, hoy + 7 días), en la zona del usuario. */
  readonly agenda: Snapshot<readonly AgendaItem[]>
  /** Horario de clases de hoy. */
  readonly timetable: Snapshot<readonly TimetableEntry[]>
  /** Relaciones del Workspace (para el grafo); como mucho 1000 (5 páginas de 200). */
  readonly relationships: Snapshot<readonly RelationshipOut[]>
  /** Recursos del almacén: la primera página del listado (30), sin filtros. */
  readonly resources: Snapshot<readonly ResourceSummary[]>
  /** Actividad reciente: los 50 últimos eventos de auditoría. */
  readonly activity: Snapshot<readonly AuditEvent[]>
  /** Estado de la memoria. */
  readonly memory: Snapshot<MemoryBackendStatus>
  /** Historial de los últimos 28 días (hoy incluido) de cada hábito de `habits`, por id. */
  readonly habitHistory: Snapshot<Readonly<Record<string, readonly HabitHistoryDay[]>>>
  /** Asignaturas sin archivar. */
  readonly subjects: Snapshot<readonly Subject[]>
  /** Carpetas raíz del almacén, con `resource_count`. */
  readonly folders: Snapshot<readonly Folder[]>
  /** `index_status` contado sobre los recursos de `resources` (muestra, no total). */
  readonly resourceIndex: Snapshot<ResourceIndexSample>
  /**
   * id → nombre y tipo, SOLO con lo ya cargado (tareas, proyectos, hábitos, asignaturas, recursos y
   * agenda). Una entidad que no esté en esas listas no aparece: muestra su tipo.
   */
  readonly entityNames: Snapshot<ReadonlyMap<string, EntityName>>
}

export type JarvisTopic = keyof JarvisData

/**
 * Hook único de datos. Solo carga los temas pedidos; se recargan solos tras un resync del enlace.
 * La lista de temas debe ser estable entre renders (constante de módulo).
 */
export type UseJarvisData = <K extends JarvisTopic>(topics: readonly K[]) => Pick<JarvisData, K>
