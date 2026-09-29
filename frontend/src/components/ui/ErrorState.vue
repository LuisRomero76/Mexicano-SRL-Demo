<script setup lang="ts">
import { RotateCw, TriangleAlert } from '@lucide/vue'
import { mensajeDeError } from '@/api/client'
import BaseButton from './BaseButton.vue'

defineProps<{ error: unknown; title?: string }>()
const emit = defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="flex flex-col items-center gap-3 rounded-2xl border border-line bg-surface px-6 py-10 text-center" role="alert">
    <span class="flex size-12 items-center justify-center rounded-full bg-peligro-50 text-peligro-600">
      <TriangleAlert class="size-6" aria-hidden="true" />
    </span>
    <p class="font-display text-lg font-semibold">{{ title ?? 'No pudimos cargar la información' }}</p>
    <p class="max-w-md text-[15px] text-muted">{{ mensajeDeError(error) }}</p>
    <BaseButton variant="subtle" size="sm" @click="emit('retry')"><RotateCw class="size-4" />Reintentar</BaseButton>
  </div>
</template>
