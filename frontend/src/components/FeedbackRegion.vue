<script setup lang="ts">
import type { FeedbackKind } from '../types/presentation'

const props = withDefaults(defineProps<{
  kind?: FeedbackKind
  title?: string
  description?: string
  action?: string
  disabled?: boolean
}>(), { kind: 'info' })
const emit = defineEmits<{ action: [] }>()
const kindIcons: Record<FeedbackKind, string> = { success: '✓', error: '!', warning: '!', info: 'i' }
</script>

<template>
  <section v-if="title || description || $slots.default" class="feedback-region" :class="[`feedback-region--${props.kind}`, { 'is-disabled': disabled }]" :role="kind === 'error' ? 'alert' : 'status'" aria-live="polite">
    <span class="feedback-region__mark" aria-hidden="true">{{ kindIcons[kind] }}</span>
    <div class="feedback-region__content"><strong v-if="title">{{ title }}</strong><p v-if="description">{{ description }}</p><slot /></div>
    <button v-if="action" type="button" class="feedback-region__action" :disabled="disabled" @click="emit('action')">{{ action }}</button>
    <div v-if="$slots.action" class="feedback-region__action"><slot name="action" /></div>
  </section>
</template>
