import { backend, queryString } from '../remote'
import type { ActivityFilters, ActivityPage } from './types'

export const listActivity = (filters: ActivityFilters = {}, cursor?: string | null) =>
  backend<ActivityPage>('GET', `/activity${queryString({ ...filters, cursor })}`)
