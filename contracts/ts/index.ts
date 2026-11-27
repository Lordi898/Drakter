// Generado: no editar. Fuente: contracts/python/drakter_contracts (scripts/gen_ts.py).
export const CONTRACT_VERSION = "1.0.0";
export const SCHEMA_VERSION = 11;

/** Listado con cursor opaco: `limit` lo acota el servidor. */
export interface Page<T> {
  items: T[];
  next_cursor: string | null;
  total?: number | null;
}

export type ActorType = "user" | "agent" | "automation" | "system";

export type AgentState = "idle" | "listening" | "thinking" | "speaking" | "executing" | "success" | "error" | "interrupted" | "offline";

export type AuditResult = "success" | "denied" | "failed" | "confirmation_required";

export type AvailabilityStatus = "available" | "missing" | "moved" | "unreachable" | "forbidden";

export type CalendarSourceType = "calendar_event" | "time_block" | "class_session";

export type ConfirmationRisk = "write" | "confirm";

export type ConfirmationStatus = "pending" | "approved" | "rejected" | "expired" | "executing" | "executed" | "failed";

export type EntityType = "task" | "project" | "habit" | "calendar_event" | "time_block" | "subject" | "class_session" | "resource" | "folder";

export type ErrorCode = "validation_error" | "internal_error" | "unauthorized" | "forbidden_client" | "forbidden_host" | "forbidden_origin" | "service_unavailable" | "not_found" | "conflict" | "invalid_query" | "permission_denied" | "revision_mismatch" | "hierarchy_cycle" | "relationship_not_allowed" | "has_dependents" | "nonexistent_local_time" | "invalid_timezone" | "unknown_setting" | "confirmation_required" | "confirmation_expired" | "confirmation_unavailable" | "confirmation_already_resolved" | "path_not_allowed" | "file_too_large" | "archive_limit_exceeded" | "unsupported_media_type" | "resource_unavailable" | "agent_unavailable" | "agent_busy" | "agent_timeout" | "agent_disconnected" | "provider_auth" | "provider_error" | "no_active_turn" | "tool_timeout" | "memory_unavailable" | "voice_unavailable" | "rate_limited";

export type EvaluationOutcome = "passed" | "failed" | "inconclusive";

export type EventKind = "event" | "reminder" | "work_session";

export type EventStatus = "tentative" | "confirmed" | "cancelled";

export type ExceptionKind = "cancelled" | "modified";

export type HabitRecordStatus = "done" | "skipped" | "missed";

export type HabitStatus = "active" | "paused" | "ended";

export type ImprovementCategory = "communication" | "context" | "skill" | "procedure" | "memory" | "performance" | "interface" | "bug";

export type ImprovementSource = "user" | "agent" | "system";

export type IndexStatus = "none" | "pending" | "indexed" | "failed" | "skipped";

export type InputSource = "text" | "voice";

export type JobState = "running" | "completed" | "failed" | "cancelled";

export type MemoryCategory = "profile" | "preferences" | "entities" | "events" | "cases" | "patterns";

export type MemoryConflictStatus = "open" | "resolved";

export type MemoryKind = "working" | "episodic" | "semantic" | "procedural";

export type MemorySourceType = "user_gui" | "user_conversation" | "agent" | "tool_result" | "document" | "import";

export type MemoryStatus = "pending" | "approved" | "rejected" | "superseded";

export type MemoryTrust = "user_confirmed" | "user_stated" | "derived" | "third_party";

export type MessageRole = "user" | "assistant" | "system";

export type MessageStatus = "streaming" | "complete" | "cancelled" | "failed";

export type NotificationSeverity = "info" | "success" | "warning" | "error";

export type Origin = "rest" | "mcp" | "scheduler" | "internal";

export type Priority = "low" | "medium" | "high" | "urgent";

export type ProgressSource = "manual" | "computed";

export type ProjectStatus = "planned" | "active" | "paused" | "completed" | "cancelled";

export type ProposalStatus = "draft" | "evaluating" | "ready" | "approved" | "rejected" | "applied" | "failed";

export type RelationshipType = "belongs_to" | "related_to" | "scheduled_for" | "uses_resource" | "depends_on" | "supports" | "studies" | "parent_of" | "references" | "derived_from";

export type ResourceType = "image" | "document" | "pdf" | "text" | "code" | "link" | "note" | "study_note" | "archive" | "other";

export type RiskClass = "read" | "write" | "confirm";

export type TaskStatus = "pending" | "in_progress" | "on_hold" | "completed" | "cancelled";

export type TimeBlockStatus = "planned" | "in_progress" | "done" | "skipped" | "cancelled";

export type TurnStatus = "queued" | "running" | "completed" | "failed" | "cancelled" | "interrupted";

export interface ActInAppArgs {
  window_id: string;
  steps: (StepClickText | StepClick | StepClickAt | StepFill | StepChoose | StepType | StepKey | StepScroll | StepHover | StepFocus | StepSet | StepWait)[];
  read_id?: string | null;
  shot_id?: string | null;
  confirm?: boolean;
}

export interface ActInAppResult {
  act_id: string;
  status: "done" | "stopped" | "failed";
  steps: StepOutcome[];
  window: WindowRef | null;
  read_id: string | null;
  envelope: UntrustedEnvelope | null;
}

export interface AgendaItem {
  occurrence_id: string;
  source_type: CalendarSourceType;
  source_id: string;
  title: string;
  description: string | null;
  location: string | null;
  kind: string;
  status: string;
  all_day: boolean;
  timezone: string;
  occurrence_local_start: string;
  starts_at_utc: string | null;
  ends_at_utc: string | null;
  start_date: string | null;
  end_date_exclusive: string | null;
  display_start: string | null;
  display_end: string | null;
  recurring: boolean;
  modified: boolean;
  room: string | null;
  subject_id: string | null;
  task_id: string | null;
  color: string | null;
}

export interface AgendaResponse {
  timezone: string;
  from_date: string;
  to_date: string;
  items: AgendaItem[];
  truncated: boolean;
}

export interface AgentError {
  session_id: string | null;
  turn_id: string | null;
  code: string;
  message: string;
  retryable: boolean;
}

export interface AgentExpressionChanged {
  expression: string;
  intensity: number | null;
  turn_id: string | null;
}

/** Lleva el texto completo: perder deltas se corrige solo. */
export interface AgentMessageCompleted {
  session_id: string;
  turn_id: string;
  message_id: string;
  text: string;
}

export interface AgentMessageDelta {
  session_id: string;
  turn_id: string;
  delta: string;
}

export interface AgentMessageStarted {
  session_id: string;
  turn_id: string;
  message_id: string;
}

export interface AgentStatusChanged {
  state: AgentState;
  previous: AgentState | null;
  turn_id: string | null;
  reason: string | null;
}

/** GET /agent/status. `detail` es texto seguro, sin secretos. */
export interface AgentStatusOut {
  state: AgentState;
  provider: string | null;
  model: string | null;
  detail: string | null;
}

export interface AgentToolCompleted {
  session_id: string;
  turn_id: string;
  tool: string;
  call_id: string;
  source: "drakter" | "hermes";
  error: boolean;
}

export interface AgentToolStarted {
  session_id: string;
  turn_id: string;
  tool: string;
  call_id: string;
  source: "drakter" | "hermes";
}

