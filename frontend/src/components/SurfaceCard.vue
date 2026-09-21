<script setup lang="ts">
withDefaults(defineProps<{
  heading?: string
  meta?: string
  loading?: boolean
  disabled?: boolean
  selected?: boolean
  interactive?: boolean
}>(), { interactive: false })
</script>

<template>
  <section class="surface-card shared-surface-card" :class="{ 'is-loading': loading, 'is-disabled': disabled, 'is-selected': selected, 'is-interactive': interactive }" :aria-busy="loading || undefined" :aria-disabled="disabled || undefined">
    <header v-if="heading || meta || $slots.heading || $slots.actions" class="card-heading shared-surface-card__heading">
      <div class="shared-surface-card__title"><slot name="heading"><h3 v-if="heading">{{ heading }}</h3></slot><span v-if="meta" class="muted-text">{{ meta }}</span></div>
      <div v-if="$slots.actions" class="toolbar-actions"><slot name="actions" /></div>
    </header>
    <div class="shared-surface-card__body"><slot /></div>
  </section>
</template>
