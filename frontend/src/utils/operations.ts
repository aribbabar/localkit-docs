export function createOperationId(): string {
  if ('randomUUID' in crypto) return crypto.randomUUID()
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function formatPhase(phase?: string): string {
  if (!phase) return 'Working'
  return phase.replace(/^\w/, (letter) => letter.toUpperCase())
}
