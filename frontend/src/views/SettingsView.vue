<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import FeedbackRegion from '../components/FeedbackRegion.vue'
import PageHeader from '../components/PageHeader.vue'
import ResponsiveDialog from '../components/ResponsiveDialog.vue'
import SurfaceCard from '../components/SurfaceCard.vue'
import TableFrame from '../components/TableFrame.vue'
import { service } from '../services'
import type { BloggerSummary, FundOption, InitialPositionRecord } from '../types/domain'
import type { BloggerDraft, InitialPositionDraft } from '../services/types'
import { isNonNegativeNumber } from '../utils/validators'

const bloggers = ref<BloggerSummary[]>([])
const funds = ref<FundOption[]>([])
const positions = ref<InitialPositionRecord[]>([])
const activeTab = ref('bloggers')
const loading = ref(false)
const feedback = ref<{ kind: 'success' | 'error' | 'warning' | 'info'; title: string; description?: string } | null>(null)
const bloggerFormRef = ref<FormInstance>()
const fundFormRef = ref<FormInstance>()
const positionFormRef = ref<FormInstance>()
const bloggerDialog = ref(false)
const fundDialog = ref(false)
const positionDialog = ref(false)
const editingBloggerId = ref<number | null>(null)
const editingFundId = ref<number | null>(null)
const bloggerForm = reactive<BloggerDraft>({ name: '', sector: '', observeStartDate: '' })
const fundForm = reactive<FundOption>({ id: 0, name: '', code: '' })
const positionForm = reactive<InitialPositionDraft>({ bloggerId: 0, fundId: 0, shares: 0, costBasis: 0, recordDate: '' })

const bloggerRules: FormRules<BloggerDraft> = {
  name: [{ required: true, message: '请输入博主名称', trigger: 'blur' }],
  sector: [{ required: true, message: '请输入板块', trigger: 'blur' }],
  observeStartDate: [{ required: true, message: '请选择观察开始日', trigger: 'change' }],
}
const fundRules: FormRules<FundOption> = {
  name: [{ required: true, message: '请输入基金名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入基金代码', trigger: 'blur' }],
}
const positionRules: FormRules<InitialPositionDraft> = {
  bloggerId: [{ required: true, message: '请选择博主', trigger: 'change' }],
  fundId: [{ required: true, message: '请选择基金', trigger: 'change' }],
  recordDate: [{ required: true, message: '请选择记录日期', trigger: 'change' }],
  shares: [{ validator: (_rule, value: number, callback) => isNonNegativeNumber(value) ? callback() : callback(new Error('份额必须大于等于 0')), trigger: 'change' }],
  costBasis: [{ validator: (_rule, value: number, callback) => isNonNegativeNumber(value) ? callback() : callback(new Error('成本金额必须大于等于 0')), trigger: 'change' }],
}

function setFeedback(kind: 'success' | 'error' | 'warning' | 'info', title: string, description?: string): void {
  feedback.value = { kind, title, description }
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const [nextBloggers, nextFunds, nextPositions] = await Promise.all([
      service.listBloggers(),
      service.listFunds(),
      service.listInitialPositions(),
    ])
    bloggers.value = nextBloggers
    funds.value = nextFunds
    positions.value = nextPositions as InitialPositionRecord[]
  } catch (cause) {
    setFeedback('error', '设置数据加载失败', cause instanceof Error ? cause.message : '请重试。')
  } finally {
    loading.value = false
  }
}

function resetBlogger(): void { Object.assign(bloggerForm, { name: '', sector: '', observeStartDate: '' }); editingBloggerId.value = null }
function editBlogger(item: BloggerSummary): void { Object.assign(bloggerForm, { name: item.name, sector: item.sector, observeStartDate: item.observeStartDate }); editingBloggerId.value = item.id; bloggerDialog.value = true }
function resetFund(): void { Object.assign(fundForm, { id: 0, name: '', code: '' }); editingFundId.value = null }
function editFund(item: FundOption): void { Object.assign(fundForm, item); editingFundId.value = item.id; fundDialog.value = true }
function openNewBlogger(): void { resetBlogger(); bloggerDialog.value = true }
function openNewFund(): void { resetFund(); fundDialog.value = true }
function openNewPosition(): void { Object.assign(positionForm, { bloggerId: 0, fundId: 0, shares: 0, costBasis: 0, recordDate: '' }); positionDialog.value = true }

