export const LOCAL_COST_LABEL = 'local (no API cost)'

/** Format a USD cost, or label it as local when the model ran on Ollama. */
export function formatCost(value: number | null | undefined, digits: number, isLocal = false): string {
  if (isLocal) return LOCAL_COST_LABEL
  return `$${(value ?? 0).toFixed(digits)}`
}
