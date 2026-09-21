import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { defineComponent } from 'vue'
import PageHeader from '../../src/components/PageHeader.vue'
import SurfaceCard from '../../src/components/SurfaceCard.vue'
import FilterBar from '../../src/components/FilterBar.vue'
import TableFrame from '../../src/components/TableFrame.vue'
import StatusTag from '../../src/components/StatusTag.vue'
import FeedbackRegion from '../../src/components/FeedbackRegion.vue'
import ResponsiveDialog from '../../src/components/ResponsiveDialog.vue'

describe('shared presentation components', () => {
  it('keeps stable slots and action regions for page surfaces', () => {
    const wrapper = mount(PageHeader, { props: { title: '总览', description: '说明' }, slots: { actions: '<button>导入</button>' } })
    expect(wrapper.find('h2').text()).toBe('总览')
    expect(wrapper.find('.page-header__actions').text()).toBe('导入')

    const card = mount(SurfaceCard, { props: { heading: '列表', meta: '2 条' }, slots: { default: '内容' } })
    expect(card.find('h3').text()).toBe('列表')
    expect(card.text()).toContain('内容')
  })

  it('exposes loading, empty, feedback, and non-color status cues', () => {
    const filter = mount(FilterBar, { props: { loading: true }, slots: { default: '筛选' } })
    expect(filter.attributes('aria-busy')).toBe('true')

    const table = mount(TableFrame, { props: { title: '记录', empty: true }, slots: { empty: '暂无记录' } })
    expect(table.find('[role="status"]').text()).toContain('暂无记录')

    const status = mount(StatusTag, { props: { status: 'warning', label: '疑似重复', tone: 'warning' } })
    expect(status.text()).toContain('疑似重复')
    expect(status.find('.status-tag__mark').text()).toBe('!')

    const feedback = mount(FeedbackRegion, { props: { kind: 'error', title: '失败', description: '可重试' } })
    expect(feedback.attributes('role')).toBe('alert')
    expect(feedback.text()).toContain('可重试')
  })

  it('forwards dialog content and model updates through the stable wrapper', async () => {
    const DialogStub = defineComponent({ emits: ['update:modelValue'], template: '<div><slot /><slot name="footer" /></div>' })
    const wrapper = mount(ResponsiveDialog, { props: { modelValue: true, title: '编辑' }, slots: { default: '表单', footer: '保存' }, global: { stubs: { 'el-dialog': DialogStub } } })
    expect(wrapper.text()).toContain('表单')
    expect(wrapper.text()).toContain('保存')
    await wrapper.findComponent(DialogStub).vm.$emit('update:modelValue', false)
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([false])
  })
})
