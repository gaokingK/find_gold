<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import BloggerStatusTag from '../components/BloggerStatusTag.vue'
import FeedbackRegion from '../components/FeedbackRegion.vue'
import MetricCard from '../components/MetricCard.vue'
import OperationTable from '../components/OperationTable.vue'
import PageHeader from '../components/PageHeader.vue'
import PositionTable from '../components/PositionTable.vue'
import SurfaceCard from '../components/SurfaceCard.vue'
import { service } from '../services'
import type { BloggerDetail } from '../types/domain'
import { formatCurrency, formatDate, formatPercent, valueTone } from '../utils/formatters'
import {
  createBloggerDetailBarOption,
  createBloggerDetailChartTheme,
  createBloggerDetailPieOption,
  disposeCharts,
  observeChartResize,
} from '../utils/chartTheme'

const route = useRoute()
const router = useRouter()
const blogger = ref<BloggerDetail | null>(null)
const loading = ref(true)
const error = ref('')
const pieElement = ref<HTMLElement | null>(null)
const barElement = ref<HTMLElement | null>(null)
let pieChart: echarts.ECharts | undefined
let barChart: echarts.ECharts | undefined
let cleanupChartResize = (): void => {}

const skeletonMetricLabels = ['收益率', '累计收益', '最大回撤', '观察天数']
const metrics = computed<Array<{ label: string; value: string; tone: 'default' | 'positive' | 'negative' | 'muted' }>>(() => blogger.value ? [
  { label: '收益率', value: formatPercent(blogger.value.returnRate), tone: valueTone(blogger.value.returnRate) },
  { label: '累计收益', value: formatCurrency(blogger.value.profit), tone: valueTone(blogger.value.profit) },
  { label: '最大回撤', value: formatPercent(blogger.value.maxDrawdown), tone: blogger.value.maxDrawdown === null ? 'muted' : 'negative' },
  { label: '观察天数', value: `${blogger.value.observeDays} 天`, tone: 'default' },
] : [])

function goToOverview(): void {
  router.push('/')
}

function goToImport(): void {
  router.push('/import')
}

function drawCharts(): void {
  if (!blogger.value) return

  cleanupChartResize()
  disposeCharts([pieChart, barChart])
  pieChart = undefined
  barChart = undefined
  const theme = createBloggerDetailChartTheme(pieElement.value ?? barElement.value)

  if (pieElement.value) {
    pieChart = echarts.init(pieElement.value)
    pieChart.setOption(createBloggerDetailPieOption(theme, blogger.value.positions.map((position) => ({
      name: position.fundName,
      value: position.allocation * 100,
    }))))
  }
  if (barElement.value) {
    barChart = echarts.init(barElement.value)
    barChart.setOption(createBloggerDetailBarOption(
      theme,
      blogger.value.monthlyOperationCount.map((item) => item.month),
      blogger.value.monthlyOperationCount.map((item) => item.count),
    ))
  }

  cleanupChartResize = observeChartResize([
    { element: pieElement.value, chart: pieChart },
    { element: barElement.value, chart: barChart },
  ])
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  blogger.value = null
  const id = Number(route.params.id)
  try {
    blogger.value = await service.getBloggerDetail(id)
    loading.value = false
    await nextTick()
    drawCharts()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '加载博主详情失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
onBeforeUnmount(() => {
  cleanupChartResize()
  disposeCharts([pieChart, barChart])
})
</script>

<template>
  <div class="detail-page">
    <PageHeader
      v-if="loading"
      title="博主详情"
      description="正在加载博主信息与组合数据。"
      eyebrow="博主详情"
      :loading="true"
    />
    <PageHeader
      v-else-if="error"
      title="博主详情"
      description="详情数据暂时不可用。"
      eyebrow="博主详情"
    >
      <template #actions>
        <el-button type="primary" aria-label="返回总览" @click="goToOverview">返回总览</el-button>
      </template>
    </PageHeader>
    <PageHeader
      v-else-if="blogger"
      :title="blogger.name"
      :description="`${blogger.sector} · ${formatDate(blogger.observeStartDate)}开始观察`"
      eyebrow="博主详情"
    >
      <template #actions>
        <BloggerStatusTag :status="blogger.status" />
        <el-button aria-label="返回总览" @click="goToOverview">返回总览</el-button>
        <el-button type="primary" aria-label="导入新截图" @click="goToImport">导入新截图</el-button>
      </template>
    </PageHeader>

    <div v-if="loading" class="detail-loading" aria-label="博主详情加载中" aria-busy="true">
      <section class="detail-metrics" aria-label="博主详情指标加载中">
        <MetricCard v-for="label in skeletonMetricLabels" :key="label" :label="label" value="--" loading />
      </section>
      <div class="detail-grid">
        <SurfaceCard heading="持仓分布" loading><div class="detail-skeleton-chart"><el-skeleton :rows="4" animated /></div></SurfaceCard>
        <SurfaceCard heading="月度操作次数" loading><div class="detail-skeleton-chart"><el-skeleton :rows="4" animated /></div></SurfaceCard>
      </div>
      <div class="section-stack">
        <SurfaceCard heading="当前持仓" loading><div class="detail-skeleton-table"><el-skeleton :rows="6" animated /></div></SurfaceCard>
        <SurfaceCard heading="操作历史" loading><div class="detail-skeleton-table"><el-skeleton :rows="6" animated /></div></SurfaceCard>
      </div>
    </div>

    <FeedbackRegion
      v-else-if="error"
      class="detail-feedback"
      kind="error"
      title="无法加载博主详情"
      :description="error"
      action="返回总览"
      @action="goToOverview"
    />

    <template v-else-if="blogger">
      <section class="detail-metrics" aria-label="博主详情指标">
        <MetricCard v-for="metric in metrics" :key="metric.label" :label="metric.label" :value="metric.value" :tone="metric.tone" />
      </section>

      <section class="detail-grid" aria-label="博主详情图表">
        <SurfaceCard heading="持仓分布" class="chart-card">
          <div ref="pieElement" class="chart" role="img" aria-label="持仓分布图表"></div>
        </SurfaceCard>
        <SurfaceCard heading="月度操作次数" class="chart-card">
          <div ref="barElement" class="chart" role="img" aria-label="月度操作次数图表"></div>
        </SurfaceCard>
      </section>

      <div class="section-stack">
        <SurfaceCard heading="当前持仓" :meta="`${blogger.positions.length} 只基金`" class="table-card">
          <PositionTable :positions="blogger.positions" />
        </SurfaceCard>
        <SurfaceCard heading="操作历史" :meta="`${blogger.operations.length} 条记录`" class="table-card">
          <OperationTable :operations="blogger.operations" />
        </SurfaceCard>
      </div>
    </template>
  </div>
</template>

<style scoped>
.detail-page,
.detail-page > * {
  min-width: 0;
}

.detail-feedback {
  margin-bottom: var(--space-6);
}

.detail-skeleton-chart {
  min-width: 0;
  min-height: 240px;
  display: flex;
  align-items: center;
  padding: var(--space-4);
}

.detail-skeleton-chart :deep(.el-skeleton) {
  width: 100%;
}

.detail-skeleton-table {
  min-height: 230px;
  padding: var(--space-5);
}

@media (max-width: 720px) {
  .detail-skeleton-chart {
    min-height: 210px;
  }

  .detail-skeleton-table {
    min-height: 210px;
    padding: var(--space-4);
  }
}
</style>
