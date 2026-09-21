import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AppShell from '../../src/components/AppShell.vue'

const mocks = vi.hoisted(() => ({
  route: { path: '/' },
  push: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ push: mocks.push }),
}))

describe('AppShell', () => {
  beforeEach(() => {
    mocks.route.path = '/'
    mocks.push.mockReset()
  })

  it('renders presentation navigation and maps blogger details to overview', () => {
    mocks.route.path = '/bloggers/42'
    const wrapper = mount(AppShell, { slots: { default: '<p>detail</p>' } })
    const navItems = wrapper.findAll('.nav-item')

    expect(navItems).toHaveLength(4)
    expect(navItems[0].attributes('aria-current')).toBe('page')
    expect(navItems[1].attributes('aria-current')).toBeUndefined()
    expect(wrapper.get('.eyebrow').text()).toBe('FUND TRACKER / BLOGGER')
    expect(wrapper.get('h1').text()).toBe('博主详情')
    expect(wrapper.get('.brand-block').text()).toContain('Fund Lens')
    expect(wrapper.get('.brand-block').text()).toContain('博主追踪台')
    expect(wrapper.get('.sidebar-footer').text()).toContain('本地 Demo 模式')
    expect(wrapper.get('main').attributes('class')).toContain('content-area')
  })

  it('keeps accessible navigation names and pushes the selected route', async () => {
    const wrapper = mount(AppShell)
    const importButton = wrapper.findAll('.nav-item')[1]

    expect(importButton.attributes('aria-label')).toBe('前往截图导入')
    expect(importButton.attributes('title')).toBe('截图导入')
    await importButton.trigger('click')

    expect(mocks.push).toHaveBeenCalledWith('/import')
  })
})