export interface AgentTurnCreate {
  conversation_id: string;
  input_source?: InputSource;
}

export interface AgentTurnFinished {
  session_id: string;
  turn_id: string;
  outcome: "completed" | "failed" | "cancelled" | "interrupted";
}

export interface AgentTurnOut {
  id: string;
  conversation_id: string;
  correlation_id: string;
  status: TurnStatus;
  input_source: InputSource;
  error_code: string | null;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
}

export interface AgentTurnStarted {
  session_id: string;
  turn_id: string;
  input_source: "text" | "voice";
}

export interface AgentTurnUpdate {
  status?: TurnStatus | null;
}

/** Solo lectura: la auditoría es append-only (trigger `audit_immutable`); no hay Create/Update públicos. `params` sale de la lista blanca de `ToolSpec.audit`: nunca claves ni contenido de documentos. */
export interface AuditEventOut {
  seq: number;
  id: string;
  occurred_at: string;
  correlation_id: string;
  actor_type: ActorType;
  origin: Origin;
  action: string;
  tool_name: string | null;
  entity_type: EntityType | null;
  entity_id: string | null;
  affected_count: number | null;
  params: Record<string, unknown> | null;
  params_hash: string | null;
  changes: Record<string, unknown> | null;
  result: AuditResult;
  error_code: string | null;
  confirmation_id: string | null;
  duration_ms: number | null;
  turn_id: string | null;
  tainted: boolean;
  agent_provider: string | null;
}

export interface AvailabilityResponse {
  available: boolean;
  starts_at_utc: string;
  ends_at_utc: string;
  conflicts: AgendaItem[];
}

/** Día completo: `start_date` + `end_date_exclusive`; si no, `local_start` + `local_end`. */
export interface CalendarEventCreate {
  title: string;
  description?: string | null;
  location?: string | null;
  kind?: EventKind;
  status?: EventStatus;
  timezone: string;
  all_day?: boolean;
  local_start?: string | null;
  local_end?: string | null;
  start_date?: string | null;
  end_date_exclusive?: string | null;
  rrule?: string | null;
  reminder_minutes_before?: number | null;
}

export interface CalendarEventOut {
  id: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  revision: number;
  title: string;
  description: string | null;
  location: string | null;
  kind: EventKind;
  status: EventStatus;
  timezone: string;
  all_day: boolean;
  local_start: string | null;
  local_end: string | null;
  start_date: string | null;
  end_date_exclusive: string | null;
  starts_at_utc: string | null;
  ends_at_utc: string | null;
  rrule: string | null;
  reminder_minutes_before: number | null;
}

export interface CalendarEventUpdate {
  title?: string | null;
  description?: string | null;
  location?: string | null;
  kind?: EventKind | null;
  status?: EventStatus | null;
  timezone?: string | null;
  all_day?: boolean | null;
  local_start?: string | null;
  local_end?: string | null;
  start_date?: string | null;
  end_date_exclusive?: string | null;
  rrule?: string | null;
  reminder_minutes_before?: number | null;
}

export interface CalendarEventWriteResult {
  event: CalendarEventOut;
  conflicts: AgendaItem[];
}

/** Sesión de chat en la API. `session_id` en rutas y eventos es `conversations.id`. */
export interface ChatSession {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  ended_at: string | null;
  status: "open" | "closed";
}

/** Mensaje del usuario ya guardado, escrito o dictado. El renderer adopta `session_id`. */
export interface ChatUserMessage {
  message_id: string;
  session_id: string;
  turn_id: string;
  text: string;
  input_source: "text" | "voice";
  created_at: string;
}

export interface ClassSessionCreate {
  weekday: number;
  starts_local_time: string;
  ends_local_time: string;
  timezone: string;
  valid_from: string;
  valid_until?: string | null;
  interval_weeks?: number;
  room?: string | null;
}

export interface ClassSessionOut {
  id: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  revision: number;
  subject_id: string;
  weekday: number;
  starts_local_time: string;
  ends_local_time: string;
  timezone: string;
  valid_from: string;
  valid_until: string | null;
  interval_weeks: number;
  room: string | null;
}

export interface ClassSessionUpdate {
  weekday?: number | null;
  starts_local_time?: string | null;
  ends_local_time?: string | null;
  timezone?: string | null;
  valid_from?: string | null;
  valid_until?: string | null;
  interval_weeks?: number | null;
  room?: string | null;
}

/** `status` y `shutdown` no llevan payload. */
export type CmdEmpty = Record<string, never>;

export interface CmdModeSet {
  mode: "standby" | "conversation";
  trigger: "wake" | "hotkey" | "ui" | "followup";
}

export interface CmdRtcOffer {
  sdp: string;
  type?: "offer";
  pc_id?: string | null;
  restart_pc?: boolean | null;
}

/** Modo flotante (docs/floating/CONTRACT.md §10): dice `text` como una locución propia con `speech_id`. Equivale a `speak.open` + `speak.delta` + `speak.close(completed)` en un solo comando. Se encola detrás de lo que ya suene en ese `turn_id` (FIFO, sin cortar ni ser cortada por otro tramo del mismo turno); la cortan `speak.stop` y el barge-in, como a cualquier tramo. Emite los `voice.playback` habituales con este `speech_id`. `ok{ignored: true}` si la voz está silenciada (`tts_enabled=false`) o sin conexión: el backend usa entonces el reloj local del overlay. */
export interface CmdSpeakBeat {
  turn_id: string;
  speech_id: number;
  guide_id: string;
  beat: number;
  text: string;
}

export interface CmdSpeakClose {
  speech_id: number;
  outcome: "completed" | "cancelled" | "failed";
}

/** Texto crudo con etiquetas. Duplicado o speech cortado → `ok{ignored: true}`. */
export interface CmdSpeakDelta {
  speech_id: number;
  seq: number;
  text: string;
}

export interface CmdSpeakFlush {
  speech_id: number;
}

/** Abre un tramo de habla. `speech_id` es monótono por proceso de backend. */
export interface CmdSpeakOpen {
  turn_id: string;
  speech_id: number;
}

export interface CmdSpeakPhrase {
  key: "ack_1" | "ack_2" | "ack_3" | "wait_1" | "wait_2" | "wait_3" | "tool_generic" | "confirm_on_screen" | "rest_on_screen" | "busy" | "job_started" | "job_done" | "job_failed" | "tts_fallback" | "offline" | "idle_nudge" | "goodbye" | "ui_jarvis" | "ui_drakter" | "ui_avatar" | "ui_layout" | "ui_floating_on" | "ui_floating_off" | "floating_unavailable";
  when?: "now" | "when_silent";
}

export interface CmdSpeakStop {
  speech_id?: number | null;
  reason: "barge_in" | "user" | "mute" | "new_turn" | "steered";
}

export interface CmdTurnPhase {
  turn_id: string;
  phase: "thinking" | "executing" | "done";
  tool?: string | null;
}

export interface CmdVoiceConfig {
  tts_enabled: boolean;
  profile: string;
  wake_enabled: boolean;
  expression: "off" | "llm";
}

export interface ComponentHealth {
  component: "backend" | "hermes" | "memory" | "voice" | "database";
  status: "ok" | "degraded" | "down";
  detail: string | null;
}

/** Cuerpo de approve, con rol `approver`. */
export interface ConfirmationApprove {
  params_hash: string;
}

