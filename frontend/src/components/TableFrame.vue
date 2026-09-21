<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
  count?: string | number
  loading?: boolean
  empty?: boolean
  error?: boolean
  disabled?: boolean
  label?: string
}>(), { label: '数据表格' })
</script>

<template>
  <section class="surface-card table-card table-frame" :class="{ 'is-loading': loading, 'is-disabled': disabled, 'has-error': error }" :aria-busy="loading || undefined" :aria-disabled="disabled || undefined" :aria-label="label">
    <header v-if="title || count !== undefined || $slots.heading || $slots.actions" class="card-heading table-frame__heading">
      <div class="table-frame__title"><slot name="heading"><h3 v-if="title">{{ title }}</h3></slot><span v-if="count !== undefined" class="muted-text">{{ count }}</span></div>
      <div v-if="$slots.actions" class="toolbar-actions"><slot name="actions" /></div>
    </header>
    <div v-if="loading" class="table-frame__state" role="status"><span class="state-mark" aria-hidden="true">…</span><span>加载中</span></div>
    <div v-else-if="error" class="table-frame__state state-error" role="alert"><span class="state-mark" aria-hidden="true">!</span><span>加载失败</span><slot name="error" /></div>
    <div v-else-if="empty" class="table-frame__state" role="status"><slot name="empty"><span class="state-mark" aria-hidden="true">—</span><span>暂无数据</span></slot></div>
    <div v-else class="table-scroll table-frame__body"><slot /></div>
  </section>
</template>
