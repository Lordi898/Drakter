export interface TextPart {
  readonly text: string
  readonly match: boolean
}

/** Pliega carácter a carácter: los índices siguen siendo válidos en el texto original. */
function fold(text: string): string {
  return Array.from({ length: text.length }, (_, index) => {
    const unit = text.charAt(index)
    const base = unit.normalize('NFD').charAt(0).toLowerCase()
    return base.length === 1 ? base : unit
  }).join('')
}

/** Marca los términos sin depender de sintaxis del contenido. Es solo presentación. */
export function highlightTerms(text: string, query: string): readonly TextPart[] {
  const folded = fold(text)
  const terms = fold(query).split(/\s+/).filter((term) => term.length > 0)
  const ranges: [number, number][] = []
  for (const term of terms) {
    for (let at = folded.indexOf(term); at !== -1; at = folded.indexOf(term, at + term.length)) {
      ranges.push([at, at + term.length])
    }
  }
  ranges.sort((a, b) => a[0] - b[0])

  const parts: TextPart[] = []
  let position = 0
  for (const [start, end] of ranges) {
    if (end <= position) continue
    const from = Math.max(start, position)
    if (from > position) parts.push({ text: text.slice(position, from), match: false })
    parts.push({ text: text.slice(from, end), match: true })
    position = end
  }
  if (position < text.length) parts.push({ text: text.slice(position), match: false })
  return parts
}
