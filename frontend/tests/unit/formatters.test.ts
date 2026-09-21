import { describe, expect, it } from 'vitest'
import { formatCurrency, formatDate, formatPercent, valueTone } from '../../src/utils/formatters'

describe('formatters', () => {
  it('formats null values as placeholder', () => {
    expect(formatCurrency(null)).toBe('--')
    expect(formatPercent(null)).toBe('--')
  })
  it('formats currency, percent, and date for display', () => {
    expect(formatCurrency(1234.5)).toBe('¥1,234.50')
    expect(formatPercent(0.1568)).toBe('15.68%')
    expect(formatDate('2026-07-20')).toBe('2026年07月20日')
  })
  it('treats zero return as neutral in A-share display semantics', () => {
    expect(valueTone(0)).toBe('muted')
    expect(valueTone(0.01)).toBe('positive')
    expect(valueTone(-0.01)).toBe('negative')
  })
})
