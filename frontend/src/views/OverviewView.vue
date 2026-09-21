<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import BloggerStatusTag from '../components/BloggerStatusTag.vue'
import EmptyState from '../components/EmptyState.vue'
import FeedbackRegion from '../components/FeedbackRegion.vue'
import FilterBar from '../components/FilterBar.vue'
import MetricCard from '../components/MetricCard.vue'
import PageHeader from '../components/PageHeader.vue'
import TableFrame from '../components/TableFrame.vue'
import { service } from '../services'
import type { BloggerSummary } from '../types/domain'
import type { BloggerQuery } from '../services/types'
import { formatCurrency, formatPercent, valueTone } from '../utils/formatters'

const router = useRouter()
const bloggers = ref<BloggerSummary[]>([])
const sectors = ref<string[]>([])
const loading = ref(false)
const loadError = ref(false)
const filters = reactive<BloggerQuery>({ sector: 'all', status: 'all', keyword: '', sortBy: 'returnRate' })

const formalCount = computed(() => bloggers.value.filter((blogger) => blogger.status === 'active').length)
const observingCount = computed(() => bloggers.value.filter((blogger) => blogger.status === 'observing').length)
const averageReturn = computed(() => {
  const formal = bloggers.value.filter((blogger) => blogger.returnRate !== null)
  return formal.length ? formal.reduce((sum, blogger) => sum + (blogger.returnRate ?? 0), 0) / formal.length : null
})
const hasActiveFilters = computed(() => filters.sector !== 'all' || filters.status !== 'all' || Boolean(filters.keyword))

async function load(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    bloggers.value = await service.listBloggers(filters)
  } catch {
    bloggers.value = []
    loadError.value = true
  } finally {
    loading.value = false
  }
}

async function clearFilters(): Promise<void> {
  filters.sector = 'all'
  filters.status = 'all'
  filters.keyword = ''
  filters.sortBy = 'returnRate'
  await load()
}

function goToImport(): void {
  router.push('/import')
}

function goToBlogger(id: number): void {
  router.push(`/bloggers/${id}`)
}

onMounted(async () => {
  try {
    sectors.value = await service.listSectors()
    await load()
  } catch {
    loadError.value = true
  }
})
</script>

<template>
  <PageHeader
    title="追踪池概览"
    description="观察你关注的基金博主，及时掌握组合变化与收益表现。"
  >
    <template #actions>
      <el-button type="primary" @click="goToImport">导入截图</el-button>
    </template>
  </PageHeader>

  <section class="summary-grid" aria-label="追踪池指标">
    <MetricCard label="总博主数" :value="String(bloggers.length)" />
    <MetricCard label="正式观察" :value="String(formalCount)" tone="positive" />
    <MetricCard label="观察期中" :value="String(observingCount)" tone="muted" />
    <MetricCard label="平均收益率" :value="formatPercent(averageReturn)" :tone="valueTone(averageReturn)" />
  </section>

  <FilterBar :loading="loading" label="博主列表筛选">
    <el-form class="overview-filter-form" inline @submit.prevent="load">
      <el-form-item label="关键词">
        <el-input v-model="filters.keyword" placeholder="搜索博主名称" clearable @change="load" />
      </el-form-item>
      <el-form-item label="板块">
        <el-select v-model="filters.sector" placeholder="全部板块" @change="load">
          <el-option label="全部板块" value="all" />
          <el-option v-for="sector in sectors" :key="sector" :label="sector" :value="sector" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" @change="load">
          <el-option label="全部状态" value="all" />
          <el-option label="已达标" value="active" />
          <el-option label="观察期中" value="observing" />
          <el-option label="未开始" value="inactive" />
        </el-select>
      </el-form-item>
      <el-form-item label="排序">
        <el-select v-model="filters.sortBy" @change="load">
          <el-option label="收益率" value="returnRate" />
          <el-option label="观察天数" value="observeDays" />
          <el-option label="累计收益" value="profit" />
        </el-select>
      </el-form-item>
    </el-form>

    <template #actions>
      <el-button v-if="hasActiveFilters" @click="clearFilters">清除筛选</el-button>
      <el-button @click="load">刷新</el-button>
    </template>
  </FilterBar>

  <FeedbackRegion
    v-if="loadError"
    kind="error"
    title="博主列表加载失败"
    description="暂时无法获取追踪池数据，请重试。"
    action="重试"
    @action="load"
  />

  <TableFrame
    title="博主列表"
    :count="`共 ${bloggers.length} 位`"
    :loading="loading"
    :empty="!loading && bloggers.length === 0"
    label="博主列表"
  >
    <el-table :data="bloggers" stripe empty-text="">
      <el-table-column label="博主名称" min-width="150">
        <template #default="scope"><span class="name-cell">{{ scope.row.name }}</span></template>
      </el-table-column>
      <el-table-column label="板块" prop="sector" min-width="120" />
      <el-table-column label="观察开始日" prop="observeStartDate" min-width="130" />
      <el-table-column label="观察天数" prop="observeDays" min-width="100" />
      <el-table-column label="状态" min-width="110">
        <template #default="scope"><BloggerStatusTag :status="scope.row.status" /></template>
      </el-table-column>
      <el-table-column label="收益率" min-width="110">
        <template #default="scope"><span :class="valueTone(scope.row.returnRate)">{{ formatPercent(scope.row.returnRate) }}</span></template>
      </el-table-column>
      <el-table-column label="累计收益" min-width="130">
        <template #default="scope"><span :class="valueTone(scope.row.profit)">{{ formatCurrency(scope.row.profit) }}</span></template>
      </el-table-column>
      <el-table-column label="最大回撤" min-width="110">
        <template #default="scope"><span class="negative">{{ formatPercent(scope.row.maxDrawdown) }}</span></template>
      </el-table-column>
      <el-table-column label="操作次数" prop="operationCount" min-width="95" />
      <el-table-column label="" fixed="right" width="80">
        <template #default="scope"><button class="action-link" type="button" :aria-label="`查看 ${scope.row.name} 详情`" @click="goToBlogger(scope.row.id)">详情</button></template>
      </el-table-column>
    </el-table>

    <template #empty>
      <EmptyState>
        <div class="toolbar-actions empty-state__actions">
          <el-button v-if="hasActiveFilters" @click="clearFilters">清除筛选</el-button>
          <el-button type="primary" @click="goToImport">导入截图</el-button>
        </div>
      </EmptyState>
    </template>
  </TableFrame>
</template>
