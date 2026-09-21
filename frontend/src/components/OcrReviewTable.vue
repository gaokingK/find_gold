<script setup lang="ts">
import StatusTag from './StatusTag.vue'
import type { ParsedOcrRecord, ReviewAction } from '../types/domain'
import { formatCurrency, formatPercent } from '../utils/formatters'

const props = withDefaults(defineProps<{ records: ParsedOcrRecord[]; disabled?: boolean; invalidRecordIds?: string[] }>(), { invalidRecordIds: () => [] })
const emit = defineEmits<{ update: [records: ParsedOcrRecord[]] }>()
const reviewLabels = { pending: '待处理', accepted: '接受', rejected: '拒绝' } as const

function reviewLabel(action: ReviewAction): string {
  return reviewLabels[action]
}

function updateAmount(id: string, value: number | undefined): void {
  updateRecord(id, { operationAmount: value ?? 0 })
}

function updateRecord(id: string, patch: Partial<ParsedOcrRecord>): void {
  emit('update', props.records.map((record) => record.id === id ? { ...record, ...patch } : record))
}
</script>

<template>
  <div class="table-region table-scroll table-frame__body" role="region" aria-label="OCR 审核表格">
    <el-table :data="records" stripe>
      <el-table-column label="博主 / 板块" min-width="150">
        <template #default="scope"><span class="name-cell">{{ scope.row.bloggerName }}</span><span class="sub-cell">{{ scope.row.sector }}</span></template>
      </el-table-column>
      <el-table-column label="基金" prop="fundName" min-width="160" />
      <el-table-column label="操作金额" min-width="135"><template #default="scope"><div class="ocr-amount-control"><el-input-number :model-value="scope.row.operationAmount" :min="0" :precision="2" controls-position="right" :disabled="disabled || scope.row.reviewAction !== 'pending'" :aria-invalid="props.invalidRecordIds.includes(scope.row.id)" @update:model-value="(value: number | undefined) => updateAmount(scope.row.id, value)" /><span v-if="props.invalidRecordIds.includes(scope.row.id)" class="field-error" role="alert">请输入有效的非负金额</span></div></template></el-table-column>
      <el-table-column label="持有收益" min-width="120"><template #default="scope">{{ formatCurrency(scope.row.holdingProfit) }}</template></el-table-column>
      <el-table-column label="累计收益" min-width="120"><template #default="scope">{{ formatCurrency(scope.row.cumulativeProfit) }}</template></el-table-column>
      <el-table-column label="近一年" min-width="95"><template #default="scope">{{ formatPercent(scope.row.return1y) }}</template></el-table-column>
      <el-table-column label="最大回撤" min-width="100"><template #default="scope">{{ formatPercent(scope.row.maxDrawdown) }}</template></el-table-column>
      <el-table-column label="审核操作" fixed="right" min-width="180">
        <template #default="scope">
          <div class="tag-row">
            <StatusTag v-if="scope.row.suspectedDuplicate" status="duplicate" label="疑似重复" tone="warning" icon="!" />
            <el-button v-if="scope.row.reviewAction === 'pending'" size="small" type="success" plain :disabled="disabled" @click="updateRecord(scope.row.id, { reviewAction: 'accepted' })">接受</el-button>
            <el-button v-if="scope.row.reviewAction === 'pending'" size="small" type="danger" plain :disabled="disabled" @click="updateRecord(scope.row.id, { reviewAction: 'rejected' })">拒绝</el-button>
            <StatusTag v-else :status="scope.row.reviewAction" :label="reviewLabel(scope.row.reviewAction)" :tone="scope.row.reviewAction === 'accepted' ? 'positive' : 'error'" :icon="scope.row.reviewAction === 'accepted' ? '✓' : '×'" />
          </div>
          <span v-if="scope.row.suspectedDuplicate" class="duplicate-note">与已有记录疑似重复</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
