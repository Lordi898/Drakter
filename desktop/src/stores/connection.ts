import { useSyncExternalStore } from 'react'
import { getLinkStatus, subscribeLinkStatus, type LinkStatus } from '@/services/ws'

export type { LinkStatus }

function subscribe(listener: () => void): () => void {
  return subscribeLinkStatus(listener)
}

export function useLinkStatus(): LinkStatus {
  return useSyncExternalStore(subscribe, getLinkStatus)
}
