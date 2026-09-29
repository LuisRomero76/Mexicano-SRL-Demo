<script setup lang="ts">
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import { computed } from 'vue'

const props = defineProps<{ total: number; limit: number }>()
const offset = defineModel<number>('offset', { required: true })

const pagina = computed(() => Math.floor(offset.value / props.limit) + 1)
const paginas = computed(() => Math.max(1, Math.ceil(props.total / props.limit)))
const desde = computed(() => (props.total === 0 ? 0 : offset.value + 1))
const hasta = computed(() => Math.min(props.total, offset.value + props.limit))
</script>

<template>
  <nav class="flex items-center justify-between gap-3 border-t border-line px-5 py-3 text-sm text-muted" aria-label="Paginación">
    <span>{{ desde }}–{{ hasta }} de {{ total }}</span>
    <div class="flex items-center gap-1">
      <button
        class="flex size-9 items-center justify-center rounded-lg hover:bg-surface-2 disabled:opacity-40"
        :disabled="pagina <= 1"
        aria-label="Página anterior"
        @click="offset = Math.max(0, offset - limit)"
      >
        <ChevronLeft class="size-4" />
      </button>
      <span class="px-2 font-medium text-fg">{{ pagina }} / {{ paginas }}</span>
      <button
        class="flex size-9 items-center justify-center rounded-lg hover:bg-surface-2 disabled:opacity-40"
        :disabled="pagina >= paginas"
        aria-label="Página siguiente"
        @click="offset = offset + limit"
      >
        <ChevronRight class="size-4" />
      </button>
    </div>
  </nav>
</template>
