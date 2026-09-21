<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  description?: string
  eyebrow?: string
  loading?: boolean
  disabled?: boolean
}>(), { eyebrow: 'FUND LENS' })
</script>

<template>
  <header class="page-header page-intro" :class="{ 'is-loading': loading, 'is-disabled': disabled }" :aria-busy="loading || undefined">
    <div class="page-header__copy">
      <span v-if="eyebrow" class="page-header__eyebrow">{{ eyebrow }}</span>
      <h2>{{ title }}</h2>
      <p v-if="description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>
