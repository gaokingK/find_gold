<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import FeedbackRegion from '../components/FeedbackRegion.vue'
import OcrReviewTable from '../components/OcrReviewTable.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import SurfaceCard from '../components/SurfaceCard.vue'
import { service } from '../services'
import type { ParsedOcrRecord, ScreenshotImportResult } from '../types/domain'
import type { FeedbackKind } from '../types/presentation'
import { isFiniteAmount } from '../utils/validators'
import { todayString, validateScreenshotFile } from '../utils/upload'

interface ImportItem {
  fileName: string
  status: 'processing' | 'success' | 'error'
  result?: ScreenshotImportResult
  error?: string
}

const operationDate = ref<string | null>(todayString())
const dateError = ref('')
const uploadError = ref('')
const files = ref<ImportItem[]>([])
const activeResult = ref<ScreenshotImportResult | null>(null)
const records = ref<ParsedOcrRecord[]>([])
const confirming = ref(false)
const feedbackKind = ref<FeedbackKind>('info')
const feedbackTitle = ref('准备导入')
const feedbackDescription = ref('先选择操作日期和截图，识别结果会保留在当前页面供复核。')

const hasFiles = computed(() => files.value.length > 0)
const hasInvalidAmount = computed(() => records.value.some((record) => !isFiniteAmount(record.operationAmount)))
const invalidRecordIds = computed(() => records.value.filter((record) => !isFiniteAmount(record.operationAmount)).map((record) => record.id))
const hasPending = computed(() => records.value.some((record) => record.reviewAction === 'pending'))
const hasDuplicate = computed(() => records.value.some((record) => record.suspectedDuplicate))
const canConfirm = computed(() => Boolean(operationDate.value) && hasFiles.value && Boolean(activeResult.value) && !hasInvalidAmount.value && !confirming.value)

function setFeedback(kind: FeedbackKind, title: string, description?: string): void {
  feedbackKind.value = kind
  feedbackTitle.value = title
  feedbackDescription.value = description ?? ''
}

function handleDateChange(value: string | null): void {
  operationDate.value = value
  dateError.value = value ? '' : '请选择操作日期'
  if (value) uploadError.value = ''
}

async function handleFiles(fileList: File[]): Promise<void> {
  if (!operationDate.value) {
    dateError.value = '请选择操作日期'
    setFeedback('error', '无法开始识别', '请先选择操作日期。')
    ElMessage.error('请先选择操作日期')
    return
  }

  dateError.value = ''
  for (const file of fileList) {
    const validationError = validateScreenshotFile(file)
    if (validationError) {
      uploadError.value = `${file.name}：${validationError}`
      setFeedback('error', '文件未添加', uploadError.value)
      ElMessage.error(uploadError.value)
      continue
    }

    uploadError.value = ''
    const item: ImportItem = { fileName: file.name, status: 'processing' }
    files.value.push(item)
    setFeedback('info', '正在识别截图', `${file.name} 正在处理，请稍候。`)
    try {
      item.result = await service.recognizeScreenshot(file, operationDate.value)
      item.status = 'success'
      activeResult.value = item.result
      records.value = item.result.records.map((record) => ({ ...record }))
      setFeedback('success', '截图识别完成', `${file.name} 已生成 ${item.result.records.length} 条待审核记录。`)
    } catch (cause) {
      item.status = 'error'
      item.error = cause instanceof Error ? cause.message : '识别失败'
      setFeedback('error', '截图识别失败', `${file.name}：${item.error}`)
    }
  }
}

function onUploadChange(uploadFile: { raw?: File }): void {
  if (uploadFile.raw) void handleFiles([uploadFile.raw])
}

function updateRecords(nextRecords: ParsedOcrRecord[]): void {
  records.value = nextRecords
}

async function confirmBatch(): Promise<void> {
  if (!canConfirm.value || !activeResult.value) return
  if (hasPending.value) {
    try {
      await ElMessageBox.confirm('仍有记录未选择接受或拒绝，确认后将按当前状态提交吗？', '确认批次', { type: 'warning', confirmButtonText: '继续确认', cancelButtonText: '返回处理' })
    } catch {
      return
    }
  }
  confirming.value = true
  setFeedback('info', '正在确认批次', '记录正在提交，请勿重复操作。')
  try {
    const result = await service.confirmOcrRecords(activeResult.value.screenshotId, records.value)
    records.value = records.value.map((record) => record.reviewAction === 'pending' ? { ...record, reviewAction: 'rejected' } : record)
    setFeedback('success', '批次确认成功', `本批已确认：接受 ${result.accepted} 条，拒绝 ${result.rejected} 条。`)
    ElMessage.success(`本批已确认：接受 ${result.accepted} 条，拒绝 ${result.rejected} 条`)
  } catch (cause) {
    const message = cause instanceof Error ? cause.message : '确认失败'
    setFeedback('error', '批次确认失败', message)
    ElMessage.error(message)
  } finally {
    confirming.value = false
  }
}
</script>

