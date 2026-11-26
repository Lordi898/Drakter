export type ImprovementCategory =
  | 'communication_preference'
  | 'context_adjustment'
  | 'skill_fix'
  | 'procedure_improvement'
  | 'memory_retrieval'
  | 'performance'
  | 'interface'
  | 'bug_fix'
export type Severity = 'low' | 'medium' | 'high' | 'critical'
export type FeedbackOrigin = 'user' | 'agent' | 'system'
export type ProposalStatus =
  | 'draft'
  | 'evaluating'
  | 'evaluated_passed'
  | 'evaluated_failed'
  | 'evaluation_blocked'
  | 'approved'
  | 'applied'
  | 'reverted'
  | 'rejected'

/** Paginación por `offset` (desviación aceptada en v1). */
export interface OffsetPage<T> {
  readonly items: readonly T[]
  readonly total: number
  readonly limit: number
  readonly offset: number
}

export interface Feedback {
  readonly id: string
  readonly origin: FeedbackOrigin
  readonly author_id: string
  readonly body: string
  readonly category: ImprovementCategory
  readonly severity: Severity
  readonly classified_by: 'rules' | 'default' | 'user'
  readonly created_at: string
  readonly updated_at: string
}

export interface Proposal {
  readonly id: string
  readonly title: string
  readonly rationale: string
  readonly category: ImprovementCategory | null
  readonly feedback_id: string | null
  readonly author_kind: string
  readonly author_id: string
  readonly patch_sha256: string | null
  readonly patch_size: number | null
  readonly status: ProposalStatus
  readonly current_evaluation_id: string | null
  readonly pending_evaluation_id: string | null
  readonly approved_digest: string | null
  readonly approved_at: string | null
  readonly applied_branch: string | null
  readonly applied_commit: string | null
  readonly applied_at: string | null
  readonly reverted_at: string | null
  readonly rejected_at: string | null
  readonly rejection_reason: string | null
  readonly created_at: string
  readonly updated_at: string
}

export interface Evaluation {
  readonly id: string
  readonly status: 'passed' | 'failed' | 'blocked'
  readonly base_commit: string | null
  readonly patch_sha256: string | null
  readonly changed_paths: readonly string[]
  readonly protected_paths: readonly string[]
  readonly checks: unknown
  readonly reason: string | null
  readonly created_at: string
  readonly untrusted: true
}

/** Detalle: propuesta, su última evaluación y el parche (texto no confiable; nunca se ejecuta aquí). */
export interface ProposalDetail extends Proposal {
  readonly evaluation: Evaluation | null
  readonly patch: string | null
}

export interface ChangelogEvent {
  readonly seq: number
  readonly id: string
  readonly proposal_id: string | null
  readonly feedback_id: string | null
  readonly event_type: string
  readonly from_status: string | null
  readonly to_status: string | null
  readonly actor_kind: string
  readonly actor_id: string
  readonly detail: Record<string, unknown>
  readonly created_at: string
}

export interface ImprovementSummary {
  readonly from: string | null
  readonly to: string | null
  readonly feedback: {
    readonly total: number
    readonly by_type: Readonly<Record<string, number>>
    readonly by_severity: Readonly<Record<string, number>>
  }
  readonly proposals: {
    readonly total: number
    readonly by_status: Readonly<Record<string, number>>
    readonly by_type: Readonly<Record<string, number>>
  }
}

export interface FeedbackParams {
  readonly category?: ImprovementCategory
  readonly severity?: Severity
  readonly origin?: FeedbackOrigin
  readonly limit?: number
  readonly offset?: number
}

export interface ProposalParams {
  readonly status?: ProposalStatus
  readonly limit?: number
  readonly offset?: number
}

export interface ChangelogParams {
  readonly proposal_id?: string
  readonly limit?: number
  readonly offset?: number
}
