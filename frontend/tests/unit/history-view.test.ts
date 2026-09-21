import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import FeedbackRegion from '../../src/components/FeedbackRegion.vue'
import FilterBar from '../../src/components/FilterBar.vue'
import PageHeader from '../../src/components/PageHeader.vue'
import TableFrame from '../../src/components/TableFrame.vue'
import HistoryView from '../../src/views/HistoryView.vue'
import { service } from '../../src/services'
import type { ScreenshotImportResult } from '../../src/types/domain'

const mockRouter = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock('vue-router', () => ({ useRouter: () => mockRouter }))

const historyItem: ScreenshotImportResult = {
  screenshotId: 7,
  fileName: 'history.png',
  operationDate: '2026-07-20',
  rawText: '博主：示例博主\n金额：100',
  records: [{
    id: 'record-1', bloggerName: '示例博主', sector: '科技', fundName: '示例基金', operationAmount: 100,
    holdingProfit: null, cumulativeProfit: null, return1y: null, return3y: null, maxDrawdown: null,
    suspectedDuplicate: false, reviewAction: 'accepted',
  }],
}

function mountHistory() {
  return mount(HistoryView, { global: { plugins: [ElementPlus] } })
}

type HistoryViewModel = {
  selectedDate: string
  items: ScreenshotImportResult[]
  load: () => Promise<void>
  openDetail: (item: ScreenshotImportResult) => void
  restoreBackgroundState: () => Promise<void>
}

function historyViewModel(wrapper: ReturnType<typeof mountHistory>): HistoryViewModel {
  return wrapper.vm as unknown as HistoryViewModel
}

function addContentArea(scrollTop: number, writable = true): HTMLElement {
  const element = document.createElement('main')
  element.id = 'main-content'
  let position = scrollTop
  Object.defineProperty(element, 'scrollTop', {
    configurable: true,
    get: () => position,
    set: (value: number) => { if (writable) position = value },
  })
  document.body.appendChild(element)
  return element
}

describe('HistoryView', () => {
  beforeEach(() => {
    mockRouter.push.mockReset()
    vi.spyOn(service, 'listHistory').mockResolvedValue([historyItem])
  })

  afterEach(() => {
    vi.restoreAllMocks()
    document.getElementById('main-content')?.remove()
  })

  it('composes shared history regions and keeps the date query contract', async () => {
    const listHistory = vi.mocked(service.listHistory)
    const wrapper = mountHistory()
    await flushPromises()

    expect(wrapper.findComponent(PageHeader).exists()).toBe(true)
    expect(wrapper.findComponent(FilterBar).exists()).toBe(true)
    expect(wrapper.findComponent(TableFrame).exists()).toBe(true)
    expect(wrapper.findComponent(FeedbackRegion).exists()).toBe(false)

    const view = historyViewModel(wrapper)
    view.selectedDate = '2026-07-20'
    await view.load()
    expect(listHistory).toHaveBeenLastCalledWith('2026-07-20')
  })

  it('keeps an empty result actionable with a new-import route', async () => {
    vi.mocked(service.listHistory).mockResolvedValue([])
    const wrapper = mountHistory()
    await flushPromises()

    expect(wrapper.findComponent(TableFrame).text()).toContain('暂无历史记录')
    await wrapper.findComponent(TableFrame).get('button').trigger('click')
    expect(mockRouter.push).toHaveBeenCalledWith('/import')
  })

  it('restores query and list state only after scroll restoration succeeds', async () => {
    const area = addContentArea(120)
    const wrapper = mountHistory()
    await flushPromises()

    const view = historyViewModel(wrapper)
    view.selectedDate = '2026-07-20'
    view.items = [historyItem]
    view.openDetail(historyItem)
    area.scrollTop = 10
    view.selectedDate = ''
    view.items = []

    await view.restoreBackgroundState()
    expect(area.scrollTop).toBe(120)
    expect(view.selectedDate).toBe('2026-07-20')
    expect(view.items).toHaveLength(1)
  })

  it('does not restore any grouped state when scroll restoration fails', async () => {
    const area = addContentArea(120, false)
    const wrapper = mountHistory()
    await flushPromises()

    const view = historyViewModel(wrapper)
    view.selectedDate = '2026-07-20'
    view.items = [historyItem]
    view.openDetail(historyItem)
    Object.defineProperty(area, 'scrollTop', { configurable: true, get: () => 10, set: () => undefined })
    view.selectedDate = ''
    view.items = []

    await view.restoreBackgroundState()
    expect(area.scrollTop).toBe(10)
    expect(view.selectedDate).toBe('')
    expect(view.items).toHaveLength(0)
  })
})
