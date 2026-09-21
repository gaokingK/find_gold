import type { ECharts } from 'echarts'
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  createBloggerDetailBarOption,
  createBloggerDetailChartTheme,
  createBloggerDetailPieOption,
  disposeCharts,
  observeChartResize,
} from '../../src/utils/chartTheme'

describe('Blogger Detail chart presentation adapter', () => {
  afterEach(() => {
    document.documentElement.removeAttribute('style')
    vi.unstubAllGlobals()
  })

  it('maps visual CSS tokens without borrowing A-share semantic colors', () => {
    document.documentElement.style.setProperty('--chart-text', '#334455')
    document.documentElement.style.setProperty('--chart-grid', '#ddeeff')
    document.documentElement.style.setProperty('--chart-series-1', '#526f7e')
    document.documentElement.style.setProperty('--chart-tooltip-bg', '#203b57')

    const theme = createBloggerDetailChartTheme()
    const pie = createBloggerDetailPieOption(theme, [{ name: '基金 A', value: 25 }])
    const bar = createBloggerDetailBarOption(theme, ['2025-01'], [2])

    expect(theme.textColor).toBe('#334455')
    expect(theme.gridLineColor).toBe('#ddeeff')
    expect((pie.color as string[])[0]).toBe('#526f7e')
    expect((pie.color as string[])).not.toContain('#d45d5d')
    expect((pie.color as string[])).not.toContain('#0d8b67')
    expect((bar.yAxis as { splitLine: { lineStyle: { color: string } } }).splitLine.lineStyle.color).toBe('#ddeeff')
    expect((bar.tooltip as { confine: boolean }).confine).toBe(true)
  })

  it('keeps chart data in the view-facing option inputs', () => {
    const theme = createBloggerDetailChartTheme()
    const pie = createBloggerDetailPieOption(theme, [{ name: '基金 A', value: 40 }])
    const bar = createBloggerDetailBarOption(theme, ['2025-01', '2025-02'], [1, 3])

    expect((pie.series as Array<{ data: unknown }>)[0].data).toEqual([{ name: '基金 A', value: 40 }])
    expect((bar.xAxis as { data: string[] }).data).toEqual(['2025-01', '2025-02'])
    expect((bar.series as Array<{ data: number[] }>)[0].data).toEqual([1, 3])
  })

  it('binds resize and disposes charts through safe lifecycle helpers', () => {
    vi.stubGlobal('ResizeObserver', undefined)
    const resize = vi.fn()
    const dispose = vi.fn()
    const chart = { resize, dispose, isDisposed: () => false } as unknown as ECharts
    const element = document.createElement('div')
    document.body.appendChild(element)

    const cleanup = observeChartResize([{ element, chart }])
    window.dispatchEvent(new Event('resize'))
    expect(resize).toHaveBeenCalledOnce()

    cleanup()
    window.dispatchEvent(new Event('resize'))
    expect(resize).toHaveBeenCalledOnce()

    disposeCharts([chart])
    expect(dispose).toHaveBeenCalledOnce()
    element.remove()
  })
})
