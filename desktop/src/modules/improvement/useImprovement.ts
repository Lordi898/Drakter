import { useCallback, useState } from 'react'
import { useRemote, type RemoteState } from '../remote'
import {
  evaluateProposal, getProposal, getSummary, listChangelog, listFeedback, listProposals,
  recordFeedback, rejectProposal, requestApproval, requestRevert
} from './api'
import type {
  ChangelogEvent, ChangelogParams, Feedback, FeedbackParams, ImprovementSummary,
  OffsetPage, Proposal, ProposalDetail, ProposalParams
} from './types'

export function useFeedback(params: FeedbackParams = {}): RemoteState<OffsetPage<Feedback>> {
  return useRemote(() => listFeedback(params), JSON.stringify(params))
}

export function useProposals(params: ProposalParams = {}): RemoteState<OffsetPage<Proposal>> {
  return useRemote(() => listProposals(params), JSON.stringify(params))
}

export function useProposal(id: string | null): RemoteState<ProposalDetail> {
  return useRemote(() => getProposal(id ?? ''), id ?? '', id !== null)
}

export function useChangelog(params: ChangelogParams = {}): RemoteState<OffsetPage<ChangelogEvent>> {
  return useRemote(() => listChangelog(params), JSON.stringify(params))
}

export function useImprovementSummary(range: { readonly from?: string; readonly to?: string } = {}): RemoteState<ImprovementSummary> {
  return useRemote(() => getSummary(range), JSON.stringify(range))
}

/**
 * Acciones del ciclo. `requestApproval` y `requestRevert` devuelven `confirmation`: ya queda pendiente
 * en `stores/confirmations`. Aplicar no está aquí: lo ejecuta el backend tras una aprobación real.
 */
export function useImprovementActions(onChanged?: () => void) {
  const [busy, setBusy] = useState(false)
  const run = useCallback(
    async <T,>(call: () => Promise<T>): Promise<T> => {
      setBusy(true)
      try {
        const result = await call()
        onChanged?.()
        return result
      } finally {
        setBusy(false)
      }
    },
    [onChanged]
  )
  return {
    busy,
    sendFeedback: (text: string) => run(() => recordFeedback(text)),
    evaluate: (id: string) => run(() => evaluateProposal(id)),
    reject: (id: string, reason: string) => run(() => rejectProposal(id, reason)),
    requestApproval: (id: string) => run(() => requestApproval(id)),
    requestRevert: (id: string) => run(() => requestRevert(id))
  }
}
