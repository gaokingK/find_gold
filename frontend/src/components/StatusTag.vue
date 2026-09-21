<script setup lang="ts">
import type { VisualTone } from '../types/presentation'

const props = withDefaults(defineProps<{
  status: string
  label?: string
  tone?: VisualTone
  icon?: string
  disabled?: boolean
  selected?: boolean
}>(), { tone: 'default' })

const toneIcons: Record<VisualTone, string> = { default: '•', positive: '✓', negative: '↓', muted: '—', warning: '!', error: '×' }
</script>

<template>
  <span class="status-tag" :class="[`status-tag--${props.tone}`, { 'is-disabled': disabled, 'is-selected': selected }]" :aria-label="`${label ?? status}${disabled ? '（不可用）' : ''}`">
    <span class="status-tag__mark" aria-hidden="true">{{ icon ?? toneIcons[tone] }}</span>
    <span>{{ label ?? status }}</span>
  </span>
</template>
