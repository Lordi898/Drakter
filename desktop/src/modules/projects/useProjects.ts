import { listProjects } from './api'
import type { ListPage, Project, ProjectListParams } from './types'
import { useLoad, type LoadState } from './useLoad'

/**
 * Lista de proyectos (una página) para vistas de solo lectura, como el HUD de Jarvis. Vuelve a pedirla
 * cuando cambian los parámetros o se llama a `reload`. `ProjectsPage` sigue con su propia paginación.
 */
export function useProjects(params: ProjectListParams = {}): LoadState<ListPage<Project>> {
  return useLoad(() => listProjects(params), JSON.stringify(params))
}
