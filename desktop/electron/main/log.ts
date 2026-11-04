/** Una entrada, una línea: los saltos y caracteres de control no llegan a la terminal. */
function toSingleLine(text: string): string {
  return text.replace(/[\p{Cc}\u2028\u2029]+/gu, ' ').trim()
}

export function logError(scope: string, message: string, detail?: string): void {
  const suffix = detail ? ` | ${toSingleLine(detail)}` : ''
  console.error(`[drakter:${toSingleLine(scope)}] ${toSingleLine(message)}${suffix}`)
}

export function describeError(reason: unknown): string {
  if (reason instanceof Error) return reason.stack ?? `${reason.name}: ${reason.message}`
  return String(reason)
}