<template>
  <PageHeader title="截图导入" description="上传博主操作截图，使用本地 mock OCR 结果完成人工确认。" />

  <div class="import-layout import-page-layout">
    <SurfaceCard class="upload-panel import-upload-card">
      <template #heading>
        <div>
          <h3>创建导入批次</h3>
          <span class="muted-text">先设定日期，再添加一张或多张截图</span>
        </div>
      </template>
      <div class="import-card-copy">Demo 不会上传图片到服务器，只使用文件名和操作日期生成固定识别结果。</div>
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="操作日期" required :error="dateError || undefined">
          <el-date-picker
            :model-value="operationDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            clearable
            style="width: 100%"
            :aria-invalid="Boolean(dateError)"
            @update:model-value="handleDateChange"
          />
          <div v-if="dateError" class="field-error" role="alert">{{ dateError }}</div>
        </el-form-item>
        <el-form-item label="截图文件" required :error="uploadError || undefined">
          <el-upload drag multiple :auto-upload="false" accept=".png,.jpg,.jpeg" :show-file-list="false" :on-change="onUploadChange">
            <div class="upload-drop">
              <div class="upload-icon" aria-hidden="true">⇧</div>
              <strong>点击或拖拽图片到这里</strong>
              <small>支持 PNG / JPG / JPEG，单个不超过 10MB</small>
            </div>
          </el-upload>
          <div v-if="uploadError" class="field-error" role="alert">{{ uploadError }}</div>
        </el-form-item>

        <div class="import-file-list" aria-label="截图识别状态" aria-live="polite">
          <div v-if="!files.length" class="import-file-empty">尚未添加截图</div>
          <div v-for="file in files" :key="file.fileName" class="ocr-file import-file-row" :class="`import-file-row--${file.status}`">
            <div class="import-file-copy">
              <span class="state-mark import-file-mark" aria-hidden="true">{{ file.status === 'success' ? '✓' : file.status === 'error' ? '!' : '…' }}</span>
              <div class="import-file-text">
                <strong>{{ file.fileName }}</strong>
                <small>{{ file.status === 'success' ? '识别完成，可在右侧审核结果中处理' : file.status === 'error' ? '识别失败，请检查文件后重试' : '待识别，正在处理截图' }}</small>
                <span v-if="file.error" class="field-error">{{ file.error }}</span>
              </div>
            </div>
            <StatusTag
              :status="file.status"
              :label="file.status === 'success' ? '识别完成' : file.status === 'error' ? '识别失败' : '待识别'"
              :tone="file.status === 'success' ? 'positive' : file.status === 'error' ? 'error' : 'muted'"
              :icon="file.status === 'success' ? '✓' : file.status === 'error' ? '!' : '…'"
            />
          </div>
        </div>

        <el-button class="import-confirm-button" type="primary" :disabled="!canConfirm" :loading="confirming" @click="confirmBatch">确认本批记录</el-button>
      </el-form>
    </SurfaceCard>

    <SurfaceCard class="table-card ocr-result-card">
      <template #heading>
        <div>
          <h3>OCR 审核结果</h3>
          <span class="muted-text">{{ records.length ? `共 ${records.length} 条，请逐条确认金额和审核操作` : '等待选择截图' }}</span>
        </div>
        <div class="tag-row import-risk-summary">
          <StatusTag v-if="hasPending" status="pending" label="待处理记录" tone="warning" icon="!" />
          <StatusTag v-if="hasDuplicate" status="duplicate" label="疑似重复风险" tone="warning" icon="!" />
        </div>
      </template>
      <div v-if="records.length" class="ocr-review-region">
        <OcrReviewTable :records="records" :invalid-record-ids="invalidRecordIds" @update="updateRecords" />
      </div>
      <div v-else class="ocr-empty-state" role="status">
        <span class="state-mark" aria-hidden="true">—</span>
        <strong>等待 OCR 结果</strong>
        <span>选择 PNG、JPG 或 JPEG 截图后，这里会显示待审核记录。</span>
      </div>
    </SurfaceCard>
  </div>

  <div class="import-feedback-slot">
    <FeedbackRegion :kind="feedbackKind" :title="feedbackTitle" :description="feedbackDescription" />
  </div>
</template>
