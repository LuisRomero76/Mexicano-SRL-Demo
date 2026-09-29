<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { ArrowLeft, BadgePercent } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, unwrap } from '@/api/client'
import BookingSteps from '@/components/booking/BookingSteps.vue'
import SeatMap from '@/components/booking/SeatMap.vue'
import TripSummary from '@/components/booking/TripSummary.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import { bs } from '@/lib/format'
import { useCompraStore, type AsientoElegido } from '@/stores/compra'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const router = useRouter()
const compra = useCompraStore()
const avisos = useToastStore()

const salidaId = computed(() => String(route.params.salidaId))
const pasajeros = computed(() => Math.min(6, Math.max(1, Number(route.query.pasajeros) || compra.estado.asientos.length || 1)))

const detalle = useQuery({
  queryKey: computed(() => ['salida', salidaId.value]),
  queryFn: () => unwrap(api.GET('/api/v1/salidas/{salida_id}', { params: { path: { salida_id: salidaId.value } } })),
  refetchInterval: 30_000,
})

const seleccion = ref<number[]>(
  compra.estado.salida?.id === salidaId.value ? compra.estado.asientos.map((a) => a.numero) : [],
)
const planta = ref<'alta' | 'baja'>('alta')

watch(
  () => detalle.data.value,
  (d) => {
    if (!d) return
    if (d.salida) compra.iniciar(d.salida)
    const ocupados = new Set(d.asientos.filter((a) => a.estado !== 'libre').map((a) => a.numero))
    const perdidos = seleccion.value.filter((n) => ocupados.has(n))
    if (perdidos.length) {
      seleccion.value = seleccion.value.filter((n) => !ocupados.has(n))
      avisos.info('Un asiento se acaba de ocupar', `El asiento ${perdidos.join(', ')} ya no está disponible. Elige otro.`)
    }
  },
)

const precios = computed(() => Object.fromEntries((detalle.data.value?.precios ?? []).map((p) => [p.tipo_asiento, p])))
const alta = computed(() => (detalle.data.value?.asientos ?? []).filter((a) => a.planta === 'alta'))
const baja = computed(() => (detalle.data.value?.asientos ?? []).filter((a) => a.planta === 'baja'))
const libres = (lista: { estado: string }[]) => lista.filter((a) => a.estado === 'libre').length

const elegidos = computed<AsientoElegido[]>(() =>
  seleccion.value
    .map((n) => detalle.data.value?.asientos.find((a) => a.numero === n))
    .filter((a): a is NonNullable<typeof a> => !!a)
    .map((a) => ({
      numero: a.numero,
      tipo_asiento: a.tipo_asiento,
      clase: precios.value[a.tipo_asiento]?.nombre ?? a.tipo_asiento,
      precio_bs: precios.value[a.tipo_asiento]?.precio_bs ?? 0,
    }))
    .sort((a, b) => a.numero - b.numero),
)
const total = computed(() => elegidos.value.reduce((t, a) => t + a.precio_bs, 0))
const faltan = computed(() => pasajeros.value - seleccion.value.length)

function continuar(): void {
  if (faltan.value !== 0) return
  compra.fijarAsientos(elegidos.value)
  void router.push({ name: 'pasajeros' })
}

const precioTexto = (codigo: string) => {
  const p = precios.value[codigo]
  return p ? `${bs(p.precio_bs)} por asiento` : ''
}
</script>

