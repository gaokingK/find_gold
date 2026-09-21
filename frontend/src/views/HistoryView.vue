<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import FeedbackRegion from '../components/FeedbackRegion.vue'
import FilterBar from '../components/FilterBar.vue'
import PageHeader from '../components/PageHeader.vue'
import ResponsiveDialog from '../components/ResponsiveDialog.vue'
import TableFrame from '../components/TableFrame.vue'
import { service } from '../services'
import type { ParsedOcrRecord, ScreenshotImportResult } from '../types/domain'
import { todayString } from '../utils/upload'

interface HistoryStateSnapshot {
  scrollTop: number
  selectedDate: string
  items: ScreenshotImportResult[]
}

const router = useRouter()
const selectedDate = ref('')
const items = ref<ScreenshotImportResult[]>([])
const loading = ref(false)
const loadError = ref(false)
const drawerVisible = ref(false)
const selected = ref<ScreenshotImportResult | null>(null)
const stateSnapshot = ref<HistoryStateSnapshot | null>(null)

function cloneItems(history: ScreenshotImportResult[]): ScreenshotImportResult[] {
  return history.map((item) => ({
    ...item,
    records: item.records.map((record) => ({ ...record })),
  }))
}

function contentArea(): HTMLElement | null {
  return document.getElementById('main-content')
}

