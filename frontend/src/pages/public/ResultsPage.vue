<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { ArrowRight, BusFront, CircleAlert, SlidersHorizontal } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, unwrap, type Schemas } from '@/api/client'
import { usePoliticas } from '@/api/queries'
import BookingSteps from '@/components/booking/BookingSteps.vue'
import DateStrip from '@/components/booking/DateStrip.vue'
import DepartureCard from '@/components/booking/DepartureCard.vue'
import TripSearchForm from '@/components/booking/TripSearchForm.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import { fechaLarga, hoyISO, sumarDias } from '@/lib/format'
import { useCompraStore } from '@/stores/compra'

const route = useRoute()
const router = useRouter()
const compra = useCompraStore()
const { data: politicas } = usePoliticas()

const texto = (v: unknown, def: string) => (typeof v === 'string' && v ? v : def)
const origen = computed(() => texto(route.query.origen, 'Sucre'))
const destino = computed(() => texto(route.query.destino, 'Santa Cruz'))
const fecha = computed(() => {
  const f = texto(route.query.fecha, hoyISO())
  return /^\d{4}-\d{2}-\d{2}$/.test(f) && f >= hoyISO() ? f : hoyISO()
})
const pasajeros = computed(() => Math.min(6, Math.max(1, Number(route.query.pasajeros) || 1)))

const inicioVentana = ref(fecha.value)
watch(fecha, (f) => {
  if (f < inicioVentana.value || f > sumarDias(inicioVentana.value, 6)) inicioVentana.value = f
})

const calendario = useQuery({
  queryKey: computed(() => ['calendario', origen.value, destino.value, inicioVentana.value]),
  queryFn: () =>
    unwrap(
      api.GET('/api/v1/salidas/calendario', {
        params: { query: { origen: origen.value, destino: destino.value, desde: inicioVentana.value, dias: 7 } },
      }),
    ),
})

const busqueda = useQuery({
  queryKey: computed(() => ['salidas', origen.value, destino.value, fecha.value]),
  queryFn: () =>
    unwrap(api.GET('/api/v1/salidas', { params: { query: { origen: origen.value, destino: destino.value, fecha: fecha.value } } })),
})

const fechaSeleccionada = computed({
  get: () => fecha.value,
  set: (f: string) => void router.replace({ query: { ...route.query, fecha: f } }),
})

function mover(dias: number): void {
  const nuevo = sumarDias(inicioVentana.value, dias)
  inicioVentana.value = nuevo < hoyISO() ? hoyISO() : nuevo
}

const clase = ref<'todas' | 'SUITE_CAMA' | 'LEITO_CAMA'>('todas')
const horario = ref<'todas' | 'temprano' | 'tarde'>('todas')
const orden = ref<'hora' | 'precio'>('hora')
const modificar = ref(false)

const precioMinimo = (s: Schemas['SalidaResumen']) => Math.min(...s.clases.map((c) => c.precio_bs ?? Infinity))
const salidas = computed(() => {
  let lista = (busqueda.data.value?.salidas ?? []).map((s) => ({
    ...s,
    clases: clase.value === 'todas' ? s.clases : s.clases.filter((c) => c.codigo === clase.value),
  }))
  lista = lista.filter((s) => s.clases.length > 0)
  if (horario.value !== 'todas') {
    lista = lista.filter((s) => {
      const h = Number(new Date(s.fecha_hora_salida).toLocaleTimeString('en-GB', { timeZone: 'America/La_Paz', hour: '2-digit' }))
      return horario.value === 'temprano' ? h < 19 : h >= 19
    })
  }
  return orden.value === 'precio' ? [...lista].sort((a, b) => precioMinimo(a) - precioMinimo(b)) : lista
})

function elegir(salida: Schemas['SalidaResumen']): void {
  const original = busqueda.data.value?.salidas.find((s) => s.id === salida.id) ?? salida
  compra.iniciar(original)
  void router.push({ name: 'asientos', params: { salidaId: salida.id }, query: { pasajeros: String(pasajeros.value) } })
}

const esRutaInvalida = computed(() => (busqueda.error.value as { code?: string } | null)?.code === 'ruta_no_disponible')
</script>

