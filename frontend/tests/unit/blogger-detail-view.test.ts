import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import BloggerDetailView from '../../src/views/BloggerDetailView.vue'
import FeedbackRegion from '../../src/components/FeedbackRegion.vue'
import MetricCard from '../../src/components/MetricCard.vue'
import PageHeader from '../../src/components/PageHeader.vue'
import OperationTable from '../../src/components/OperationTable.vue'
import PositionTable from '../../src/components/PositionTable.vue'
import SurfaceCard from '../../src/components/SurfaceCard.vue'
import { service } from '../../src/services'
import type { BloggerDetail } from '../../src/types/domain'

const mocks = vi.hoisted(() => ({
  route: { params: { id: '42' } },
  push: vi.fn(),
  init: vi.fn(),
}))
const resizeObserverInstances: Array<{ callback: ResizeObserverCallback; element?: Element }> = []

class TestResizeObserver {
  private readonly record: { callback: ResizeObserverCallback; element?: Element }

  constructor(callback: ResizeObserverCallback) {
    this.record = { callback }
    resizeObserverInstances.push(this.record)
  }

  observe(element: Element): void {
    this.record.element = element
  }
  disconnect(): void {}
}

vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ push: mocks.push }),
}))

vi.mock('echarts', () => ({ init: mocks.init }))

const detail: BloggerDetail = {
  id: 42,
  name: '示例博主',
  sector: '科技',
  observeStartDate: '2025-01-01',
  observeDays: 30,
  status: 'active',
  returnRate: null,
  profit: null,
  maxDrawdown: null,
  operationCount: 2,
  positions: [{
    fundId: 1,
    fundName: '成长基金',
    fundCode: '000001',
    shares: 10,
    costBasis: 100,
    currentNav: 11,
    marketValue: 110,
    profit: 10,
    allocation: 0.6,
  }],
  operations: [{
    id: 1,
    bloggerId: 42,
    fundId: 1,
    fundName: '成长基金',
    operationDate: '2025-01-02',
    operationType: 'buy',
    amount: 100,
    shares: 10,
    screenshotId: 3,
    reviewAction: 'accepted',
    suspectedDuplicate: false,
  }],
  monthlyOperationCount: [{ month: '2025-01', count: 2 }],
}

function chart(): { setOption: ReturnType<typeof vi.fn>; resize: ReturnType<typeof vi.fn>; dispose: ReturnType<typeof vi.fn>; isDisposed: () => boolean } {
  return { setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn(), isDisposed: () => false }
}

function mountDetail() {
  return mount(BloggerDetailView, { global: { plugins: [ElementPlus] } })
}

describe('BloggerDetailView', () => {
  beforeEach(() => {
    mocks.push.mockReset()
    mocks.init.mockReset()
    mocks.init.mockImplementation(() => chart())
    resizeObserverInstances.length = 0
    vi.stubGlobal('ResizeObserver', TestResizeObserver)
    vi.spyOn(service, 'getBloggerDetail').mockResolvedValue(detail)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('keeps the detail structure, metrics, tables, and navigation entries', async () => {
    const wrapper = mountDetail()
    await flushPromises()

    expect(vi.mocked(service.getBloggerDetail)).toHaveBeenCalledWith(42)
    expect(wrapper.findComponent(PageHeader).props('title')).toBe('示例博主')
    expect(wrapper.findComponent(PageHeader).text()).toContain('科技')
    expect(wrapper.findAllComponents(MetricCard)).toHaveLength(4)
    expect(wrapper.findAllComponents(SurfaceCard)).toHaveLength(4)
    expect(wrapper.findComponent(PositionTable).props('positions')).toEqual(detail.positions)
    expect(wrapper.findComponent(OperationTable).props('operations')).toEqual(detail.operations)
    expect(wrapper.text()).toContain('--')
    expect(wrapper.text()).toContain('30 天')

    await wrapper.get('button[aria-label="返回总览"]').trigger('click')
    await wrapper.get('button[aria-label="导入新截图"]').trigger('click')
    expect(mocks.push).toHaveBeenNthCalledWith(1, '/')
    expect(mocks.push).toHaveBeenNthCalledWith(2, '/import')
  })

  it('keeps metric tones and final-shaped loading skeletons', async () => {
    let resolveDetail!: (value: BloggerDetail) => void
    vi.mocked(service.getBloggerDetail).mockReturnValueOnce(new Promise((resolve) => { resolveDetail = resolve }))
    const wrapper = mountDetail()

    expect(wrapper.find('.detail-loading').exists()).toBe(true)
    expect(wrapper.findAllComponents(MetricCard)).toHaveLength(4)
    expect(wrapper.findAllComponents(SurfaceCard)).toHaveLength(4)
    expect(wrapper.find('.detail-skeleton-chart').exists()).toBe(true)

    resolveDetail(detail)
    await flushPromises()
    const metricCards = wrapper.findAllComponents(MetricCard)
    expect(metricCards[0].props('tone')).toBe('muted')
    expect(metricCards[1].props('tone')).toBe('muted')
    expect(metricCards[2].props('tone')).toBe('muted')
  })

  it('shows a stable error feedback with a return action', async () => {
    vi.mocked(service.getBloggerDetail).mockRejectedValueOnce(new Error('详情服务不可用'))
    const wrapper = mountDetail()
    await flushPromises()

    const feedback = wrapper.findComponent(FeedbackRegion)
    expect(feedback.exists()).toBe(true)
    expect(feedback.props('description')).toBe('详情服务不可用')
    await feedback.get('button').trigger('click')
    expect(mocks.push).toHaveBeenCalledWith('/')
  })

  it('initializes chart data and cleans up resize listeners and charts', async () => {
    const wrapper = mountDetail()
    await flushPromises()

    expect(mocks.init).toHaveBeenCalledTimes(2)
    const [pie, bar] = mocks.init.mock.results.map((result) => result.value as ReturnType<typeof chart>)
    expect(pie.setOption).toHaveBeenCalledOnce()
    expect(bar.setOption).toHaveBeenCalledOnce()
    const pieOption = pie.setOption.mock.calls[0][0] as { series: Array<{ data: unknown }> }
    const barOption = bar.setOption.mock.calls[0][0] as { xAxis: { data: string[] } }
    expect(pieOption.series[0].data).toEqual([{ name: '成长基金', value: 60 }])
    expect(barOption.xAxis.data).toEqual(['2025-01'])

    window.dispatchEvent(new Event('resize'))
    const chartResizeObservers = resizeObserverInstances.filter((instance) => instance.element instanceof HTMLElement && instance.element.classList.contains('chart'))
    chartResizeObservers.forEach((instance) => instance.callback([], instance as unknown as ResizeObserver))
    expect(pie.resize).toHaveBeenCalledOnce()
    expect(bar.resize).toHaveBeenCalledOnce()
    wrapper.unmount()
    expect(pie.dispose).toHaveBeenCalledOnce()
    expect(bar.dispose).toHaveBeenCalledOnce()
  })
})
