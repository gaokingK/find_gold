<script setup lang="ts">
withDefaults(defineProps<{
  loading?: boolean
  disabled?: boolean
  label?: string
}>(), { label: '筛选条件' })
</script>

<template>
  <section class="surface-card filter-bar filter-card" :class="{ 'is-loading': loading, 'is-disabled': disabled }" :aria-busy="loading || undefined" :aria-disabled="disabled || undefined">
    <div class="filter-bar__content">
      <span class="sr-only">{{ label }}</span>
      <slot />
    </div>
    <div v-if="$slots.actions" class="filter-bar__actions toolbar-actions"><slot name="actions" /></div>
  </section>
</template>