<template>
  <div>
    <BookingSteps :paso="1" />
    <section class="bg-noche-900 text-white">
      <div class="contenedor flex flex-col gap-4 py-5 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 class="flex flex-wrap items-center gap-3 text-2xl font-bold sm:text-[28px]">
            {{ origen }} <ArrowRight class="size-6 text-carmin-200" aria-hidden="true" /> {{ destino }}
          </h1>
          <p class="mt-1 text-sm text-noche-200">
            {{ fechaLarga(fecha) }} · {{ pasajeros }} {{ pasajeros === 1 ? 'pasajero' : 'pasajeros' }}
          </p>
        </div>
        <BaseButton variant="white" size="sm" class="h-10 self-start md:self-auto" :aria-expanded="modificar" @click="modificar = !modificar">
          <SlidersHorizontal class="size-4" aria-hidden="true" />{{ modificar ? 'Cerrar' : 'Modificar búsqueda' }}
        </BaseButton>
      </div>
      <div v-if="modificar" class="contenedor pb-6">
        <div class="rounded-2xl bg-surface p-4 text-fg">
          <TripSearchForm
            :key="route.fullPath"
            :initial="{ origen, destino, fecha, pasajeros }"
            @submitted="modificar = false"
          />
        </div>
      </div>
    </section>

    <div class="contenedor flex flex-col gap-6 py-6 sm:py-8">
      <DateStrip
        v-if="!esRutaInvalida"
        v-model="fechaSeleccionada"
        :dias="calendario.data.value?.dias"
        :loading="calendario.isLoading.value"
        :puede-retroceder="inicioVentana > hoyISO()"
        @mover="mover"
      />

      <div class="grid items-start gap-6 lg:grid-cols-[280px_1fr]">
        <aside class="flex flex-col gap-4 lg:sticky lg:top-24">
          <div class="flex flex-col gap-5 rounded-2xl border border-line bg-surface p-5">
            <SegmentedControl
              v-model="clase"
              label="Clase"
              variant="switch"
              :options="[
                { value: 'todas', label: 'Todas' },
                { value: 'SUITE_CAMA', label: 'Suite' },
                { value: 'LEITO_CAMA', label: 'Leito' },
              ]"
            />
            <SegmentedControl
              v-model="horario"
              label="Hora de salida (tarde: antes de las 19:00)"
              variant="switch"
              :options="[
                { value: 'todas', label: 'Todas' },
                { value: 'temprano', label: 'Tarde' },
                { value: 'tarde', label: 'Noche' },
              ]"
            />
            <SegmentedControl
              v-model="orden"
              label="Ordenar por"
              variant="switch"
              :options="[
                { value: 'hora', label: 'Hora' },
                { value: 'precio', label: 'Precio' },
              ]"
            />
          </div>
          <div v-if="politicas" class="hidden flex-col gap-2.5 rounded-2xl bg-noche-900 p-5 text-sm leading-relaxed text-white lg:flex">
            <strong class="font-display text-base">Antes de viajar</strong>
            <span class="text-noche-200">{{ politicas.equipaje_bodega_kg }} kg en bodega y {{ politicas.equipaje_mano_kg }} kg de mano por pasajero.</span>
            <span class="text-noche-200">Menores de 3 a 11 años (50 %) y adultos mayores (20 %) compran en boletería con su documento.</span>
            <RouterLink :to="{ name: 'ayuda' }" class="font-semibold text-carmin-200 hover:underline">Ver políticas de viaje</RouterLink>
          </div>
        </aside>

        <div class="flex min-w-0 flex-col gap-4" aria-live="polite">
          <template v-if="busqueda.isLoading.value">
            <SkeletonBlock v-for="n in 2" :key="n" class="h-56 rounded-2xl" />
          </template>
          <ErrorState
            v-else-if="busqueda.isError.value"
            :title="esRutaInvalida ? 'Esa ruta no está disponible' : undefined"
            :error="busqueda.error.value"
            @retry="busqueda.refetch()"
          />
          <template v-else>
            <p class="text-[15px] text-muted">
              <strong class="text-fg">{{ salidas.length }} {{ salidas.length === 1 ? 'salida' : 'salidas' }}</strong>
              el {{ fechaLarga(fecha) }}
            </p>
            <DepartureCard
              v-for="s in salidas"
              :key="s.id"
              :salida="s"
              :pasajeros="pasajeros"
              :duracion-min="busqueda.data.value?.duracion_estimada_min ?? 0"
              @elegir="elegir"
            />
            <EmptyState
              v-if="salidas.length === 0"
              :icon="BusFront"
              title="No hay salidas con esos filtros"
              text="Prueba con otra fecha de la franja superior o quita los filtros."
            />
            <div class="flex gap-3 rounded-2xl border border-aviso-600/30 bg-aviso-50 p-4 text-sm text-aviso-800 dark:bg-aviso-600/10 dark:text-amber-200">
              <CircleAlert class="size-5 shrink-0" aria-hidden="true" />
              <span>Los horarios pueden cambiar por condiciones del camino o del clima. Si cancelamos un viaje, te devolvemos el 100 % de inmediato.</span>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
