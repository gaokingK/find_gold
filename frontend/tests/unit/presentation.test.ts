import { describe, expect, it } from 'vitest'
import {
  getActiveNavPath,
  getAsyncStatePresentation,
  getPageFeedback,
  getPageRouteMetadata,
  getVisualTone,
  isNavItemActive,
  navigationItems,
} from '../../src/utils/presentation'

describe('presentation adapters', () => {
  it('keeps A-share value tone semantics for positive, negative, zero, and null values', () => {
    expect(getVisualTone(0.01)).toBe('positive')
    expect(getVisualTone(-0.01)).toBe('negative')
    expect(getVisualTone(0)).toBe('muted')
    expect(getVisualTone(null)).toBe('muted')
  })

  it('provides stable async and feedback presentation values', () => {
    expect(getAsyncStatePresentation('loading')).toEqual({ tone: 'default', label: '加载中', icon: '…' })
    expect(getAsyncStatePresentation('empty').tone).toBe('muted')
    expect(getPageFeedback('error')).toEqual({ kind: 'error', title: '操作失败', description: '请稍后重试。' })
  })

  it('maps blogger details to the overview navigation state and route metadata', () => {
    expect(navigationItems).toHaveLength(4)
    expect(getActiveNavPath('/bloggers/42')).toBe('/')
    expect(isNavItemActive('/', '/bloggers/42')).toBe(true)
    expect(isNavItemActive('/history', '/bloggers/42')).toBe(false)
    expect(getPageRouteMetadata('/bloggers/42')).toMatchObject({ title: '博主详情', pathLabel: 'FUND TRACKER / BLOGGER' })
    expect(getPageRouteMetadata('/history')).toMatchObject({ title: '历史记录', path: '/history' })
  })
})
