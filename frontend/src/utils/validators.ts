export function isNonNegativeNumber(value: number): boolean {
  return Number.isFinite(value) && value >= 0
}

export function isFiniteAmount(value: number): boolean {
  return Number.isFinite(value) && value >= 0
}