/** Uso interno del backend; ninguna ruta pública la acepta. Los textos los calcula el backend. */
export interface ConfirmationCreate {
  tool_name: string;
  actor_type: ActorType;
  origin: Origin;
  turn_id?: string | null;
  correlation_id: string;
  args: Record<string, unknown>;
  targets?: ConfirmationTarget[];
  summary: string;
  affected_count?: number | null;
  risk: ConfirmationRisk;
}

/** `args` ya sin secretos (lista blanca de auditoría). `params_hash` es la columna `args_hash`. */
export interface ConfirmationOut {
  id: string;
  tool_name: string;
  actor_type: ActorType;
  origin: Origin;
  turn_id: string | null;
  correlation_id: string;
  args: Record<string, unknown>;
  params_hash: string;
  targets: ConfirmationTarget[];
  summary: string;
  affected_count: number | null;
  risk: ConfirmationRisk;
  status: ConfirmationStatus;
  created_at: string;
  expires_at: string;
  decided_at: string | null;
  decided_via: "desktop" | null;
  executed_at: string | null;
  result: Record<string, unknown> | null;
  error_code: string | null;
}

export interface ConfirmationRequested {
  action_id: string;
  session_id: string | null;
  turn_id: string | null;
  tool: string;
  summary: string;
  affected_count: number | null;
  expires_at: string;
  job_id: string | null;
}

/** HTTP 409 con `error.code == "confirmation_required"`. Nunca 2xx. */
export interface ConfirmationRequiredEnvelope {
  error: ErrorBody;
  confirmation: ConfirmationTicket;
}

export interface ConfirmationResolved {
  action_id: string;
  status: "approved" | "rejected" | "expired" | "executed" | "failed";
  error_code: string | null;
}

export interface ConfirmationTarget {
  entity_type: string;
  entity_id: string;
  revision: number | null;
}

/** `summary` y `affected_count` los calcula el backend. `params_hash` es `args_hash` de la fila. */
export interface ConfirmationTicket {
  id: string;
  summary: string;
  affected_count: number | null;
  expires_at: string;
  params_hash: string;
}

/** Sin nombre ni valor: esos textos van en el sobre (`#id rol «nombre» = valor`). */
export interface ControlInfo {
  id: number;
  role: string;
  rect: LogicalRect | null;
  states: string[];
  actions: string[];
  editable: boolean;
  offscreen: boolean;
  secret: boolean;
}

export interface ConversationCreate {
  title?: string | null;
}

/** No es entidad (0007): sin revision ni archived_at; `ended_at` cierra la conversación. */
export interface ConversationOut {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  ended_at: string | null;
}

export interface ConversationUpdate {
  title?: string | null;
}

export interface DrawDoneIn {
  type: "draw_done";
  guide_id: string;
}

export interface DrawStartedIn {
  type: "draw_started";
  guide_id: string;
  seg: number;
}

/** Envoltura de `draw`. El esquema que ve el modelo es `contracts/floating/draw_args.schema.json` (generado del zod de `draw.mjs`, versión lean); la validación real es: tidyDraw → JSON Schema → checkDraw → reglas Drakter. */
export interface DrawToolArgs {
  target?: string | null;
  beats?: Record<string, unknown>[] | null;
  edit?: Record<string, unknown>[] | null;
  deep?: boolean | null;
  keep?: boolean | null;
}

export interface DrawToolResult {
  guide_id: string;
  status: "done" | "waiting" | "edited";
  waiting_beat: number | null;
  wait: "click" | "hover" | null;
  drawn: DrawnPart[];
  on_screen: DrawnPart[];
  missing: MissingTarget[];
  said: string[];
  notes: string[];
}

export interface DrawWaitDoneIn {
  type: "draw_wait_done";
  guide_id: string;
  beat: number;
  result: "clicked" | "hovered" | "timeout" | "skipped";
}

export interface DrawnPart {
  part: string;
  kind: string;
  label: string | null;
}

/** Campos de `entities` que expone toda entidad de dominio (0001). */
export interface EntityCoreOut {
  id: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  revision: number;
}

/** Entidad que además expone `metadata` en la API (tareas, proyectos, eventos). */
export interface EntityOut {
  id: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  revision: number;
  metadata: Record<string, unknown>;
}

export interface EntityTagsReplace {
  names: string[];
}

export interface ErrorBody {
  code: string;
  message: string;
  request_id: string;
  details: ErrorDetail[];
}

export interface ErrorDetail {
  field: string | null;
  code: string;
  message: string;
}

export interface ErrorEnvelope {
  error: ErrorBody;
}

export interface EventEnvelope {
  event_id: string;
  seq: number;
  boot_id: string;
  timestamp: string;
  type: string;
  version: number;
  correlation_id: string | null;
  payload: Record<string, unknown>;
}

export interface EvtError {
  code: string;
  stage: "transport" | "stt" | "turn" | "tts" | "ipc" | "wake";
  recoverable: boolean;
  turn_id: string | null;
  message: string | null;
}

/** Orden de la capa 0, ya aplicada por la voz. `ui_jarvis`/`ui_drakter`: cambiar el modo de la interfaz (el backend publica `ui.mode`). `ui_floating_on`/`ui_floating_off`: «modo flotante» / «quita el modo flotante» (el backend publica `ui.floating`, docs/floating/CONTRACT.md §10). `ui_appearance`: cambiar el avatar o la interfaz Jarvis, con exactamente uno de `avatar` o `layout` (el backend publica `ui.appearance`). */
export interface EvtLocalCommand {
  command: "stop_speech" | "rest" | "close" | "ui_jarvis" | "ui_drakter" | "ui_appearance" | "ui_floating_on" | "ui_floating_off";
  utt_id: string;
  avatar: "holo-contorno" | "holo-hilo" | "holo-busto" | "holo-orbe" | "holo-filamento" | "ascuario" | "relojero" | "filamento" | "none" | null;
  layout: "nucleo" | "holomesa" | "visor" | null;
}

/** Sin texto. `agent_ttft_ms` lo mide el backend. */
export interface EvtMetrics {
  turn_id: string | null;
  endpointing_ms: number | null;
  stt_ms: number | null;
  tts_ttfa_ms: number | null;
  total_ms: number | null;
  false_ducks: number | null;
}

/** `heard_tail`/`pending_head` solo con `state="interrupted"`: texto hablado, no el del chat. */
export interface EvtPlayback {
  turn_id: string;
  speech_id: number;
  state: "started" | "sentence_done" | "finished" | "interrupted";
  sentence_index: number;
  heard_tail: string | null;
  pending_head: string | null;
}

export interface EvtReady {
  pipecat: string;
  stt: string;
  tts: string;
  wake: boolean;
}

export interface EvtState {
  connected: boolean;
  mode: "standby" | "conversation";
  tts: "fish" | "local";
  profile: string;
}

/** Una vez por arranque. `from` es palabra reservada en Python: el atributo es `from_`. */
export interface EvtTtsFallback {
  from: "fish";
  to: "local";
  reason: "auth" | "quota" | "rate_limit" | "network" | "expired" | "unknown";
}

export interface EvtUserSpeech {
  utt_id: string;
  phase: "started" | "stopped";
}

export interface EvtUserTurn {
  utt_id: string;
  text: string;
  lang: "es";
  trigger: "wake" | "hotkey" | "ui" | "followup";
  overlap: "none" | "bot_speaking" | "agent_busy";
  audio_ms: number;
  stt_ms: number;
  eot_ms: number;
}

