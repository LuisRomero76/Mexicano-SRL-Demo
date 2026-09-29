<script setup lang="ts">
import { ArrowRight, Clock3, Route } from '@lucide/vue'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useCiudades, useRutas } from '@/api/queries'
import BaseButton from '@/components/ui/BaseButton.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import { bs, duracion, hoyISO, sumarDias } from '@/lib/format'

const router = useRouter()
const { data: rutas, isLoading, isError, error, refetch } = useRutas()
const { data: ciudadesCarga } = useCiudades({ carga: true })

const ordenadas = computed(() => [...(rutas.value ?? [])].sort((a, b) => a.codigo.localeCompare(b.codigo)))

function ver(origen: string, destino: string): void {
  void router.push({ name: 'resultados', query: { origen, destino, fecha: sumarDias(hoyISO(), 1), pasajeros: '1' } })
}
</script>

<template>
  <div>
    <section class="bg-noche-900 text-white">
      <div class="contenedor py-10 sm:py-14">
        <h1 class="text-[34px] font-bold sm:text-[44px]">Rutas e itinerarios</h1>
        <p class="mt-2 max-w-2xl text-noche-200">
          Viajes nocturnos entre Sucre y Santa Cruz, Tarija y La Paz, en buses de dos pisos Suite Cama y Leito Cama.
        </p>
      </div>
    </section>

    <div class="contenedor flex flex-col gap-10 py-10">
      <ErrorState v-if="isError" :error="error" @retry="refetch()" />
      <div v-else class="grid gap-5 md:grid-cols-2">
        <template v-if="isLoading"><SkeletonBlock v-for="n in 4" :key="n" class="h-64 rounded-2xl" /></template>
        <article v-for="r in ordenadas" :key="r.id" class="flex flex-col gap-5 rounded-2xl border border-line bg-surface p-6">
          <div class="flex items-start justify-between gap-3">
            <h2 class="flex flex-wrap items-center gap-2.5 text-xl font-semibold text-noche-900">
              {{ r.origen }} <ArrowRight class="size-5 text-carmin-600" aria-hidden="true" /> {{ r.destino }}
            </h2>
            <span class="codigo rounded-md bg-surface-2 px-2 py-1 text-xs text-muted">{{ r.codigo }}</span>
          </div>
          <ol class="flex flex-col" :aria-label="`Recorrido de ${r.origen} a ${r.destino}`">
            <li class="flex gap-3">
              <span class="mt-1.5 size-3 rounded-full bg-carmin-600" aria-hidden="true" />
              <span><strong>{{ r.origen }}</strong> <span class="text-sm text-muted">· salida</span></span>
            </li>
            <li v-for="p in r.paradas" :key="p.ciudad" class="ml-1.25 flex gap-3 border-l-2 border-dashed border-line-strong py-1.5 pl-4.5 text-sm text-muted">
              {{ p.ciudad }} · km {{ p.km_desde_origen }} · parada de carga
            </li>
            <li class="flex gap-3" :class="r.paradas.length ? '' : 'mt-3'">
              <span class="mt-1.5 size-3 rounded-full bg-noche-900" aria-hidden="true" />
              <span><strong>{{ r.destino }}</strong> <span class="text-sm text-muted">· llegada</span></span>
            </li>
          </ol>
          <dl class="grid grid-cols-3 gap-3 rounded-xl bg-canvas p-4 text-sm">
            <div><dt class="text-muted">Distancia</dt><dd class="font-semibold">{{ r.distancia_km }} km</dd></div>
            <div><dt class="text-muted">Duración</dt><dd class="font-semibold">{{ duracion(r.duracion_estimada_min) }}</dd></div>
            <div><dt class="text-muted">Desde</dt><dd class="font-semibold">{{ bs(r.precio_desde_bs) }}</dd></div>
          </dl>
          <div class="mt-auto flex flex-wrap items-center justify-between gap-3">
            <span class="flex items-center gap-2 text-sm text-muted">
              <Clock3 class="size-4" aria-hidden="true" />Salidas diarias: {{ r.horarios?.length ? r.horarios.join(' · ') : 'consultar' }}
            </span>
            <BaseButton size="sm" class="h-10" @click="ver(r.origen, r.destino)">Ver salidas</BaseButton>
          </div>
        </article>
      </div>

      <section class="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-6">
        <h2 class="flex items-center gap-2 font-sans text-lg font-bold"><Route class="size-5 text-carmin-600" aria-hidden="true" />Destinos de carga</h2>
        <ul class="flex flex-wrap gap-2">
          <li v-for="c in ciudadesCarga ?? []" :key="c.id" class="rounded-full bg-surface-2 px-3.5 py-1.5 text-sm font-medium">{{ c.nombre }}</li>
        </ul>
        <p class="text-sm text-muted">Potosí, Camargo y El Alto reciben carga en las paradas de las rutas a Tarija y La Paz.</p>
      </section>
    </div>
  </div>
</template>
