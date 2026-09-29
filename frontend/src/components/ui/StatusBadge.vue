<script setup lang="ts">
import { computed } from 'vue'
import type { Tono } from '@/lib/labels'

const props = withDefaults(defineProps<{ tono?: Tono; label: string; dot?: boolean; size?: 'sm' | 'md' }>(), {
  tono: 'neutro',
  dot: true,
  size: 'md',
})

const estilos: Record<Tono, { caja: string; punto: string }> = {
  exito: { caja: 'bg-exito-50 text-exito-800 dark:bg-exito-600/20 dark:text-emerald-200', punto: 'bg-exito-600' },
  info: { caja: 'bg-info-50 text-info-800 dark:bg-info-600/20 dark:text-blue-200', punto: 'bg-info-600' },
  aviso: { caja: 'bg-aviso-50 text-aviso-800 dark:bg-aviso-600/20 dark:text-amber-200', punto: 'bg-aviso-600' },
  peligro: { caja: 'bg-peligro-50 text-peligro-800 dark:bg-peligro-600/25 dark:text-red-200', punto: 'bg-peligro-600' },
  neutro: { caja: 'bg-[#EEF0F3] text-[#374151] dark:bg-white/10 dark:text-noche-200', punto: 'bg-[#6B7280]' },
  turquesa: {
    caja: 'bg-turquesa-50 text-turquesa-800 dark:bg-turquesa-600/25 dark:text-teal-200',
    punto: 'bg-turquesa-600',
  },
  noche: { caja: 'bg-noche-900 text-white dark:bg-noche-600', punto: 'bg-sky-300' },
  carmin: { caja: 'bg-carmin-50 text-carmin-800', punto: 'bg-carmin-600' },
}
const e = computed(() => estilos[props.tono])
</script>

<template>
  <span
    class="inline-flex shrink-0 items-center gap-1.5 rounded-full font-semibold whitespace-nowrap"
    :class="[e.caja, size === 'sm' ? 'h-6 px-2 text-xs' : 'h-7 px-2.5 text-[13px]']"
  >
    <span v-if="dot" class="size-2 rounded-full" :class="e.punto" aria-hidden="true" />
    {{ label }}
  </span>
</template>
