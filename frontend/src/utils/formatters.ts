export function formatCurrency(value: number | null): string {
  if (value === null) return '--'
  return `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function formatPercent(value: number | null): string {
  if (value === null) return '--'
  return `${(value * 100).toFixed(2)}%`
}

export function formatDate(value: string): string {
  if (!value) return '--'
  const [year, month, day] = value.split('-')
  return `${year}年${month}月${day}日`
}

export function valueTone(value: number | null): 'positive' | 'negative' | 'muted' {
  if (value === null) return 'muted'
  if (value === 0) return 'muted'
  return value > 0 ? 'positive' : 'negative'
}
