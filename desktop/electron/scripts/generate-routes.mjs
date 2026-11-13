#!/usr/bin/env node
/**
 * Genera `shared/routes.generated.ts` desde `contracts/api/routes.md`.
 * Uso: node scripts/generate-routes.mjs [ruta/a/routes.md]
 * Sin argumento lee el archivo del repositorio, o la rama `drakter/contratos`.
 */
import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const repoFile = resolve(here, '../../../contracts/api/routes.md')
const output = resolve(here, '../shared/routes.generated.ts')

function readContract() {
  const given = process.argv[2]
  if (given) return readFileSync(given, 'utf8')
  if (existsSync(repoFile)) return readFileSync(repoFile, 'utf8')
  return execFileSync('git', ['show', 'drakter/contratos:contracts/api/routes.md'], {
    cwd: here,
    encoding: 'utf8'
  })
}

/** Defensa por si una fila pierde su marca `(`approver`)`. */
function isApproverOnly(method, path) {
  if (/^\/api\/v1\/confirmations\/[^/]+\/(approve|reject|approval-token)$/.test(path)) return true
  if (path.startsWith('/api/v1/permissions')) return true
  // Aplicar o revertir una mejora cambia producción: la GUI con token `ui` no las llama (drakter-33).
  if (/^\/api\/v1\/improvement\/proposals\/[^/]+\/(apply|revert)$/.test(path)) return true
  return path.startsWith('/api/v1/storage-locations') && method !== 'GET'
}

// Lo que sigue a este título son desviaciones de los frentes, no rutas válidas.
const [routes] = readContract().split(/^## Desviaciones/m)
const rows = [...routes.matchAll(/^\| (GET|POST|PUT|PATCH|DELETE) \| `([^`]+)`(.*)$/gm)]
  .filter(([, , , rest]) => !rest.includes('(`approver`)'))
  .map(([, m, p]) => [m, p])
const seen = new Set()
const lines = []
for (const [method, path] of rows) {
  const key = `${method} ${path}`
  if (seen.has(key) || isApproverOnly(method, path)) continue
  seen.add(key)
  lines.push(`  ['${method}', '${path}'],`)
}
if (lines.length < 50) throw new Error(`Solo ${lines.length} rutas: el formato del contrato ha cambiado`)

writeFileSync(
  output,
  `// GENERADO por scripts/generate-routes.mjs desde contracts/api/routes.md. No editar.
export const GENERATED_ROUTES = [
${lines.join('\n').replace(/,$/, '')}
] as const
`
)
console.log(`${lines.length} rutas`)
