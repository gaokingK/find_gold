import { describe, expect, it } from 'vitest'
import { service } from '../../src/services'

describe('mock service', () => {
  it('filters observing bloggers and hides unavailable metrics as null', async () => {
    const bloggers = await service.listBloggers({ status: 'observing' })
    expect(bloggers).toHaveLength(1)
    expect(bloggers[0].observeDays).toBeLessThan(30)
    expect(bloggers[0].returnRate).toBeNull()
    expect(bloggers[0].profit).toBeNull()
    expect(bloggers[0].maxDrawdown).toBeNull()
  })
  it('returns a suspected duplicate in OCR mock data and counts confirmations', async () => {
    const result = await service.recognizeScreenshot(new File(['demo'], 'review.png', { type: 'image/png' }), '2026-07-20')
    expect(result.records.some((record) => record.suspectedDuplicate)).toBe(true)
    const records = result.records.map((record, index) => ({ ...record, reviewAction: index === 0 ? 'accepted' as const : 'rejected' as const }))
    await expect(service.confirmOcrRecords(result.screenshotId, records)).resolves.toEqual({ accepted: 1, rejected: 1 })
  })
})
