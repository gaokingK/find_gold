import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus, { ElMessageBox } from 'element-plus'
import { describe, expect, it, vi } from 'vitest'
import OcrReviewTable from '../../src/components/OcrReviewTable.vue'
import ImportView from '../../src/views/ImportView.vue'
import { service } from '../../src/services'
import type { ScreenshotImportResult } from '../../src/types/domain'
import { isFiniteAmount } from '../../src/utils/validators'
import { todayString, validateScreenshotFile } from '../../src/utils/upload'

const result: ScreenshotImportResult = {
  screenshotId: 101,
  fileName: 'operations.png',
  operationDate: '2025-03-08',
  rawText: 'mock OCR text',
  records: [
    { id: '101-1', bloggerName: '基金小星', sector: '成长股', fundName: '华夏成长混合', operationAmount: 5000, holdingProfit: 2160, cumulativeProfit: 5674, return1y: 0.15, return3y: null, maxDrawdown: -0.08, suspectedDuplicate: false, reviewAction: 'pending' },
    { id: '101-2', bloggerName: '慢慢变富', sector: '稳健配置', fundName: '中欧医疗健康混合', operationAmount: 2500, holdingProfit: -270, cumulativeProfit: null, return1y: null, return3y: null, maxDrawdown: null, suspectedDuplicate: true, reviewAction: 'pending' },
  ],
}

function mountImport() {
  return mount(ImportView, { global: { plugins: [ElementPlus] } })
}

describe('import flow validation', () => {
  it('accepts supported image files and rejects invalid files', () => {
    expect(validateScreenshotFile(new File(['x'], 'a.png', { type: 'image/png' }))).toBeNull()
    expect(validateScreenshotFile(new File(['x'], 'a.pdf', { type: 'application/pdf' }))).toContain('仅支持')
  })
  it('requires a finite non-negative amount', () => {
    expect(isFiniteAmount(200)).toBe(true)
    expect(isFiniteAmount(Number.NaN)).toBe(false)
    expect(isFiniteAmount(-1)).toBe(false)
  })
})

describe('ImportView composition and review flow', () => {
  it('renders shared cards and keeps successful OCR, duplicate, and pending states visible', async () => {
    vi.spyOn(service, 'recognizeScreenshot').mockResolvedValue(result)
    const wrapper = mountImport()
    const view = wrapper.vm as unknown as { handleFiles: (files: File[]) => Promise<void> }

    await view.handleFiles([new File(['image'], result.fileName, { type: 'image/png' })])
    await flushPromises()

    expect(wrapper.text()).toContain('创建导入批次')
    expect(wrapper.text()).toContain('OCR 审核结果')
    expect(wrapper.text()).toContain('识别完成')
    expect(wrapper.text()).toContain('待处理记录')
    expect(wrapper.text()).toContain('疑似重复风险')
    expect(wrapper.findComponent(OcrReviewTable).exists()).toBe(true)
    const operationDate = todayString()
    expect(service.recognizeScreenshot).toHaveBeenCalledWith(expect.any(File), operationDate)
  })

  it('shows date and local file errors, and keeps recognition failure in a fixed status row', async () => {
    const recognize = vi.spyOn(service, 'recognizeScreenshot')
    const wrapper = mountImport()
    const view = wrapper.vm as unknown as { handleFiles: (files: File[]) => Promise<void>; handleDateChange: (value: string | null) => void }

    view.handleDateChange(null)
    await view.handleFiles([new File(['image'], 'missing-date.png', { type: 'image/png' })])
    await flushPromises()
    expect(wrapper.text()).toContain('请先选择操作日期')
    expect(recognize).not.toHaveBeenCalled()

    view.handleDateChange('2025-03-08')
    recognize.mockRejectedValueOnce(new Error('OCR 服务不可用'))
    await view.handleFiles([new File(['image'], 'broken.png', { type: 'image/png' })])
    await flushPromises()
    expect(wrapper.text()).toContain('识别失败')
    expect(wrapper.text()).toContain('OCR 服务不可用')

    await view.handleFiles([new File(['pdf'], 'wrong.pdf', { type: 'application/pdf' })])
    expect(wrapper.text()).toContain('文件未添加')
    expect(wrapper.text()).toContain('仅支持 PNG、JPG、JPEG 图片')
  })

  it('updates OCR review actions and preserves records when pending confirmation is cancelled', async () => {
    vi.spyOn(service, 'recognizeScreenshot').mockResolvedValue(result)
    const confirmRecords = vi.spyOn(service, 'confirmOcrRecords')
    vi.spyOn(ElMessageBox, 'confirm').mockRejectedValueOnce(new Error('cancelled'))
    const wrapper = mountImport()
    const view = wrapper.vm as unknown as { handleFiles: (files: File[]) => Promise<void>; confirmBatch: () => Promise<void> }

    await view.handleFiles([new File(['image'], result.fileName, { type: 'image/png' })])
    await flushPromises()
    const table = wrapper.findComponent(OcrReviewTable)
    const acceptButton = table.findAll('button').find((button) => button.text().includes('接受'))
    expect(acceptButton).toBeDefined()
    await acceptButton!.trigger('click')
    expect(wrapper.text()).toContain('接受')

    await view.confirmBatch()
    expect(confirmRecords).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('待处理记录')
  })
})