/** `POST /api/v1/overlay/presence`. Al arrancar, en cada cambio y cada 30 s; caduca a los 75 s. */
export interface FloatingPresence {
  active: boolean;
  ready: boolean;
  companion: "ok" | "missing" | "outdated" | "denied" | "unsupported_session";
  monitor?: MonitorInfo | null;
  bridge_version?: number;
}

export interface FolderCreate {
  name: string;
  parent_folder_id?: string | null;
}

export interface FolderOut {
  id: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  revision: number;
  name: string;
  parent_folder_id: string | null;
  resource_count: number;
}

export interface FolderUpdate {
  name?: string | null;
  parent_folder_id?: string | null;
  expected_revision?: number | null;
}

export interface FreeSlot {
  starts_at_utc: string;
  ends_at_utc: string;
  display_start: string;
  display_end: string;
}

export interface GuideWaitArgs {
  guide_id: string;
}

export interface GuideWaitResult {
  guide_id: string;
  beat: number;
  result: "clicked" | "hovered" | "timeout" | "skipped";
  status: "waiting" | "done" | "stopped";
  waiting_beat: number | null;
  wait: "click" | "hover" | null;
  said: string[];
  notes: string[];
}

export interface HabitCreate {
  name: string;
  description?: string | null;
  timezone: string;
  rrule: string;
  start_date: string;
  end_date?: string | null;
  goal_note?: string | null;
  goal_project_id?: string | null;
  preferred_local_time?: string | null;
  reminder_enabled?: boolean;
}

export interface HabitHistory {
  habit_id: string;
  from_date: string;
  to_date: string;
  days: HabitHistoryDay[];
}

export interface HabitHistoryDay {
  date: string;
  scheduled: boolean;
  status: HabitRecordStatus | null;
  note: string | null;
}

export interface HabitOut {
  id: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  revision: number;
  name: string;
  description: string | null;
  timezone: string;
  rrule: string;
  schedule_versions: HabitScheduleVersionOut[];
  status: HabitStatus;
  start_date: string;
  end_date: string | null;
  goal_note: string | null;
  goal_project_id: string | null;
  preferred_local_time: string | null;
  reminder_enabled: boolean;
  today_scheduled: boolean;
  today_status: HabitRecordStatus | null;
}

/** PUT de un día (idempotente por habit_id + occurrence_date). */
export interface HabitRecordCreate {
  status: HabitRecordStatus;
  note?: string | null;
}

