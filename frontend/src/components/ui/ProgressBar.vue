<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ value: number; max: number; label?: string }>()
const pct = computed(() => (props.max > 0 ? Math.min(100, Math.round((props.value / props.max) * 100)) : 0))
const color = computed(() => (pct.value >= 90 ? 'bg-carmin-600' : 'bg-noche-700 dark:bg-sky-400'))
</script>

<template>
  <div class="flex items-center gap-2.5">
    <div
      class="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-2"
      role="progressbar"
      :aria-valuenow="value"
      :aria-valuemin="0"
      :aria-valuemax="max"
      :aria-label="label ?? 'Ocupación'"
    >
      <div class="h-full rounded-full transition-[width]" :class="color" :style="{ width: `${pct}%` }" />
    </div>
    <span class="w-12 shrink-0 text-right text-[13px] tabular text-muted">{{ value }}/{{ max }}</span>
  </div>
</template>
