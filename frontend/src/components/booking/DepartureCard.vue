<script setup lang="ts">
import { Armchair, Clock3 } from '@lucide/vue'
import { computed } from 'vue'
import type { Schemas } from '@/api/client'
import BaseButton from '@/components/ui/BaseButton.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { bs, duracion, esDiaSiguiente, fechaCorta, hora } from '@/lib/format'
import { ESTADO_SALIDA, etiqueta } from '@/lib/labels'

const props = defineProps<{ salida: Schemas['SalidaResumen']; pasajeros: number; duracionMin: number }>()
const emit = defineEmits<{ elegir: [salida: Schemas['SalidaResumen']] }>()

const estado = computed(() => {
  const e = etiqueta(ESTADO_SALIDA, props.salida.estado)
  return props.salida.estado === 'demorada' ? { ...e, label: `Demorada ${props.salida.minutos_demora} min` } : e
})
const libresTotal = computed(() => props.salida.clases.reduce((t, c) => t + c.asientos_libres, 0))
const alcanza = computed(() => libresTotal.value >= props.pasajeros)
</script>

<template>
  <article class="overflow-hidden rounded-2xl border border-line bg-surface transition-shadow hover:shadow-suave">
    <div class="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:gap-7 sm:px-6">
      <div class="flex flex-1 items-center gap-4 sm:gap-7">
        <div class="flex flex-col">
          <span class="font-display text-[28px] leading-none font-bold tabular sm:text-[30px]">{{ hora(salida.fecha_hora_salida) }}</span>
          <span class="mt-1 text-sm text-muted">{{ salida.origen }}</span>
        </div>
        <div class="flex flex-1 flex-col items-center gap-1.5">
          <span class="flex items-center gap-1 text-xs text-muted"><Clock3 class="size-3.5" aria-hidden="true" />{{ duracion(duracionMin) }}</span>
          <div class="flex w-full items-center gap-1.5" aria-hidden="true">
            <span class="size-2.5 rounded-full border-2 border-noche-900 dark:border-noche-300" />
            <span class="h-0.5 flex-1 bg-noche-900 dark:bg-noche-300" />
            <span class="size-2.5 rounded-full bg-noche-900 dark:bg-noche-300" />
          </div>
          <span class="text-xs text-muted">Directo</span>
        </div>
        <div class="flex flex-col text-right">
          <span class="font-display text-[28px] leading-none font-bold tabular sm:text-[30px]">
            {{ hora(salida.fecha_hora_llegada_estimada) }}<sup v-if="esDiaSiguiente(salida.fecha_hora_salida, salida.fecha_hora_llegada_estimada)" class="ml-0.5 text-xs font-semibold text-carmin-600">+1</sup>
          </span>
          <span class="mt-1 text-sm text-muted">{{ salida.destino }} · {{ fechaCorta(salida.fecha_hora_llegada_estimada) }}</span>
        </div>
      </div>
      <StatusBadge :label="estado.label" :tono="estado.tono" class="self-start sm:self-center" />
    </div>
    <div class="grid border-t border-line sm:grid-cols-2">
      <div
        v-for="c in salida.clases"
        :key="c.tipo_asiento_id"
        class="flex items-center justify-between gap-4 px-5 py-4 not-last:border-b sm:px-6 sm:not-last:border-r sm:not-last:border-b-0 border-line"
      >
        <div class="flex flex-col gap-0.5">
          <span class="font-semibold">{{ c.nombre }} <span class="font-normal text-muted">· {{ c.codigo === 'SUITE_CAMA' ? '180°' : '160°' }}</span></span>
          <span
            class="flex items-center gap-1 text-[13px] font-semibold"
            :class="c.asientos_libres === 0 ? 'text-muted' : c.asientos_libres <= 5 ? 'text-aviso-700' : 'text-exito-600'"
          >
            <Armchair class="size-3.5" aria-hidden="true" />
            {{ c.asientos_libres === 0 ? 'Agotado' : c.asientos_libres <= 5 ? `Quedan ${c.asientos_libres}` : `${c.asientos_libres} libres` }}
          </span>
        </div>
        <div class="text-right">
          <span class="block text-xs text-muted">por asiento</span>
          <span class="font-display text-[22px] font-bold tabular">{{ bs(c.precio_bs) }}</span>
        </div>
      </div>
    </div>
    <div class="flex flex-col gap-3 bg-surface-2/60 px-5 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
      <span class="text-[13px] text-muted">
        Bus {{ salida.bus ?? 'por asignar' }}<template v-if="salida.anden"> · Andén {{ salida.anden }}</template> · Aire · Calefacción · USB · Baño
      </span>
      <BaseButton v-if="salida.vendible && alcanza" size="md" @click="emit('elegir', salida)">Elegir asientos</BaseButton>
      <span v-else class="text-sm font-semibold text-muted">{{ !salida.vendible ? 'Venta cerrada' : 'No hay asientos suficientes' }}</span>
    </div>
  </article>
</template>
