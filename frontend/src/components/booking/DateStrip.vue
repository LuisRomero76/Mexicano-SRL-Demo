<script setup lang="ts">
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import type { Schemas } from '@/api/client'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import { bs, diaSemanaISO, hoyISO } from '@/lib/format'

defineProps<{ dias: Schemas['DiaCalendario'][] | undefined; loading?: boolean; puedeRetroceder: boolean }>()
const seleccion = defineModel<string>({ required: true })
const emit = defineEmits<{ mover: [dias: number] }>()

const nombres = ['', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
const etiqueta = (iso: string) => (iso === hoyISO() ? 'Hoy' : `${nombres[diaSemanaISO(iso)]} ${Number(iso.slice(8))}`)
</script>

<template>
  <div class="flex items-stretch gap-2">
    <button
      class="hidden w-10 shrink-0 items-center justify-center rounded-xl border border-line bg-surface text-muted hover:text-fg disabled:opacity-40 sm:flex"
      :disabled="!puedeRetroceder"
      aria-label="Días anteriores"
      @click="emit('mover', -7)"
    >
      <ChevronLeft class="size-5" />
    </button>
    <div class="grid flex-1 auto-cols-[minmax(92px,1fr)] grid-flow-col gap-2 overflow-x-auto pb-1 sm:grid-flow-row sm:grid-cols-7 sm:overflow-visible">
      <template v-if="loading || !dias">
        <SkeletonBlock v-for="n in 7" :key="n" class="h-[68px] rounded-xl" />
      </template>
      <button
        v-for="d in dias"
        v-else
        :key="d.fecha"
        type="button"
        class="flex h-[68px] flex-col items-center justify-center gap-0.5 rounded-xl border px-2 transition-colors"
        :class="
          seleccion === d.fecha
            ? 'border-2 border-carmin-600 bg-carmin-50 text-carmin-800'
            : d.disponible
              ? 'border-line bg-surface hover:border-noche-400'
              : 'border-line bg-surface-2 text-muted'
        "
        :aria-pressed="seleccion === d.fecha"
        @click="seleccion = d.fecha"
      >
        <span class="text-[13px]" :class="seleccion === d.fecha ? 'font-bold' : ''">{{ etiqueta(d.fecha) }}</span>
        <span class="text-[15px] font-bold tabular">{{ d.disponible ? bs(d.precio_desde_bs) : 'Sin cupos' }}</span>
      </button>
    </div>
    <button
      class="hidden w-10 shrink-0 items-center justify-center rounded-xl border border-line bg-surface text-muted hover:text-fg sm:flex"
      aria-label="Días siguientes"
      @click="emit('mover', 7)"
    >
      <ChevronRight class="size-5" />
    </button>
  </div>
</template>