async function saveBlogger(): Promise<void> {
  if (!await bloggerFormRef.value?.validate().catch(() => false)) return
  try {
    if (editingBloggerId.value) await service.updateBlogger(editingBloggerId.value, bloggerForm)
    else await service.createBlogger(bloggerForm)
    bloggerDialog.value = false
    setFeedback('success', '博主保存成功', '列表已更新。')
    ElMessage.success('博主保存成功')
    await load()
  } catch (cause) {
    setFeedback('error', '博主保存失败', cause instanceof Error ? cause.message : '请检查表单后重试。')
  }
}

async function deleteBlogger(item: BloggerSummary): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除博主“${item.name}”吗？`, '删除博主', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch { return }
  try {
    await service.deleteBlogger(item.id)
    setFeedback('success', '博主已删除', `${item.name} 已从追踪池移除。`)
    ElMessage.success('博主已删除')
    await load()
  } catch (cause) {
    setFeedback('error', '博主删除失败', cause instanceof Error ? cause.message : '请重试。')
  }
}

async function saveFund(): Promise<void> {
  if (!await fundFormRef.value?.validate().catch(() => false)) return
  try {
    if (editingFundId.value) await service.updateFund(editingFundId.value, fundForm)
    else await service.createFund(fundForm)
    fundDialog.value = false
    setFeedback('success', '基金保存成功', '列表已更新。')
    ElMessage.success('基金保存成功')
    await load()
  } catch (cause) {
    setFeedback('error', '基金保存失败', cause instanceof Error ? cause.message : '请检查表单后重试。')
  }
}

async function savePosition(): Promise<void> {
  if (!await positionFormRef.value?.validate().catch(() => false)) return
  try {
    await service.createInitialPosition(positionForm)
    positionDialog.value = false
    setFeedback('success', '初始持仓保存成功', '列表已更新。')
    ElMessage.success('初始持仓保存成功')
    await load()
  } catch (cause) {
    setFeedback('error', '初始持仓保存失败', cause instanceof Error ? cause.message : '请检查表单后重试。')
  }
}

onMounted(load)
</script>

<template>
  <PageHeader title="基础设置" description="管理 Demo 中的博主、基金和初始持仓数据。" />
  <FeedbackRegion v-if="feedback" :kind="feedback.kind" :title="feedback.title" :description="feedback.description" class="settings-feedback" />

  <SurfaceCard class="settings-card">
    <el-tabs v-model="activeTab" aria-label="基础设置类型">
      <el-tab-pane label="博主管理" name="bloggers">
        <TableFrame title="博主列表" :count="`共 ${bloggers.length} 位`" :loading="loading" :empty="!loading && bloggers.length === 0" label="博主管理列表">
          <template #actions><el-button type="primary" aria-label="新增博主" @click="openNewBlogger">新增博主</el-button></template>
          <template #empty><span class="state-mark" aria-hidden="true">—</span><span>暂无博主数据。</span><el-button type="primary" @click="openNewBlogger">新增博主</el-button></template>
          <el-table :data="bloggers" stripe aria-label="博主管理表格">
            <el-table-column label="名称" prop="name" min-width="160" />
            <el-table-column label="板块" prop="sector" min-width="120" />
            <el-table-column label="观察开始日" prop="observeStartDate" min-width="130" />
            <el-table-column label="操作" width="170" fixed="right">
              <template #default="scope"><div class="table-actions"><el-button link type="primary" @click="editBlogger(scope.row)">编辑</el-button><el-button link type="danger" @click="deleteBlogger(scope.row)">删除</el-button></div></template>
            </el-table-column>
          </el-table>
        </TableFrame>
      </el-tab-pane>

      <el-tab-pane label="基金管理" name="funds">
        <TableFrame title="基金列表" :count="`共 ${funds.length} 只`" :loading="loading" :empty="!loading && funds.length === 0" label="基金管理列表">
          <template #actions><el-button type="primary" aria-label="新增基金" @click="openNewFund">新增基金</el-button></template>
          <template #empty><span class="state-mark" aria-hidden="true">—</span><span>暂无基金数据。</span><el-button type="primary" @click="openNewFund">新增基金</el-button></template>
          <el-table :data="funds" stripe aria-label="基金管理表格">
            <el-table-column label="基金名称" prop="name" min-width="200" />
            <el-table-column label="基金代码" prop="code" min-width="130" />
            <el-table-column label="操作" width="100" fixed="right"><template #default="scope"><el-button link type="primary" @click="editFund(scope.row)">编辑</el-button></template></el-table-column>
          </el-table>
        </TableFrame>
      </el-tab-pane>

      <el-tab-pane label="初始持仓" name="positions">
        <TableFrame title="初始持仓" :count="`共 ${positions.length} 条`" :loading="loading" :empty="!loading && positions.length === 0" label="初始持仓列表">
          <template #actions><el-button type="primary" aria-label="新增初始持仓" @click="openNewPosition">新增持仓</el-button></template>
          <template #empty><span class="state-mark" aria-hidden="true">—</span><span>暂无初始持仓数据。</span><el-button type="primary" @click="openNewPosition">新增持仓</el-button></template>
          <el-table :data="positions" stripe aria-label="初始持仓表格">
            <el-table-column label="博主" prop="bloggerName" min-width="160" />
            <el-table-column label="基金" prop="fundName" min-width="200" />
            <el-table-column label="份额" prop="shares" min-width="100" />
            <el-table-column label="成本金额" prop="costBasis" min-width="120" />
            <el-table-column label="记录日期" prop="recordDate" min-width="130" />
          </el-table>
        </TableFrame>
      </el-tab-pane>
    </el-tabs>
  </SurfaceCard>

  <ResponsiveDialog v-model="bloggerDialog" :title="editingBloggerId ? '编辑博主' : '新增博主'" aria-label="博主编辑对话框">
    <el-form ref="bloggerFormRef" :model="bloggerForm" :rules="bloggerRules" label-position="top" @submit.prevent="saveBlogger">
      <el-form-item label="博主名称" prop="name"><el-input v-model="bloggerForm.name" /></el-form-item>
      <el-form-item label="板块" prop="sector"><el-input v-model="bloggerForm.sector" /></el-form-item>
      <el-form-item label="观察开始日" prop="observeStartDate"><el-date-picker v-model="bloggerForm.observeStartDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
    </el-form>
    <template #footer><div class="dialog-actions"><el-button @click="bloggerDialog = false">取消</el-button><el-button type="primary" @click="saveBlogger">保存</el-button></div></template>
  </ResponsiveDialog>

  <ResponsiveDialog v-model="fundDialog" :title="editingFundId ? '编辑基金' : '新增基金'" aria-label="基金编辑对话框">
    <el-form ref="fundFormRef" :model="fundForm" :rules="fundRules" label-position="top" @submit.prevent="saveFund">
      <el-form-item label="基金名称" prop="name"><el-input v-model="fundForm.name" /></el-form-item>
      <el-form-item label="基金代码" prop="code"><el-input v-model="fundForm.code" /></el-form-item>
    </el-form>
    <template #footer><div class="dialog-actions"><el-button @click="fundDialog = false">取消</el-button><el-button type="primary" @click="saveFund">保存</el-button></div></template>
  </ResponsiveDialog>

  <ResponsiveDialog v-model="positionDialog" title="新增初始持仓" aria-label="初始持仓编辑对话框">
    <el-form ref="positionFormRef" :model="positionForm" :rules="positionRules" label-position="top" @submit.prevent="savePosition">
      <el-form-item label="博主" prop="bloggerId"><el-select v-model="positionForm.bloggerId" style="width: 100%"><el-option v-for="item in bloggers" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
      <el-form-item label="基金" prop="fundId"><el-select v-model="positionForm.fundId" style="width: 100%"><el-option v-for="item in funds" :key="item.id" :label="`${item.name}（${item.code}）`" :value="item.id" /></el-select></el-form-item>
      <el-form-item label="份额" prop="shares"><el-input-number v-model="positionForm.shares" :min="0" :precision="2" style="width: 100%" /></el-form-item>
      <el-form-item label="成本金额" prop="costBasis"><el-input-number v-model="positionForm.costBasis" :min="0" :precision="2" style="width: 100%" /></el-form-item>
      <el-form-item label="记录日期" prop="recordDate"><el-date-picker v-model="positionForm.recordDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
    </el-form>
    <template #footer><div class="dialog-actions"><el-button @click="positionDialog = false">取消</el-button><el-button type="primary" @click="savePosition">保存</el-button></div></template>
  </ResponsiveDialog>
</template>

<style scoped>
.settings-feedback { margin-bottom: var(--space-6); }
.settings-card { padding: var(--space-4) var(--space-5) var(--space-5); }
.table-actions, .dialog-actions { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: var(--space-2); }
.settings-card :deep(.el-tabs__header) { margin-bottom: var(--space-5); }
.settings-card :deep(.table-frame) { box-shadow: none; }
.settings-card :deep(.table-frame__heading) { padding-right: var(--space-4); padding-left: var(--space-4); }
@media (max-width: 720px) {
  .settings-card { padding: var(--space-2) var(--space-3) var(--space-3); }
  .settings-card :deep(.el-tabs__nav-wrap) { overflow-x: auto; }
  .settings-card :deep(.table-frame__heading) { padding-right: var(--space-3); padding-left: var(--space-3); }
  .table-actions, .dialog-actions { justify-content: flex-start; }
}
</style>
