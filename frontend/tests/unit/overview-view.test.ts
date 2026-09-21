import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import OverviewView from '../../src/views/OverviewView.vue'
import FilterBar from '../../src/components/FilterBar.vue'
import MetricCard from '../../src/components/MetricCard.vue'
import PageHeader from '../../src/components/PageHeader.vue'
import TableFrame from '../../src/components/TableFrame.vue'
import { service } from '../../src/services'
import type { BloggerSummary } from '../../src/types/domain'

const mockRouter = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock('vue-router', () => ({ useRouter: () => mockRouter }))

const blogger: BloggerSummary = {
  id: 42,
  name: '示例博主',
  sector: '科技',
  observeStartDate: '2025-01-01',
  observeDays: 30,
  status: 'active',
  returnRate: 0.12,
  profit: 1200,
  maxDrawdown: -0.03,
  operationCount: 4,
}

function mountOverview() {
  return mount(OverviewView, { global: { plugins: [ElementPlus] } })
}

describe('overview data contract', () => {
  it('sorts formal bloggers by return rate while keeping observing data separate', async () => {
    const bloggers = await service.listBloggers({ status: 'active', sortBy: 'returnRate' })
    expect(bloggers.map((blogger) => blogger.id)).toEqual([1, 3])
    expect(bloggers[0].returnRate).toBeGreaterThan(bloggers[1].returnRate ?? 0)
  })
})

describe('OverviewView composition', () => {
  beforeEach(() => {
    mockRouter.push.mockReset()
    vi.spyOn(service, 'listSectors').mockResolvedValue(['科技'])
    vi.spyOn(service, 'listBloggers').mockResolvedValue([blogger])
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the shared page structure and preserves import/detail navigation', async () => {
    const wrapper = mountOverview()
    await flushPromises()

    expect(wrapper.findComponent(PageHeader).exists()).toBe(true)
    expect(wrapper.findComponent(FilterBar).exists()).toBe(true)
    expect(wrapper.findComponent(TableFrame).exists()).toBe(true)
    expect(wrapper.findAllComponents(MetricCard)).toHaveLength(4)

    await wrapper.getComponent(PageHeader).get('button').trigger('click')
    expect(mockRouter.push).toHaveBeenCalledWith('/import')

    await wrapper.get('button.action-link').trigger('click')
    expect(mockRouter.push).toHaveBeenCalledWith('/bloggers/42')
  })

  it('keeps an empty result actionable and clears filters with the original query shape', async () => {
    const listBloggers = vi.mocked(service.listBloggers)
    listBloggers.mockResolvedValue([])
    const wrapper = mountOverview()
    await flushPromises()

    expect(wrapper.findComponent(TableFrame).text()).toContain('导入截图')
    const view = wrapper.vm as unknown as {
      filters: { keyword?: string }
      clearFilters: () => Promise<void>
    }
    view.filters.keyword = '不存在'
    await view.clearFilters()

    expect(listBloggers).toHaveBeenLastCalledWith({
      sector: 'all',
      status: 'all',
      keyword: '',
      sortBy: 'returnRate',
    })
  })
})
