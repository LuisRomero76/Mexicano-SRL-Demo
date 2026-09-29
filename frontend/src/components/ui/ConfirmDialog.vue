<script setup lang="ts">
import AppDialog from './AppDialog.vue'
import BaseButton from './BaseButton.vue'

withDefaults(
  defineProps<{
    title: string
    description?: string
    confirmLabel?: string
    cancelLabel?: string
    danger?: boolean
    loading?: boolean
  }>(),
  { confirmLabel: 'Confirmar', cancelLabel: 'Volver' },
)
const abierto = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ confirm: [] }>()
</script>

<template>
  <AppDialog v-model:open="abierto" :title="title" :description="description" size="sm">
    <slot />
    <template #footer>
      <BaseButton variant="subtle" @click="abierto = false">{{ cancelLabel }}</BaseButton>
      <BaseButton :variant="danger ? 'danger' : 'primary'" :loading="loading" @click="emit('confirm')">
        {{ confirmLabel }}
      </BaseButton>
    </template>
  </AppDialog>
</template>
