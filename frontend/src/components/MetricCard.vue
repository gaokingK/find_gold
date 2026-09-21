<script setup lang="ts">
const props = withDefaults(defineProps<{
  label: string
  value: string
  tone?: 'default' | 'positive' | 'negative' | 'muted'
  loading?: boolean
  disabled?: boolean
  selected?: boolean
}>(), { tone: 'default' })
</script>

<template>
  <section class="metric-card shared-metric-card" :class="{ 'is-loading': loading, 'is-disabled': disabled, 'is-selected': selected }" :aria-label="label" role="group" :aria-busy="loading || undefined" :aria-disabled="disabled || undefined">
    <span class="metric-label">{{ label }}</span>
    <strong class="metric-value" :class="`tone-${props.tone}`">{{ value }}</strong>
  </section>
</template>
