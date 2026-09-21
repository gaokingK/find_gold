<script setup lang="ts">
import StatusTag from './StatusTag.vue'
import type { Operation, ReviewAction } from '../types/domain'
import { formatCurrency } from '../utils/formatters'

defineProps<{ operations: Operation[] }>()
const reviewLabels = { pending: '待审核', accepted: '已接受', rejected: '已拒绝' } as const

function reviewLabel(action: ReviewAction): string {
  return reviewLabels[action]
}
</script>

<template>
  <div class="table-region table-scroll table-frame__body" role="region" aria-label="操作历史表格">
    <el-table :data="operations" stripe>
      <el-table-column label="日期" prop="operationDate" min-width="120" />
      <el-table-column label="基金名称" prop="fundName" min-width="180" />
      <el-table-column label="买卖类型" min-width="100"><template #default="scope"><StatusTag :status="scope.row.operationType" :label="scope.row.operationType === 'buy' ? '买入' : '卖出'" :tone="scope.row.operationType === 'buy' ? 'positive' : 'warning'" :icon="scope.row.operationType === 'buy' ? '＋' : '－'" /></template></el-table-column>
      <el-table-column label="金额" min-width="120"><template #default="scope">{{ formatCurrency(scope.row.amount) }}</template></el-table-column>
      <el-table-column label="份额" prop="shares" min-width="100" />
      <el-table-column label="来源截图" min-width="110"><template #default="scope">{{ scope.row.screenshotId ? `#${scope.row.screenshotId}` : '--' }}</template></el-table-column>
      <el-table-column label="审核状态" min-width="100"><template #default="scope"><StatusTag :status="scope.row.reviewAction" :label="reviewLabel(scope.row.reviewAction)" :tone="scope.row.reviewAction === 'accepted' ? 'positive' : scope.row.reviewAction === 'rejected' ? 'error' : 'muted'" :icon="scope.row.reviewAction === 'accepted' ? '✓' : scope.row.reviewAction === 'rejected' ? '×' : '…'" /></template></el-table-column>
    </el-table>
  </div>
</template>
