<script setup lang="ts">
import StatusTag from './StatusTag.vue'
import type { BloggerStatus } from '../types/domain'
import type { VisualTone } from '../types/presentation'

const props = defineProps<{ status: BloggerStatus }>()
type StatusPresentation = { label: string; tone: VisualTone; icon: string }
const presentation: Record<BloggerStatus, StatusPresentation> = {
  active: { label: '已达标', tone: 'positive', icon: '✓' },
  observing: { label: '观察期中', tone: 'muted', icon: '…' },
  inactive: { label: '未开始', tone: 'warning', icon: '—' },
}
</script>

<template>
  <StatusTag :status="props.status" :label="presentation[props.status].label" :tone="presentation[props.status].tone" :icon="presentation[props.status].icon" />
</template>
