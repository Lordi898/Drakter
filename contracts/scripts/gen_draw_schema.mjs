#!/usr/bin/env node
// Genera contracts/floating/draw_args.schema.json desde el zod de `draw.mjs` (Roamies 8f0adaa, copia literal).
// Uso: node contracts/scripts/gen_draw_schema.mjs <ruta/a/draw.mjs> [salida]
// `draw.mjs` debe poder resolver `zod` (4.6.7) desde su carpeta. Contrato: docs/floating/CONTRACT.md §9.
// Reglas de Drakter sobre la salida: todo objeto lleva `additionalProperties: false` (más estricto que el
// `strip` de zod: lo que tidyDraw no recoloca es un error) y `$id`/`x-drakter-source` fijan el origen.
import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const [drawPath, outPath = 'contracts/floating/draw_args.schema.json'] = process.argv.slice(2)
if (!drawPath) {
  console.error('uso: gen_draw_schema.mjs <draw.mjs> [salida]')
  process.exit(2)
}
const abs = resolve(drawPath)
const { z } = await import(pathToFileURL(createRequire(abs).resolve('zod')).href)
const draw = await import(pathToFileURL(abs).href)

const schema = z.toJSONSchema(draw.DrawArgs, { io: 'output', unrepresentable: 'any', target: 'draft-2020-12' })
const close = (node) => {
  if (Array.isArray(node)) return node.forEach(close)
  if (!node || typeof node !== 'object') return
  if (node.type === 'object' && node.properties && node.additionalProperties === undefined) node.additionalProperties = false
  for (const value of Object.values(node)) close(value)
}
close(schema)
const source = readFileSync(abs)
const out = {
  $id: 'https://drakter.local/contracts/floating/draw_args.schema.json',
  'x-drakter-source': {
    upstream: 'KenKaiii/Roamies@8f0adaa showcase/tauri/sidecar/draw.mjs (DrawArgs)',
    sha256: createHash('sha256').update(source).digest('hex'),
    zod: '4.6.7',
    note: 'Valida los argumentos DESPUÉS de tidyDraw. Las reglas de checkDraw y las de Drakter (CONTRACT.md §9) van aparte.'
  },
  'x-drakter-limits': draw.LIMITS,
  'x-drakter-kinds': { screen: draw.SCREEN, actions: draw.ACTIONS, cards: draw.CARDS, tones: draw.TONES },
  ...schema
}
writeFileSync(outPath, JSON.stringify(out, null, 2) + '\n')
console.log(`${outPath}: ${draw.KINDS.length} tipos de marca`)
