import { describe, expect, it } from 'vitest'
import { isNonNegativeNumber } from '../../src/utils/validators'

describe('settings validation', () => {
  it('rejects negative shares and cost values', () => {
    expect(isNonNegativeNumber(0)).toBe(true)
    expect(isNonNegativeNumber(10.5)).toBe(true)
    expect(isNonNegativeNumber(-0.01)).toBe(false)
  })
})
