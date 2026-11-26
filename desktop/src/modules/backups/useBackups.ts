import { useCallback, useState } from 'react'
import { useRemote, type RemoteState } from '../remote'
import { createBackup, deleteBackup, exportWorkspace, listBackups, verifyBackup } from './api'
import type { BundleInfo } from './types'

export function useBackups(): RemoteState<readonly BundleInfo[]> {
  return useRemote(listBackups, 'backups')
}

/** Crear, exportar, verificar y borrar (este último pide confirmación). Tras cambiar algo llama a `onChanged`. */
export function useBackupActions(onChanged?: () => void) {
  const [busy, setBusy] = useState(false)
  const run = useCallback(
    async <T,>(call: () => Promise<T>, changes: boolean): Promise<T> => {
      setBusy(true)
      try {
        const result = await call()
        if (changes) onChanged?.()
        return result
      } finally {
        setBusy(false)
      }
    },
    [onChanged]
  )
  return {
    busy,
    create: (includeStorage = false) => run(() => createBackup(includeStorage), true),
    exportAll: () => run(exportWorkspace, true),
    verify: (name: string) => run(() => verifyBackup(name), false),
    remove: (name: string) => run(() => deleteBackup(name), false)
  }
}
