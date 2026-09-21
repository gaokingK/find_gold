<script setup lang="ts">
withDefaults(defineProps<{
  description?: string
  loading?: boolean
  error?: boolean
}>(), { description: '暂无符合条件的记录' })
</script>

<template>
  <div class="empty-state table-frame__state" :class="{ 'is-loading': loading, 'has-error': error }" :role="error ? 'alert' : 'status'" :aria-busy="loading || undefined">
    <span class="state-mark" aria-hidden="true">{{ error ? '!' : loading ? '…' : '—' }}</span>
    <strong class="empty-state__title">{{ description }}</strong>
    <div v-if="$slots.default" class="empty-state__actions"><slot /></div>
  </div>
</template>
