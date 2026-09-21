<script setup lang="ts">
import type { Position } from '../types/domain'
import { formatCurrency, formatPercent, valueTone } from '../utils/formatters'

defineProps<{ positions: Position[] }>()
</script>

<template>
  <div class="table-region table-scroll table-frame__body" role="region" aria-label="当前持仓表格">
    <el-table :data="positions" stripe>
    <el-table-column label="基金名称" min-width="190">
      <template #default="scope"><span class="name-cell">{{ scope.row.fundName }}</span><span class="sub-cell">{{ scope.row.fundCode }}</span></template>
    </el-table-column>
    <el-table-column label="份额" prop="shares" min-width="110" />
    <el-table-column label="成本" min-width="120"><template #default="scope">{{ formatCurrency(scope.row.costBasis) }}</template></el-table-column>
    <el-table-column label="当前净值" prop="currentNav" min-width="110" />
    <el-table-column label="市值" min-width="120"><template #default="scope">{{ formatCurrency(scope.row.marketValue) }}</template></el-table-column>
    <el-table-column label="收益" min-width="120"><template #default="scope"><span :class="valueTone(scope.row.profit)">{{ formatCurrency(scope.row.profit) }}</span></template></el-table-column>
    <el-table-column label="占比" min-width="90"><template #default="scope">{{ formatPercent(scope.row.allocation) }}</template></el-table-column>
    </el-table>
  </div>
</template>