<template>
  <div>
    <BookingSteps :paso="2" />
    <div class="contenedor py-6 sm:py-8">
      <button class="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-fg" @click="router.back()">
        <ArrowLeft class="size-4" aria-hidden="true" />Volver a las salidas
      </button>

      <ErrorState v-if="detalle.isError.value" :error="detalle.error.value" @retry="detalle.refetch()" />
      <div v-else class="grid items-start gap-6 lg:grid-cols-[1fr_360px]">
        <div class="flex min-w-0 flex-col gap-5">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h1 class="text-2xl font-bold sm:text-[26px]">
                Elige {{ pasajeros }} {{ pasajeros === 1 ? 'asiento' : 'asientos' }}
              </h1>
              <p class="mt-1 text-sm text-muted">Toca un asiento libre. <span class="hidden md:inline">El frente del bus está a la izquierda.</span></p>
            </div>
            <ul class="flex gap-4 text-[13px]" aria-label="Leyenda">
              <li class="flex items-center gap-2"><span class="size-5 rounded-md border-[1.5px] border-[#9AA3B2] bg-surface" />Libre</li>
              <li class="flex items-center gap-2"><span class="size-5 rounded-md bg-carmin-600" />Tu elección</li>
              <li class="flex items-center gap-2"><span class="size-5 rounded-md bg-[#D9DDE4]" />Ocupado</li>
            </ul>
          </div>

          <div class="flex rounded-xl bg-surface-2 p-1 md:hidden" role="tablist" aria-label="Planta del bus">
            <button
              v-for="p in (['alta', 'baja'] as const)"
              :key="p"
              role="tab"
              :aria-selected="planta === p"
              class="h-11 flex-1 rounded-lg text-sm font-semibold"
              :class="planta === p ? 'bg-surface text-fg shadow-suave' : 'text-muted'"
              @click="planta = p"
            >
              Planta {{ p }} · {{ bs(precios[p === 'alta' ? 'SUITE_CAMA' : 'LEITO_CAMA']?.precio_bs) }}
            </button>
          </div>

          <template v-if="detalle.isLoading.value">
            <SkeletonBlock class="h-64 rounded-2xl" />
            <SkeletonBlock class="h-40 rounded-2xl" />
          </template>
          <template v-else>
            <div class="rounded-2xl border border-line bg-surface p-5" :class="planta === 'alta' ? '' : 'hidden md:block'">
              <SeatMap
                v-model="seleccion"
                :asientos="alta"
                :maximo="pasajeros"
                :titulo="`Planta alta · Suite Cama 180° · ${libres(alta)} libres`"
                :precio="precioTexto('SUITE_CAMA')"
              />
            </div>
            <div class="rounded-2xl border border-line bg-surface p-5" :class="planta === 'baja' ? '' : 'hidden md:block'">
              <SeatMap
                v-model="seleccion"
                :asientos="baja"
                :maximo="pasajeros"
                :titulo="`Planta baja · Leito Cama 160° · ${libres(baja)} libres`"
                :precio="precioTexto('LEITO_CAMA')"
              />
            </div>
            <p
              v-if="detalle.data.value?.precios.some((p) => p.es_precio_especial)"
              class="flex items-center gap-2 rounded-xl bg-exito-50 px-4 py-3 text-sm font-medium text-exito-800"
            >
              <BadgePercent class="size-5" aria-hidden="true" />Esta salida tiene precio promocional.
            </p>
          </template>
        </div>

        <aside class="hidden overflow-hidden rounded-2xl border border-line bg-surface lg:sticky lg:top-24 lg:block">
          <TripSummary v-if="detalle.data.value?.salida" :salida="detalle.data.value.salida" />
          <div class="flex flex-col gap-4 p-5">
            <p v-if="elegidos.length === 0" class="text-sm text-muted">Aún no elegiste asientos.</p>
            <ul class="flex flex-col gap-3">
              <li v-for="a in elegidos" :key="a.numero" class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-3">
                  <span class="flex size-9 items-center justify-center rounded-lg bg-carmin-600 text-sm font-bold text-white">{{ a.numero }}</span>
                  {{ a.clase }}
                </span>
                <strong class="tabular">{{ bs(a.precio_bs) }}</strong>
              </li>
            </ul>
            <div class="flex items-baseline justify-between border-t border-line pt-4">
              <span class="font-semibold">Total</span>
              <span class="font-display text-[28px] font-bold tabular">{{ bs(total) }}</span>
            </div>
            <BaseButton size="lg" block :disabled="faltan !== 0" @click="continuar">
              {{ faltan > 0 ? `Elige ${faltan} ${faltan === 1 ? 'asiento más' : 'asientos más'}` : 'Continuar con los pasajeros' }}
            </BaseButton>
            <p class="text-[13px] text-muted">Guardamos tus asientos 15 minutos mientras completas la compra.</p>
          </div>
        </aside>
      </div>
    </div>

    <div class="fixed inset-x-0 bottom-16 z-30 flex items-center gap-4 border-t border-line bg-surface px-4 py-3 shadow-[0_-8px_24px_rgb(11_27_51/0.08)] lg:hidden">
      <div class="min-w-0 flex-1">
        <p class="truncate text-[13px] text-muted">
          {{ elegidos.length ? `Asientos ${elegidos.map((a) => a.numero).join(', ')}` : `Elige ${pasajeros} ${pasajeros === 1 ? 'asiento' : 'asientos'}` }}
        </p>
        <p class="font-display text-xl font-bold tabular">{{ bs(total) }}</p>
      </div>
      <BaseButton :disabled="faltan !== 0" @click="continuar">Continuar</BaseButton>
    </div>
  </div>
</template>
