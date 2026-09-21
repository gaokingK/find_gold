<script setup lang="ts">
import { computed, useAttrs } from 'vue'

const attrs = useAttrs()
const props = withDefaults(defineProps<{
  modelValue: boolean
  title?: string
  width?: string
  size?: string | number
  variant?: 'dialog' | 'drawer'
  direction?: 'rtl' | 'ltr' | 'ttb' | 'btt'
  fullscreen?: boolean
  showClose?: boolean
  destroyOnClose?: boolean
}>(), {
  width: 'min(480px, calc(100vw - 32px))',
  size: 'min(480px, calc(100vw - 32px))',
  variant: 'dialog',
  direction: 'rtl',
  showClose: true,
  destroyOnClose: false,
})
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  open: []
  opened: []
  close: []
  closed: []
}>()
const panelComponent = computed(() => props.variant === 'drawer' ? 'el-drawer' : 'el-dialog')

function update(value: boolean): void {
  emit('update:modelValue', value)
}
</script>

<template>
  <component
    :is="panelComponent"
    v-bind="attrs"
    :model-value="modelValue"
    :title="title"
    :width="width"
    :size="size"
    :direction="direction"
    :fullscreen="fullscreen"
    :show-close="showClose"
    :destroy-on-close="destroyOnClose"
    :class="props.variant === 'dialog' ? 'responsive-dialog' : undefined"
    @update:model-value="update"
    @open="emit('open')"
    @opened="emit('opened')"
    @close="emit('close')"
    @closed="emit('closed')"
  >
    <template v-if="$slots.header" #header="scope"><slot name="header" v-bind="scope" /></template>
    <slot />
    <template v-if="$slots.footer" #footer><slot name="footer" /></template>
  </component>
</template>
