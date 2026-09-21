import type { ECharts, EChartsOption } from 'echarts'

export interface PieChartDatum {
  name: string
  value: number
}

export interface BloggerDetailChartTheme {
  backgroundColor: string
  textColor: string
  mutedTextColor: string
  gridLineColor: string
  axisLineColor: string
  tooltipBackground: string
  tooltipTextColor: string
  tooltipBorderColor: string
  seriesColors: readonly string[]
}

export interface ChartResizeTarget {
  element: HTMLElement | null
  chart: ECharts | undefined
}

const fallbackTokens = {
  backgroundColor: '#ffffff',
  textColor: '#172033',
  mutedTextColor: '#7c879a',
  gridLineColor: '#eef1f5',
  axisLineColor: '#e6eaf1',
  tooltipBackground: '#203b57',
  tooltipTextColor: '#f7fbff',
  tooltipBorderColor: '#203b57',
  seriesColors: ['#52758a', '#7f9b9f', '#b19a78', '#96a7b5', '#728b95', '#a8b2aa'],
} as const

type CssTokenName = `--${string}`

function readCssToken(root: HTMLElement | null, name: CssTokenName, fallback: string): string {
  const view = root?.ownerDocument.defaultView
  if (!view || !root) return fallback

  const value = view.getComputedStyle(root).getPropertyValue(name).trim()
  if (!value) return fallback

  const variable = value.match(/^var\((--[\w-]+)\)$/)
  if (variable) return readCssToken(root, variable[1] as CssTokenName, fallback)
  return value
}

function getTokenRoot(target?: HTMLElement | null): HTMLElement | null {
  const document = target?.ownerDocument ?? (typeof globalThis.document !== 'undefined' ? globalThis.document : undefined)
  return document?.documentElement ?? null
}

export function createBloggerDetailChartTheme(target?: HTMLElement | null): BloggerDetailChartTheme {
  const root = getTokenRoot(target)
  const seriesColors = [1, 2, 3, 4, 5, 6].map((index) => readCssToken(
    root,
    `--chart-series-${index}`,
    fallbackTokens.seriesColors[index - 1],
  ))

  return {
    backgroundColor: readCssToken(root, '--chart-bg', readCssToken(root, '--surface', fallbackTokens.backgroundColor)),
    textColor: readCssToken(root, '--chart-text', readCssToken(root, '--ink', fallbackTokens.textColor)),
    mutedTextColor: readCssToken(root, '--chart-muted', readCssToken(root, '--muted', fallbackTokens.mutedTextColor)),
    gridLineColor: readCssToken(root, '--chart-grid', fallbackTokens.gridLineColor),
    axisLineColor: readCssToken(root, '--chart-axis', readCssToken(root, '--line', fallbackTokens.axisLineColor)),
    tooltipBackground: readCssToken(root, '--chart-tooltip-bg', fallbackTokens.tooltipBackground),
    tooltipTextColor: readCssToken(root, '--chart-tooltip-text', fallbackTokens.tooltipTextColor),
    tooltipBorderColor: readCssToken(root, '--chart-tooltip-border', fallbackTokens.tooltipBorderColor),
    seriesColors,
  }
}

function tooltip(theme: BloggerDetailChartTheme): NonNullable<EChartsOption['tooltip']> {
  return {
    trigger: 'item',
    confine: true,
    backgroundColor: theme.tooltipBackground,
    borderColor: theme.tooltipBorderColor,
    borderWidth: 1,
    textStyle: { color: theme.tooltipTextColor },
    extraCssText: 'box-shadow: 0 8px 20px rgb(16 38 63 / 18%);',
  }
}

export function createBloggerDetailPieOption(
  theme: BloggerDetailChartTheme,
  data: readonly PieChartDatum[],
): EChartsOption {
  return {
    backgroundColor: theme.backgroundColor,
    color: [...theme.seriesColors],
    legend: {
      type: 'scroll',
      bottom: 0,
      left: 'center',
      itemWidth: 12,
      itemHeight: 8,
      itemGap: 12,
      textStyle: { color: theme.mutedTextColor },
      pageTextStyle: { color: theme.mutedTextColor },
    },
    tooltip: {
      ...tooltip(theme),
      valueFormatter: (value: unknown) => `${Number(value).toFixed(2)}%`,
    },
    series: [{
      type: 'pie',
      center: ['50%', '42%'],
      radius: ['40%', '62%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: theme.backgroundColor, borderWidth: 2 },
      label: { formatter: '{b}\n{d}%', color: theme.textColor },
      labelLine: { lineStyle: { color: theme.mutedTextColor } },
      data: [...data],
    }],
  }
}

export function createBloggerDetailBarOption(
  theme: BloggerDetailChartTheme,
  categories: readonly string[],
  values: readonly number[],
): EChartsOption {
  return {
    backgroundColor: theme.backgroundColor,
    tooltip: {
      ...tooltip(theme),
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: { left: 34, right: 16, top: 14, bottom: 26, containLabel: true },
    xAxis: {
      type: 'category',
      data: [...categories],
      axisLine: { lineStyle: { color: theme.axisLineColor } },
      axisTick: { lineStyle: { color: theme.axisLineColor } },
      axisLabel: { color: theme.mutedTextColor },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: theme.gridLineColor } },
      axisLine: { lineStyle: { color: theme.axisLineColor } },
      axisLabel: { color: theme.mutedTextColor },
    },
    series: [{
      type: 'bar',
      barWidth: 22,
      itemStyle: { color: theme.seriesColors[0], borderRadius: [4, 4, 0, 0] },
      data: [...values],
    }],
  }
}

function resizeChart(chart: ECharts): void {
  if (typeof chart.isDisposed === 'function' && chart.isDisposed()) return
  chart.resize()
}

/**
 * Binds charts to their own container size and falls back to window resize when
 * ResizeObserver is unavailable. The returned cleanup is safe to call repeatedly.
 */
export function observeChartResize(targets: readonly ChartResizeTarget[]): () => void {
  const cleanups: Array<() => void> = []

  for (const { element, chart } of targets) {
    if (!element || !chart) continue

    const resize = () => resizeChart(chart)
    if (typeof ResizeObserver !== 'undefined') {
      const observer = new ResizeObserver(resize)
      observer.observe(element)
      cleanups.push(() => observer.disconnect())
      continue
    }

    const view = element.ownerDocument.defaultView
    view?.addEventListener('resize', resize)
    cleanups.push(() => view?.removeEventListener('resize', resize))
  }

  let cleaned = false
  return () => {
    if (cleaned) return
    cleaned = true
    cleanups.forEach((cleanup) => cleanup())
  }
}

export function disposeCharts(charts: readonly (ECharts | undefined)[]): void {
  charts.forEach((chart) => {
    if (!chart) return
    if (typeof chart.isDisposed === 'function' && chart.isDisposed()) return
    chart.dispose()
  })
}