async function load(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    items.value = await service.listHistory(selectedDate.value || undefined)
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function snapshotBackgroundState(): void {
  stateSnapshot.value = {
    scrollTop: contentArea()?.scrollTop ?? 0,
    selectedDate: selectedDate.value,
    items: cloneItems(items.value),
  }
}

function openDetail(item: ScreenshotImportResult): void {
  snapshotBackgroundState()
  selected.value = item
  drawerVisible.value = true
}

async function restoreBackgroundState(): Promise<void> {
  const snapshot = stateSnapshot.value
  stateSnapshot.value = null
  if (!snapshot) return

  const area = contentArea()
  if (!area) return
  try {
    area.scrollTop = snapshot.scrollTop
  } catch {
    return
  }
  if (area.scrollTop !== snapshot.scrollTop) return

  await nextTick()
  selectedDate.value = snapshot.selectedDate
  items.value = snapshot.items
}

function confirmedCount(records: ParsedOcrRecord[]): number {
  return records.filter((record) => record.reviewAction !== 'pending').length
}

onMounted(async () => {
  selectedDate.value = ''
  await load()
})
</script>

<template>
  <PageHeader title="历史记录" description="查看截图导入批次、识别原文和人工审核结果。">
    <template #actions>
      <el-button type="primary" aria-label="新建截图导入" @click="router.push('/import')">新建导入</el-button>
    </template>
  </PageHeader>

  <FilterBar :loading="loading" label="历史记录筛选">
    <el-form inline aria-label="历史记录筛选表单" @submit.prevent="load">
      <el-form-item label="操作日期">
        <el-date-picker
          v-model="selectedDate"
          type="date"
          value-format="YYYY-MM-DD"
          :placeholder="`最近操作日期（${todayString()}）`"
          clearable
          aria-label="操作日期"
        />
      </el-form-item>
    </el-form>
    <template #actions>
      <el-button type="primary" :loading="loading" aria-label="查询历史记录" @click="load">查询</el-button>
    </template>
  </FilterBar>

  <FeedbackRegion
    v-if="loadError"
    kind="error"
    title="历史记录加载失败"
    description="暂时无法获取导入批次，请重试。"
    action="重试"
    @action="load"
  />

  <TableFrame
    title="导入批次"
    :count="`共 ${items.length} 批`"
    :loading="loading"
    :empty="!loading && items.length === 0"
    label="导入批次列表"
  >
    <template #empty>
      <span class="state-mark" aria-hidden="true">—</span>
      <span>暂无历史记录，可先新建导入。</span>
      <el-button type="primary" aria-label="从空历史记录创建新导入" @click="router.push('/import')">新建导入</el-button>
    </template>
    <el-table :data="items" stripe aria-label="导入批次表格">
      <el-table-column label="截图文件名" min-width="220">
        <template #default="scope">
          <span class="name-cell">{{ scope.row.fileName }}</span>
          <span class="sub-cell">Demo 未保存图片预览</span>
        </template>
      </el-table-column>
      <el-table-column label="操作日期" prop="operationDate" min-width="130" />
      <el-table-column label="识别状态" min-width="110">
        <template #default><el-tag type="success" effect="plain">识别完成</el-tag></template>
      </el-table-column>
      <el-table-column label="记录数量" min-width="100"><template #default="scope">{{ scope.row.records.length }}</template></el-table-column>
      <el-table-column label="确认数量" min-width="100"><template #default="scope">{{ confirmedCount(scope.row.records) }}</template></el-table-column>
      <el-table-column label="操作" fixed="right" width="110">
        <template #default="scope">
          <button class="action-link" type="button" :aria-label="`查看 ${scope.row.fileName} 详情`" @click="openDetail(scope.row)">查看详情</button>
        </template>
      </el-table-column>
    </el-table>
  </TableFrame>

  <ResponsiveDialog
    v-model="drawerVisible"
    title="导入详情"
    variant="drawer"
    size="min(620px, calc(100vw - 32px))"
    class="history-drawer"
    :show-close="false"
    :destroy-on-close="false"
    aria-label="导入详情"
    aria-labelledby="history-drawer-title"
    @closed="restoreBackgroundState"
  >
    <template #header>
      <div class="history-drawer__header">
        <h2 id="history-drawer-title">导入详情</h2>
        <button class="history-drawer__close" type="button" aria-label="关闭导入详情" @click="drawerVisible = false">×</button>
      </div>
    </template>
    <div v-if="selected" class="history-detail">
      <div class="drawer-preview" aria-label="导入文件预览">
        {{ selected.fileName }}<br />Demo 未保存图片预览
      </div>
      <section aria-labelledby="history-raw-text-title">
        <h3 id="history-raw-text-title" class="chart-title">OCR 原文</h3>
        <pre class="raw-text" aria-label="原始 OCR 文本">{{ selected.rawText }}</pre>
      </section>
      <TableFrame title="结构化记录" :count="`${selected.records.length} 条`" label="结构化记录表">
        <el-table :data="selected.records" size="small" aria-label="结构化 OCR 记录表">
          <el-table-column label="博主" prop="bloggerName" />
          <el-table-column label="基金" prop="fundName" />
          <el-table-column label="金额" prop="operationAmount" />
          <el-table-column label="审核状态" min-width="90">
            <template #default="scope">
              <el-tag :type="scope.row.reviewAction === 'accepted' ? 'success' : scope.row.reviewAction === 'rejected' ? 'danger' : 'info'" effect="plain">
                {{ scope.row.reviewAction === 'accepted' ? '接受' : scope.row.reviewAction === 'rejected' ? '拒绝' : '待处理' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </TableFrame>
    </div>
  </ResponsiveDialog>
</template>

<style scoped>
.history-drawer__header {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.history-drawer__header h2 {
  min-width: 0;
  margin: 0;
  color: var(--ink);
  font-size: var(--text-lg);
  line-height: 1.4;
}

.history-drawer__close {
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--muted);
  background: transparent;
  font-size: 24px;
  line-height: 1;
}

.history-drawer__close:hover {
  color: var(--ink);
  background: var(--el-fill-color-light);
}

.history-detail {
  min-width: 0;
}

.history-detail :deep(.el-table) {
  min-width: 480px;
}

@media (max-width: 720px) {
  .history-drawer {
    width: min(620px, calc(100vw - 32px)) !important;
  }

  .history-drawer :deep(.el-drawer__body) {
    min-width: 0;
    overflow-y: auto;
  }
}
</style>