/** Fila de `habit_records`: no es entidad (sin archived_at ni revision). */
export interface HabitRecordOut {
  id: string;
  habit_id: string;
  occurrence_date: string;
  status: HabitRecordStatus;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface HabitRecordUpdate {
  status?: HabitRecordStatus | null;
  note?: string | null;
}

export interface HabitScheduleVersionOut {
  id: string;
  rrule: string;
  valid_from: string;
  valid_until: string | null;
}

export interface HabitStatistics {
  habit_id: string;
  from_date: string;
  to_date: string;
  scheduled: number;
  done: number;
  skipped: number;
  missed: number;
  unrecorded: number;
  completion_rate: number | null;
  current_streak: number;
  best_streak: number;
  by_weekday: WeekdayStat[];
}

export interface HabitUpdate {
  name?: string | null;
  description?: string | null;
  timezone?: string | null;
  rrule?: string | null;
  schedule_effective_from?: string | null;
  end_date?: string | null;
  status?: HabitStatus | null;
  goal_note?: string | null;
  goal_project_id?: string | null;
  preferred_local_time?: string | null;
  reminder_enabled?: boolean | null;
}

export interface HandsStepBounds {
  bounds: number[];
  hover: boolean;
}

export interface HealthOut {
  status: "ok" | "degraded" | "down";
  components: ComponentHealth[];
}

/** Imagen que acompaña a un resultado (modo flotante, docs/floating/CONTRACT.md §8.1). Nunca entra en `data` ni en la auditoría: el puente MCP la añade como `ImageContent` detrás del texto (que lleva el sobre no confiable). Máximo 1 por resultado en v1; lado largo ≤ 1568 px. */
export interface ImageAttachment {
  mime_type: "image/png" | "image/jpeg";
  data_b64: string;
  width: number;
  height: number;
  sha256: string;
}

export interface ImprovementEvaluationCreate {
  proposal_id: string;
  environment: string;
  outcome: EvaluationOutcome;
  report_path?: string | null;
}

export interface ImprovementEvaluationOut {
  id: string;
  proposal_id: string;
  environment: string;
  outcome: EvaluationOutcome;
  report_path: string | null;
  created_at: string;
}

export interface ImprovementFeedbackCreate {
  source: ImprovementSource;
  category: ImprovementCategory;
  summary: string;
  correlation_id?: string | null;
}

export interface ImprovementFeedbackOut {
  id: string;
  source: ImprovementSource;
  category: ImprovementCategory;
  summary: string;
  correlation_id: string | null;
  created_at: string;
}

export interface ImprovementProposalCreate {
  title: string;
  category: ImprovementCategory;
  summary: string;
  feedback_id?: string | null;
  created_by?: ImprovementSource;
}

export interface ImprovementProposalOut {
  id: string;
  title: string;
  category: ImprovementCategory;
  summary: string;
  status: ProposalStatus;
  feedback_id: string | null;
  document_path: string | null;
  git_ref: string | null;
  created_by: ImprovementSource;
  created_at: string;
  updated_at: string;
  decided_at: string | null;
  decided_via: "desktop" | null;
  applied_at: string | null;
}

/** Aprobar, rechazar o aplicar solo lo decide la GUI; la automejora nunca toca producción sin ello. */
export interface ImprovementProposalUpdate {
  title?: string | null;
  summary?: string | null;
  status?: "approved" | "rejected" | null;
}

export interface InkActionIn {
  type: "ink_action";
  part: string;
}

export interface InkClearedIn {
  type: "ink_cleared";
}

export interface InkClosedIn {
  type: "ink_closed";
  part: string;
}

export interface InkPinnedIn {
  type: "ink_pinned";
  part: string;
  on: boolean;
}

export interface IpcErr {
  code: string;
  message: string;
}

export interface IpcMessage {
  kind: "evt" | "cmd" | "ok" | "err";
  id: string;
  type: string;
  payload: Record<string, unknown>;
}

export interface JobFinished {
  job_id: string;
  state: "completed" | "failed" | "cancelled";
  reason: string | null;
  pending_actions: number;
  finished_at: string;
}

export interface JobList {
  items: JobOut[];
}

export interface JobOut {
  job_id: string;
  title: string;
  state: JobState;
  reason: string | null;
  pending_actions: number;
  created_at: string;
  finished_at: string | null;
  elapsed_s: number;
  tool_calls: number;
  last_tool: string | null;
}

export interface JobProgress {
  job_id: string;
  state: "running";
  elapsed_s: number;
  tool_calls: number;
  last_tool: string | null;
}

export interface JobStarted {
  job_id: string;
  title: string;
  lane: string;
  created_at: string;
}

export interface JobStatusItem {
  job_id: string;
  title: string;
  state: JobState;
  elapsed_s: number;
  tool_calls: number;
  last_tool: string | null;
  pending_actions: number;
}

export interface JobsAmendArgs {
  job_id: string;
  text: string;
}

export interface JobsAmendResult {
  accepted: boolean;
  mode: "redirected" | "queued";
}

export interface JobsCancelArgs {
  job_id: string;
}

export interface JobsCancelResult {
  job_id: string;
  state: "cancelled";
}

export interface JobsStartArgs {
  title: string;
  brief: string;
}

export interface JobsStartResult {
  job_id: string;
  state: "running";
}

export interface JobsStatusArgs {
  job_id?: string | null;
}

export interface JobsStatusResult {
  jobs: JobStatusItem[];
}

export type ListWindowsArgs = Record<string, never>;

export interface ListWindowsResult {
  windows: WindowRef[];
  monitors: MonitorInfo[];
  front_window_id: string | null;
  envelope: UntrustedEnvelope;
}

export interface LogicalRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface LookScreenArgs {
  target?: "front" | "screen" | "window";
  window_id?: string | null;
  zoom?: ZoomRegion | null;
  cursor?: boolean;
}

/** `logical = origin + px_captura * scale_to_logical`. La imagen viaja aparte (`attachments`, ImageContent MCP). */
export interface LookScreenResult {
  shot_id: string;
  image: ShotImage;
  origin: number[];
  scale_to_logical: number;
  window: WindowRef | null;
  taken_at: string;
  envelope: UntrustedEnvelope;
}

export interface MemoryConflictOut {
  id: string;
  memory_a: string;
  memory_b: string;
  reason: string;
  status: MemoryConflictStatus;
  created_at: string;
  resolved_at: string | null;
  kept: string | null;
}

export interface MemoryConflictResolve {
  kept: string;
}

export interface MemoryEntityRef {
  entity_type: EntityType;
  entity_id: string;
}

/** De dónde salió un recuerdo. Lo fija el backend; nunca lo manda el cliente. */
export interface MemoryProvenance {
  source_type: MemorySourceType;
  source_ref: string | null;
  session_id: string | null;
  captured_at: string;
}

/** Alta desde la GUI (`POST /api/v1/memory`). La memoria es dato no confiable: nunca modifica reglas, permisos ni confirmaciones. El origen (`provenance`) lo pone el backend. */
export interface MemoryRecordCreate {
  kind: MemoryKind;
  category: MemoryCategory;
  subject?: string;
  content: string;
  abstract?: string;
  overview?: string;
  confidence?: number;
  valid_until?: string | null;
  entity_refs?: MemoryEntityRef[];
}

/** No es entidad. `seq` es interno y no se expone. */
export interface MemoryRecordOut {
  id: string;
  kind: MemoryKind;
  category: MemoryCategory;
  subject: string;
  content: string;
  abstract: string;
  overview: string;
  provenance: MemoryProvenance;
  trust: MemoryTrust;
  confidence: number;
  valid_until: string | null;
  status: MemoryStatus;
  content_hash: string;
  supersedes: string | null;
  entity_refs: MemoryEntityRef[];
  created_at: string;
  updated_at: string;
}

/** `PATCH /api/v1/memory/{id}`. Aprobar, rechazar u olvidar van por sus rutas. */
export interface MemoryRecordUpdate {
  subject?: string | null;
  content?: string | null;
  abstract?: string | null;
  overview?: string | null;
  kind?: MemoryKind | null;
  category?: MemoryCategory | null;
  valid_until?: string | null;
}

/** Resultado de búsqueda: solo L0 (`abstract`); L1/L2 se leen bajo demanda. Dato no confiable. */
export interface MemorySearchHit {
  id: string;
  kind: MemoryKind;
  category: MemoryCategory;
  abstract: string;
  score: number;
  trust: MemoryTrust;
  provenance: MemoryProvenance;
  updated_at: string;
}

/** Respuesta 202 de POST /chat/sessions/{id}/messages. */
export interface MessageAccepted {
  turn_id: string;
  message_id: string;
}

/** Mensaje del usuario; arranca un turno. `client_message_id` evita duplicados al reintentar. */
export interface MessageCreate {
  text: string;
  client_message_id: string;
  input_source?: InputSource;
}

/** En la API se llaman `session_id` y `text`; en la BD, `conversation_id` y `content`. */
export interface MessageOut {
  id: string;
  session_id: string;
  turn_id: string | null;
  role: MessageRole;
  text: string;
  status: MessageStatus;
  created_at: string;
}

/** Solo cancelación de un mensaje en streaming. */
export interface MessageUpdate {
  status?: MessageStatus | null;
}

export interface MissingTarget {
  beat: number;
  mark: number;
  reason: "not_found" | "off_screen" | "stale_shot" | "stale_read" | "no_window" | "hands_off";
}

export interface MonitorInfo {
  index: number;
  geometry: LogicalRect;
  workarea: LogicalRect;
  scale: number;
  primary: boolean;
}

export interface NotificationCreate {
  kind: string;
  title: string;
  body?: string | null;
  severity?: NotificationSeverity;
  entity_id?: string | null;
  dedupe_key?: string | null;
}

export interface NotificationCreated {
  notification_id: string;
  kind: string;
  title: string;
  severity: "info" | "success" | "warning" | "error";
}

/** No es entidad: sin revision ni archived_at. */
export interface NotificationOut {
  id: string;
  kind: string;
  title: string;
  body: string | null;
  severity: NotificationSeverity;
  entity_id: string | null;
  created_at: string;
  read_at: string | null;
  dedupe_key: string | null;
}

/** PATCH: marcar leída (`true`) o no leída (`false`). */
export interface NotificationUpdate {
  read?: boolean | null;
}

export interface OccurrenceOverride {
  title?: string | null;
  description?: string | null;
  local_start?: string | null;
  local_end?: string | null;
  room?: string | null;
}

export interface OpenTargetArgs {
  url?: string | null;
  app_id?: string | null;
  location_id?: string | null;
  relative_path?: string | null;
  confirm?: boolean;
}

export interface OpenTargetResult {
  opened: boolean;
  kind: "url" | "app" | "file";
  display: string;
}

export interface OverlapGroup {
  items: string[];
  starts_at_utc: string;
  ends_at_utc: string;
}

/** Un beat ya resuelto, con la forma que espera `ink.js` (Roamies `SC/tools.mjs:739-743`). `marks` son marcas de `draw.mjs` con los objetivos ya resueltos (`at.rect`, `to.rect`, `tie.rect`, `points` en px lógicos globales) y `part` asignada. Electron main las vuelve a validar con `draw.mjs` + zod. */
export interface OverlayBeat {
  say: string;
  marks: Record<string, unknown>[];
  wait: "click" | "hover" | null;
  n: number;
  caption: string;
  voiced: boolean;
  read: number | null;
}

/** `overlay.clipboard`: Electron main copia `text` al portapapeles (botón `copy` de una tarjeta, pulsado por el usuario). */
export interface OverlayClipboard {
  part: string;
  text: string;
}

/** `overlay.draw`: un segmento (= un beat) de un dibujo. El bridge lo entrega como `{kind:'agent', e:{type:'draw', id: guide_id, seg, last, beats, edits, win, busy, fade?, deep?}}`. */
export interface OverlayDraw {
  guide_id: string;
  turn_id: string;
  call_id: string;
  seg: number;
  last: boolean;
  beats: OverlayBeat[];
  edits: Record<string, unknown>[];
  win: number[] | null;
  busy: number[][];
  fade: number | null;
  deep: boolean | null;
  speech_id: number | null;
}

/** `overlay.hands` → `{kind:'hands', on}` | `{kind:'hands', step:{bounds, hover}}`. Exactamente uno. */
export interface OverlayHands {
  act_id: string;
  on: boolean | null;
  step: HandsStepBounds | null;
}

/** `overlay.ink_clear` → `{kind:'agent', e:{type:'ink_clear', ...}}` (`ink.js:2380-2384`). */
export interface OverlayInkClear {
  screen: boolean | null;
  stop: boolean | null;
  parts: string[] | null;
  all: boolean | null;
  guide_id: string | null;
}

/** `overlay.ink_stale` → `{kind:'agent', e:{type:'ink_stale'}}`: lo no fijado se desvanece. */
export interface OverlayInkStale {
  reason: "focus_changed" | "window_moved" | "window_closed";
}

/** `overlay.trail` → `{kind:'agent', e:{type:'trail', steps, head, final}}` (tarjeta de pasos). */
export interface OverlayTrail {
  act_id: string;
  steps: TrailStep[];
  head: string;
  final: boolean;
}

export interface ProjectCreate {
  name: string;
  description?: string | null;
  status?: ProjectStatus;
  priority?: Priority;
  start_date?: string | null;
  target_date?: string | null;
  manual_progress?: number | null;
  objective?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ProjectOut {
  id: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  revision: number;
  metadata: Record<string, unknown>;
  name: string;
  description: string | null;
  status: ProjectStatus;
  priority: Priority;
  start_date: string | null;
  target_date: string | null;
  completed_at: string | null;
  manual_progress: number | null;
  objective: string | null;
  progress: ProjectProgress | null;
}

export interface ProjectProgress {
  project_id: string;
  total: number;
  completed: number;
  open: number;
  cancelled: number;
  overdue: number;
  percent: number;
  computed_percent: number;
  source: ProgressSource;
}

export interface ProjectUpdate {
  name?: string | null;
  description?: string | null;
  status?: ProjectStatus | null;
  priority?: Priority | null;
  start_date?: string | null;
  target_date?: string | null;
  manual_progress?: number | null;
  objective?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface ReadWindowArgs {
  window_id?: string | null;
  max_controls?: number;
  include_text?: boolean;
}

export interface ReadWindowResult {
  read_id: string;
  window: WindowRef;
  controls: ControlInfo[];
  text_truncated: boolean;
  redacted: number;
  envelope: UntrustedEnvelope;
}

export interface RecurrenceExceptionCreate {
  occurrence_local_start: string;
  kind: ExceptionKind;
  override?: OccurrenceOverride | null;
}

export interface RecurrenceExceptionOut {
  id: string;
  source_type: "calendar_event" | "class_session";
  source_id: string;
  occurrence_local_start: string;
  kind: ExceptionKind;
  override: OccurrenceOverride | null;
  created_at: string;
}

export interface RecurrenceExceptionUpdate {
  kind?: ExceptionKind | null;
  override?: OccurrenceOverride | null;
}

export interface RelatedItem {
  relationship_id: string | null;
  relationship_type: RelationshipType;
  direction: "in" | "out";
  label: string;
  entity_id: string;
  entity_type: EntityType;
  entity_title: string;
  archived: boolean;
  virtual: boolean;
  metadata: Record<string, unknown>;
}

export interface RelatedItems {
  entity_id: string;
  entity_type: EntityType;
  entity_title: string;
  items: RelatedItem[];
}

export interface RelationshipCreate {
  source_id: string;
  target_id: string;
  relationship_type: RelationshipType;
  metadata?: Record<string, unknown>;
}

/** No es entidad: sin revision ni archived_at (0006). */
export interface RelationshipOut {
  id: string;
  source_id: string;
  source_type: EntityType;
  target_id: string;
  target_type: EntityType;
  relationship_type: RelationshipType;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface RelationshipSearch {
  source_id?: string | null;
  target_id?: string | null;
  entity_type?: EntityType | null;
  relationship_type?: RelationshipType | null;
  limit?: number;
  cursor?: string | null;
}

export interface RelationshipTypeOut {
  relationship_type: RelationshipType;
  label: string;
  inverse_label: string;
  description: string;
  symmetric: boolean;
  allowed_pairs: [EntityType, EntityType][];
}

export interface RelationshipUpdate {
  metadata?: Record<string, unknown> | null;
}

export interface ResourceCreate {
  title: string;
  resource_type?: ResourceType | null;
  folder_id?: string | null;
  location_id?: string | null;
  relative_path?: string | null;
  url?: string | null;
  note_body?: string | null;
  description?: string | null;
  tags?: string[];
  index_content?: boolean;
}

export interface ResourceOut {
  id: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  revision: number;
  title: string;
  resource_type: ResourceType;
  folder_id: string | null;
  location_id: string | null;
  relative_path: string | null;
  url: string | null;
  description: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  content_hash: string | null;
  source_modified_at: string | null;
  availability_status: AvailabilityStatus;
  index_status: IndexStatus;
  indexed_at: string | null;
  index_error_code: string | null;
  has_note_body: boolean;
  index_content: boolean;
  tags: string[];
}

export interface ResourceReadRequest {
  selector?: string | null;
  offset?: number;
  max_chars?: number;
}

/** El contenido va siempre como dato no confiable (ver `UntrustedEnvelope`). */
export interface ResourceReadResult {
  resource_id: string;
  title: string;
  text: string;
  truncated: boolean;
  next_offset: number | null;
  metadata: Record<string, string | number | boolean | null>;
  content_trust: "untrusted";
}

export interface ResourceSearchHit {
  resource: ResourceOut;
  snippet: string;
  content_trust: "untrusted";
}

export interface ResourceUpdate {
  title?: string | null;
  folder_id?: string | null;
  note_body?: string | null;
  description?: string | null;
  tags?: string[] | null;
  index_content?: boolean | null;
  expected_revision?: number | null;
}

export interface RtcAnswer {
  sdp: string;
  type: "answer";
  pc_id: string;
}

/** Búsqueda global (`search_documents`): metadatos y fragmento; sin contenido completo. */
export interface SearchHitOut {
  entity_type: EntityType;
  entity_id: string;
  title: string;
  snippet: string;
  archived: boolean;
  content_trust: "untrusted";
}

export interface SetFloatingArgs {
  on?: boolean | null;
  size?: "default" | "small" | "cursor" | null;
  pin?: "top-left" | "top-right" | "bottom-left" | "bottom-right" | "center" | "release" | null;
}

export interface SetFloatingResult {
  delivered: boolean;
  available: boolean;
  active: boolean;
  note: string;
}

/** Los secretos no van en ajustes (README §4). Los ajustes sensibles exigen confirmación. */
export interface SettingCreate {
  key: string;
  value: string;
}

export interface SettingOut {
  key: string;
  value: string;
  updated_at: string;
}

export interface SettingUpdate {
  value: string;
}

export interface ShotImage {
  width: number;
  height: number;
  mime_type: "image/png" | "image/jpeg";
  sha256: string;
}

export interface SpeakAck {
  ignored: boolean;
}

export interface StatusResult {
  state: Record<string, unknown>;
  metrics_last: Record<string, unknown> | null;
}

export interface StepChoose {
  do: "choose";
  field?: string | null;
  id?: number | null;
  option: string;
}

export interface StepClick {
  do: "click";
  id: number;
  button?: "left" | "right" | "middle";
  double?: boolean;
}

/** Último recurso: px de la captura `shot_id` del acto. */
export interface StepClickAt {
  do: "click_at";
  x: number;
  y: number;
  button?: "left" | "right" | "middle";
  double?: boolean;
}

export interface StepClickText {
  do: "click_text";
  text: string;
  near?: string | null;
  button?: "left" | "right" | "middle";
  double?: boolean;
}

export interface StepFill {
  do: "fill";
  field?: string | null;
  id?: number | null;
  text: string;
}

export interface StepFocus {
  do: "focus";
  id: number;
}

export interface StepHover {
  do: "hover";
  text?: string | null;
  id?: number | null;
}

export interface StepKey {
  do: "key";
  combo: string;
  repeat?: number;
}

export interface StepOutcome {
  index: number;
  do: string;
  status: "ok" | "failed" | "refused" | "skipped";
  code: string | null;
  message: string | null;
}

export interface StepScroll {
  do: "scroll";
  direction?: "up" | "down" | "left" | "right";
  amount?: number;
  to_end?: boolean;
  id?: number | null;
}

/** Valor de un control (deslizador, interruptor, casilla) por AT-SPI. */
export interface StepSet {
  do: "set";
  id: number;
  value: boolean | number | string;
}

/** Escribe en el campo con el foco; falla si el foco no está en un campo editable. */
export interface StepType {
  do: "type";
  text: string;
}

export interface StepWait {
  do: "wait";
  ms?: number;
  until_text?: string | null;
}

export interface StorageIndexProgress {
  job_id: string;
  done: number;
  total: number | null;
  state: "running" | "completed" | "failed";
}

export interface StorageLocationCreate {
  path: string;
  label: string;
  read_only?: boolean;
  agent_read?: boolean;
}

/** No es entidad. `root_dev` y `root_ino` no se exponen. */
export interface StorageLocationOut {
  id: string;
  path: string;
  label: string;
  read_only: boolean;
  agent_read: boolean;
  enabled: boolean;
  created_at: string;
}

export interface StorageLocationUpdate {
  label?: string | null;
  read_only?: boolean | null;
  agent_read?: boolean | null;
  enabled?: boolean | null;
}

export interface StorageRefreshResult {
  checked: number;
  available: number;
  missing: number;
  moved: number;
  forbidden: number;
  reindexed: number;
  failed: number;
}

export interface StorageScanRequest {
  location_id: string;
}

export interface StorageScanResult {
  location_id: string;
  seen: number;
  added: number;
  updated: number;
  missing: number;
  moved: number;
  skipped: number;
  truncated: boolean;
}

export interface SubjectCreate {
  name: string;
  description?: string | null;
  teacher?: string | null;
  color?: string | null;
}

export interface SubjectOut {
  id: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  revision: number;
  name: string;
  description: string | null;
  teacher: string | null;
  color: string | null;
  session_count: number;
}

export interface SubjectUpdate {
  name?: string | null;
  description?: string | null;
  teacher?: string | null;
  color?: string | null;
}

export interface SystemHealthChanged {
  component: "backend" | "hermes" | "memory" | "voice" | "database";
  status: "ok" | "degraded" | "down";
  detail: string | null;
}

export interface SystemInfoOut {
  contract_version: string;
  schema_version: number;
  boot_id: string;
  started_at: string;
  default_timezone: string;
}

export interface SystemResyncRequired {
  reason: "buffer_overflow" | "boot_changed" | "client_lagging";
}

export interface TagCreate {
  name: string;
  color?: string | null;
}

export interface TagOut {
  id: string;
  name: string;
  color: string | null;
  usage_count: number | null;
}

export interface TagUpdate {
  name?: string | null;
  color?: string | null;
}

export interface TaskCompleteRequest {
  complete_subtasks?: boolean;
}

export interface TaskCreate {
  title: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: Priority;
  start_at?: string | null;
  due_at?: string | null;
  due_date?: string | null;
  estimated_minutes?: number | null;
  parent_task_id?: string | null;
  project_id?: string | null;
  subject_id?: string | null;
  position?: number | null;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface TaskDependencyCreate {
  depends_on_task_id: string;
}

export interface TaskOut {
  id: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  revision: number;
  metadata: Record<string, unknown>;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: Priority;
  start_at: string | null;
  due_at: string | null;
  due_date: string | null;
  completed_at: string | null;
  estimated_minutes: number | null;
  parent_task_id: string | null;
  project_id: string | null;
  subject_id: string | null;
  position: number;
  tags: TagOut[];
  depth: number;
  subtask_count: number;
  completed_subtask_count: number;
  blocked: boolean;
}

export interface TaskRef {
  id: string;
  title: string;
  status: TaskStatus;
}

/** Cuerpo de PUT /tasks/{id}/tags: sustituye todas las etiquetas de la tarea. */
export interface TaskTagsReplace {
  names: string[];
}

export interface TaskUpdate {
  title?: string | null;
  description?: string | null;
  status?: TaskStatus | null;
  priority?: Priority | null;
  start_at?: string | null;
  due_at?: string | null;
  due_date?: string | null;
  estimated_minutes?: number | null;
  parent_task_id?: string | null;
  project_id?: string | null;
  subject_id?: string | null;
  position?: number | null;
  tags?: string[] | null;
  metadata?: Record<string, unknown> | null;
}

export interface TimeBlockCreate {
  title: string;
  description?: string | null;
  timezone: string;
  local_start: string;
  local_end: string;
  status?: TimeBlockStatus;
  task_id?: string | null;
}

export interface TimeBlockOut {
  id: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  revision: number;
  title: string;
  description: string | null;
  timezone: string;
  local_start: string;
  local_end: string;
  starts_at_utc: string;
  ends_at_utc: string;
  status: TimeBlockStatus;
  task_id: string | null;
}

export interface TimeBlockUpdate {
  title?: string | null;
  description?: string | null;
  timezone?: string | null;
  local_start?: string | null;
  local_end?: string | null;
  status?: TimeBlockStatus | null;
  task_id?: string | null;
}

export interface TimeBlockWriteResult {
  time_block: TimeBlockOut;
  conflicts: AgendaItem[];
}

export interface Timetable {
  on_date: string;
  entries: TimetableEntry[];
}

export interface TimetableEntry {
  session_id: string;
  subject_id: string;
  subject_name: string;
  color: string | null;
  teacher: string | null;
  weekday: number;
  starts_local_time: string;
  ends_local_time: string;
  timezone: string;
  room: string | null;
  valid_from: string;
  valid_until: string | null;
  interval_weeks: number;
}

/** `summary` lo calcula el backend desde los argumentos, nunca el modelo. */
export interface ToolConfirmationRequired {
  status: "confirmation_required";
  action_id: string;
  summary: string;
  expires_at: string;
}

export interface ToolErrorBody {
  code: string;
  message: string;
  retryable: boolean;
  details: Record<string, unknown>[];
}

export interface ToolFailed {
  status: "error";
  error: ToolErrorBody;
}

/** Una entrada de contracts/tools/catalog.json. */
export interface ToolManifest {
  name: string;
  domain: string;
  description: string;
  permission: string;
  risk: RiskClass;
  idempotent: boolean;
  returns_untrusted: boolean;
  timeout_s: number;
  errors: string[];
  args_model: string;
  result_model: string;
  phase: string;
}

export interface ToolOk {
  status: "ok";
  data: Record<string, unknown>;
}

export interface TrailStep {
  text: string;
  state: "" | "now" | "ok" | "bad";
  why: string | null;
}

export interface TurnRef {
  session_id: string;
  turn_id: string;
}

/** Petición de cambiar el avatar y/o la interfaz del modo Jarvis. Solo estética: el renderer guarda la preferencia; el backend no guarda estado. Al menos uno de `avatar` o `layout`. `source`: `voice` (capa 0, frase cerrada) o `agent` (herramienta de apariencia). */
export interface UiAppearanceRequested {
  avatar: "holo-contorno" | "holo-hilo" | "holo-busto" | "holo-orbe" | "holo-filamento" | "ascuario" | "relojero" | "filamento" | "none" | null;
  layout: "nucleo" | "holomesa" | "visor" | null;
  source: "voice" | "agent";
  utt_id: string | null;
}

/** Pide activar/desactivar el modo flotante o cambiar el avatar flotante. Solo estética; decide Electron main. `source`: `voice` (capa 0, frase cerrada) o `agent` (`ui_set_floating`). Al menos uno de `action`, `size`, `pin`. */
export interface UiFloatingRequested {
  action: "on" | "off" | "toggle" | null;
  size: "default" | "small" | "cursor" | null;
  pin: "top-left" | "top-right" | "bottom-left" | "bottom-right" | "center" | "release" | null;
  source: "voice" | "agent";
  utt_id: string | null;
}

/** Petición de cambiar el modo de la interfaz. El renderer decide si la aplica; no hay estado en el backend. `source`: `voice` (capa 0 de la voz, frase cerrada) o `agent` (herramienta `ui_set_mode`). `utt_id`: el del enunciado, solo si viene de la voz. */
export interface UiModeRequested {
  mode: "jarvis" | "drakter";
  source: "voice" | "agent";
  utt_id: string | null;
}

/** Sobre obligatorio de todo contenido de documentos o memoria. */
export interface UntrustedEnvelope {
  trust: "untrusted";
  source_type: string;
  source_id: string;
  retrieved_at: string;
  content_hash: string;
  truncated: boolean;
  content: string;
}

export interface VoiceActivateIn {
  trigger: "hotkey" | "ui";
}

export interface VoiceError {
  code: string;
  stage: "transport" | "stt" | "turn" | "tts" | "ipc" | "wake";
  recoverable: boolean;
  turn_id: string | null;
  message: string | null;
}

export interface VoiceModeIn {
  mode: "standby" | "conversation";
}

export interface VoiceOfferIn {
  sdp: string;
  type?: "offer";
  pc_id?: string | null;
  restart_pc?: boolean | null;
}

export interface VoiceOfferOut {
  sdp: string;
  type: "answer";
  pc_id: string;
}

/** Progreso de reproducción. Sin texto: lo oído viaja solo por IPC al backend. */
export interface VoicePlayback {
  turn_id: string;
  speech_id: number;
  state: "started" | "sentence_done" | "finished" | "interrupted";
  sentence_index: number;
}

/** Perfil de voz activo. Lleva el nombre del perfil, nunca su ID de Fish. */
export interface VoiceProfileChanged {
  profile: string;
  previous: string | null;
}

export interface VoiceState {
  connected: boolean;
  mode: "standby" | "conversation";
  tts: "fish" | "local";
  profile: string;
  wake_enabled: boolean;
}

/** `VoiceState` (el payload de `voice.state`) más las últimas métricas, sin texto. */
export interface VoiceStatusOut {
  connected: boolean;
  mode: "standby" | "conversation";
  tts: "fish" | "local";
  profile: string;
  wake_enabled: boolean;
  metrics_last: Record<string, unknown> | null;
}

export interface WeekdayStat {
  weekday: number;
  scheduled: number;
  done: number;
}

/** Ventana sin texto de terceros: el título va, si acaso, en el sobre no confiable. */
export interface WindowRef {
  window_id: string;
  app_id?: string | null;
  pid: number;
  client: "wayland" | "x11";
  frame: LogicalRect;
  monitor: number;
  focused: boolean;
  fullscreen?: boolean;
  hands_off?: boolean;
  drakter?: boolean;
}

export interface WorkspaceEntityChange {
  entity_type: EntityType;
  entity_id: string;
  revision: number;
  changed_fields: string[];
  actor_type: ActorType;
}

export interface WorkspaceRelationshipChange {
  relationship_id: string;
  relationship_type: string;
  source_type: EntityType;
  source_id: string;
  target_type: EntityType;
  target_id: string;
  actor_type: ActorType;
}

/** Recorte de una captura anterior del mismo turno, en px de esa captura. */
export interface ZoomRegion {
  shot_id: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Unión discriminada por `status`. */
export type ToolOutcome = ToolOk | ToolFailed | ToolConfirmationRequired;

export interface EventPayloads {
  "agent.status_changed": AgentStatusChanged;
  "agent.expression_changed": AgentExpressionChanged;
  "agent.turn_started": AgentTurnStarted;
  "agent.turn_finished": AgentTurnFinished;
  "agent.message_started": AgentMessageStarted;
  "agent.message_delta": AgentMessageDelta;
  "agent.message_completed": AgentMessageCompleted;
  "agent.tool_started": AgentToolStarted;
  "agent.tool_completed": AgentToolCompleted;
  "agent.error": AgentError;
  "chat.user_message": ChatUserMessage;
  "confirmation.requested": ConfirmationRequested;
  "confirmation.resolved": ConfirmationResolved;
  "workspace.entity_created": WorkspaceEntityChange;
  "workspace.entity_updated": WorkspaceEntityChange;
  "workspace.entity_archived": WorkspaceEntityChange;
  "workspace.entity_restored": WorkspaceEntityChange;
  "workspace.entity_deleted": WorkspaceEntityChange;
  "workspace.relationship_created": WorkspaceRelationshipChange;
  "workspace.relationship_deleted": WorkspaceRelationshipChange;
  "storage.index_progress": StorageIndexProgress;
  "notification.created": NotificationCreated;
  "system.health_changed": SystemHealthChanged;
  "system.resync_required": SystemResyncRequired;
  "job.started": JobStarted;
  "job.progress": JobProgress;
  "job.finished": JobFinished;
  "voice.state": VoiceState;
  "voice.playback": VoicePlayback;
  "voice.error": VoiceError;
  "voice.profile_changed": VoiceProfileChanged;
  "ui.mode": UiModeRequested;
  "ui.appearance": UiAppearanceRequested;
  "ui.floating": UiFloatingRequested;
  "overlay.draw": OverlayDraw;
  "overlay.ink_clear": OverlayInkClear;
  "overlay.ink_stale": OverlayInkStale;
  "overlay.hands": OverlayHands;
  "overlay.trail": OverlayTrail;
  "overlay.clipboard": OverlayClipboard;
}

export type EventType = keyof EventPayloads;

export type TypedEvent = {
  [K in EventType]: Omit<EventEnvelope, "type" | "payload"> & { type: K; payload: EventPayloads[K] };
}[EventType];
