import { backend, queryString, runConfirmable } from '../remote'
import type {
  ChangelogEvent,
  ChangelogParams,
  Evaluation,
  Feedback,
  FeedbackParams,
  ImprovementCategory,
  ImprovementSummary,
  OffsetPage,
  Proposal,
  ProposalDetail,
  ProposalParams,
  Severity
} from './types'

export const listFeedback = (p: FeedbackParams = {}) =>
  backend<OffsetPage<Feedback>>('GET', `/improvement/feedback${queryString({ ...p })}`)

export const getFeedback = (id: string) => backend<Feedback>('GET', `/improvement/feedback/${id}`)

export const recordFeedback = (text: string) => backend<Feedback>('POST', '/improvement/feedback', { text })

export const reclassifyFeedback = (id: string, category: ImprovementCategory, severity: Severity) =>
  backend<Feedback>('PATCH', `/improvement/feedback/${id}/classification`, { category, severity })

export const listProposals = (p: ProposalParams = {}) =>
  backend<OffsetPage<Proposal>>('GET', `/improvement/proposals${queryString({ ...p })}`)

export const getProposal = (id: string) => backend<ProposalDetail>('GET', `/improvement/proposals/${id}`)

export const evaluateProposal = (id: string) => backend<Evaluation>('POST', `/improvement/proposals/${id}/evaluate`, {})

export const rejectProposal = (id: string, reason: string) =>
  backend<Proposal>('POST', `/improvement/proposals/${id}/reject`, { reason })

/** Pedir aprobar o revertir solo abre una confirmación (409): la decisión es del diálogo nativo. */
export const requestApproval = (id: string) =>
  runConfirmable(() => backend<unknown>('POST', `/improvement/proposals/${id}/approval-request`, {}))

export const requestRevert = (id: string) =>
  runConfirmable(() => backend<unknown>('POST', `/improvement/proposals/${id}/revert-request`, {}))

export const getSummary = (range: { readonly from?: string; readonly to?: string } = {}) =>
  backend<ImprovementSummary>('GET', `/improvement/reports/summary${queryString({ ...range })}`)

export const listChangelog = (p: ChangelogParams = {}) =>
  backend<OffsetPage<ChangelogEvent>>('GET', `/improvement/changelog${queryString({ ...p })}`)
