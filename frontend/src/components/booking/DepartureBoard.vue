<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { Radio } from '@lucide/vue'
import { api, unwrap } from '@/api/client'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { fechaCorta, hora, hoyISO } from '@/lib/format'
import { ESTADO_SALIDA, etiqueta } from '@/lib/labels'

const { data, isLoading, isError } = useQuery({
  queryKey: ['salidas-proximas'],
  queryFn: () => unwrap(api.GET('/api/v1/salidas/proximas', { params: { query: { limite: 8 } } })),
  refetchInterval: 60_000,
})

function estado(s: { estado: string; minutos_demora: number }) {
  const e = etiqueta(ESTADO_SALIDA, s.estado)
  return s.estado === 'demorada' ? { ...e, label: `+${s.minutos_demora} min` } : e
}
const libres = (s: { clases: { asientos_libres: number }[] }) => s.clases.reduce((t, c) => t + c.asientos_libres, 0)
const esHoy = (iso: string) => new Date(iso).toLocaleDateString('en-CA', { timeZone: 'America/La_Paz' }) === hoyISO()
</script>

<template>
  <section class="overflow-hidden rounded-2xl bg-noche-900 text-white" aria-labelledby="tablero-titulo">
    <div class="flex items-center justify-between gap-3 border-b border-noche-700 px-5 py-4 sm:px-6">
      <h2 id="tablero-titulo" class="flex items-center gap-2.5 text-lg font-semibold">
        <span class="relative flex size-2.5" aria-hidden="true">
          <span class="absolute inline-flex size-full animate-ping rounded-full bg-carmin-500 opacity-60" />
          <span class="relative inline-flex size-2.5 rounded-full bg-carmin-500" />
        </span>
        Salidas en vivo
      </h2>
      <span class="flex items-center gap-1.5 text-xs text-noche-300"><Radio class="size-3.5" aria-hidden="true" />Se actualiza cada minuto</span>
    </div>
    <div v-if="isLoading" class="flex flex-col gap-3 p-5">
      <SkeletonBlock v-for="n in 4" :key="n" class="h-10 bg-noche-800!" />
    </div>
    <p v-else-if="isError" class="px-6 py-8 text-sm text-noche-200">No pudimos cargar el tablero en este momento.</p>
    <p v-else-if="!data?.length" class="px-6 py-8 text-sm text-noche-200">No hay salidas en las próximas horas.</p>
    <table v-else class="w-full text-sm">
      <caption class="sr-only">Próximas salidas de todas las rutas</caption>
      <thead class="text-left text-xs tracking-wider text-noche-300 uppercase">
        <tr>
          <th scope="col" class="px-5 py-2.5 font-semibold sm:px-6">Hora</th>
          <th scope="col" class="px-2 py-2.5 font-semibold">Ruta</th>
          <th scope="col" class="hidden px-2 py-2.5 font-semibold md:table-cell">Andén</th>
          <th scope="col" class="hidden px-2 py-2.5 font-semibold sm:table-cell">Libres</th>
          <th scope="col" class="px-5 py-2.5 text-right font-semibold sm:px-6">Estado</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in data" :key="s.id" class="border-t border-noche-800">
          <td class="px-5 py-3 sm:px-6">
            <span class="font-mono text-base font-semibold tabular">{{ hora(s.fecha_hora_salida) }}</span>
            <span v-if="!esHoy(s.fecha_hora_salida)" class="ml-1.5 text-xs text-noche-300">{{ fechaCorta(s.fecha_hora_salida) }}</span>
          </td>
          <td class="px-2 py-3 font-medium">{{ s.origen }} <span class="text-carmin-200">→</span> {{ s.destino }}</td>
          <td class="hidden px-2 py-3 text-noche-200 md:table-cell">{{ s.anden ?? '—' }}</td>
          <td class="hidden px-2 py-3 text-noche-200 tabular sm:table-cell">{{ libres(s) }}</td>
          <td class="px-5 py-3 text-right sm:px-6"><StatusBadge size="sm" :tono="estado(s).tono" :label="estado(s).label" /></td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
