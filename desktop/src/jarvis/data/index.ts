/**
 * Datos de las interfaces Jarvis. STUB de J1: todos los temas quedan en `loading`, sin red, para que
 * las interfaces compilen y se monten mientras D1 lo implementa (misma firma, `types.ts`).
 */
import { useMemo } from 'react'
import type { JarvisData, JarvisTopic, Snapshot, UseJarvisData } from './types'

export type { JarvisData, JarvisTopic, Snapshot, SnapshotStatus, UseJarvisData } from './types'

const LOADING: Snapshot<never> = { status: 'loading', data: null, error: null, updatedAt: null, reload: () => undefined }

export const useJarvisData: UseJarvisData = <K extends JarvisTopic>(topics: readonly K[]) =>
  useMemo(() => {
    const out: Partial<Record<JarvisTopic, Snapshot<never>>> = {}
    for (const topic of topics) out[topic] = LOADING
    return out as Pick<JarvisData, K>
  }, [topics])
