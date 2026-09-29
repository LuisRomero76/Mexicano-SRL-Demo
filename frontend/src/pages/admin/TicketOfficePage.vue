<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { onKeyStroke } from '@vueuse/core'
import { CircleCheck, Printer, RotateCcw, UserSearch } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { ApiError, api, unwrap, type Schemas } from '@/api/client'
import { usePoliticas } from '@/api/queries'
import SeatMap from '@/components/booking/SeatMap.vue'
import TicketCard from '@/components/booking/TicketCard.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import CheckboxInput from '@/components/ui/CheckboxInput.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { bs, bsExacto, hora, hoyISO } from '@/lib/format'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

type TipoPasajero = Schemas['TipoPasajero']
interface Pasajero {
  numero_asiento: number
  tipo_pasajero: TipoPasajero
  numero_documento: string
  nombres: string
  apellidos: string
  fecha_nacimiento: string
  permiso_viaje_numero: string
  semanas_gestacion: string
  viaja_con_perro_guia: boolean
}

const auth = useAuthStore()
const avisos = useToastStore()
const cliente = useQueryClient()
const { data: politicas } = usePoliticas()

const fecha = ref(hoyISO())
const salidasDelDia = useQuery({
  queryKey: computed(() => ['admin-salidas', { fecha: fecha.value, pos: true }]),
  queryFn: () => unwrap(api.GET('/api/v1/admin/salidas', { params: { query: { fecha: fecha.value, limit: 50 } } })),
  refetchInterval: 60_000,
})
const vendibles = computed(() =>
  (salidasDelDia.data.value?.items ?? []).filter(
    (s) => ['programada', 'demorada', 'abordando'].includes(s.estado) && new Date(s.fecha_hora_salida).getTime() > Date.now(),
  ),
)
const salidaId = ref<string | null>(null)
watch(vendibles, (l) => {
  if (!salidaId.value || !l.some((s) => s.id === salidaId.value)) salidaId.value = l[0]?.id ?? null
})

const mapa = useQuery({
  queryKey: computed(() => ['salida', salidaId.value]),
  queryFn: () => unwrap(api.GET('/api/v1/salidas/{salida_id}', { params: { path: { salida_id: salidaId.value! } } })),
  enabled: computed(() => !!salidaId.value),
  refetchInterval: 20_000,
})
const planta = ref<'alta' | 'baja'>('alta')
const seleccion = ref<number[]>([])
const pasajeros = ref<Pasajero[]>([])
watch(salidaId, () => {
  seleccion.value = []
  venta.value = null
})

watch(seleccion, (nums) => {
  const previos = new Map(pasajeros.value.map((p) => [p.numero_asiento, p]))
  pasajeros.value = [...nums].sort((a, b) => a - b).map(
    (n) =>
      previos.get(n) ?? {
        numero_asiento: n,
        tipo_pasajero: 'adulto',
        numero_documento: '',
        nombres: '',
        apellidos: '',
        fecha_nacimiento: '',
        permiso_viaje_numero: '',
        semanas_gestacion: '',
        viaja_con_perro_guia: false,
      },
  )
})

const precios = computed(() => Object.fromEntries((mapa.data.value?.precios ?? []).map((p) => [p.tipo_asiento, p])))
const politicaDe = (t: TipoPasajero) => politicas.value?.tipos_pasajero.find((p) => p.tipo_pasajero === t)
const opcionesTarifa = computed(() =>
  (politicas.value?.tipos_pasajero ?? []).map((p) => ({
    value: p.tipo_pasajero,
    label: p.descuento_porcentaje ? `${p.nombre.split(' (')[0]} −${p.descuento_porcentaje} %` : p.nombre.split(' (')[0],
  })),
)
function claseDe(n: number): string {
  return mapa.data.value?.asientos.find((a) => a.numero === n)?.tipo_asiento ?? 'SUITE_CAMA'
}
/** Estimación local (el precio final lo calcula el backend). */
function estimado(p: Pasajero): number {
  const precio = precios.value[claseDe(p.numero_asiento)]
  if (!precio) return 0
  const pct = politicaDe(p.tipo_pasajero)?.descuento_porcentaje ?? 0
  if (!pct) return precio.precio_bs
  return Math.min(precio.precio_bs, precio.precio_maximo_referencial_bs * (1 - pct / 100))
}
const totalEstimado = computed(() => pasajeros.value.reduce((t, p) => t + estimado(p), 0))
function edad(fechaNac: string): number | null {
  if (!fechaNac) return null
  const [a, m, d] = fechaNac.split('-').map(Number)
  const [ha, hm, hd] = hoyISO().split('-').map(Number)
  return ha - a - (hm < m || (hm === m && hd < d) ? 1 : 0)
}

async function buscarCliente(p: Pasajero): Promise<void> {
  const q = p.numero_documento.trim()
  if (q.length < 5 || p.nombres) return
  try {
    const r = await unwrap(api.GET('/api/v1/admin/clientes', { params: { query: { q, limit: 1 } } }))
    const c = r.items.find((x) => x.numero_documento === q.toUpperCase())
    if (c) {
      p.nombres = c.nombres
      p.apellidos = c.apellidos
      p.fecha_nacimiento = c.fecha_nacimiento ?? ''
      if (p === pasajeros.value[0] && c.telefono_e164 && !comprador.telefono) comprador.telefono = c.telefono_e164
      avisos.info('Cliente encontrado', `${c.nombres} ${c.apellidos}`)
    }
  } catch {
    /* la búsqueda es una ayuda; si falla se completa a mano */
  }
}

const comprador = reactive({ telefono: '', email: '', nit: '', razon: '' })
const venta = ref<Schemas['ReservaOut'] | null>(null)
const cobro = reactive({ metodo: 'efectivo' as 'efectivo' | 'qr' | 'tarjeta_debito', recibido: '', tarjeta: '' })
const cambio = computed(() => {
  const r = Number(cobro.recibido.replace(',', '.'))
  return venta.value && r ? r - venta.value.total_bs : null
})
const finalizada = ref<Schemas['ReservaOut'] | null>(null)

const crear = useMutation({
  mutationFn: () => {
    const primero = pasajeros.value[0]
    return unwrap(
      api.POST('/api/v1/admin/ventas', {
        body: {
          salida_id: salidaId.value!,
          comprador: {
            numero_documento: primero.numero_documento.trim(),
            nombres: primero.nombres.trim(),
            apellidos: primero.apellidos.trim(),
            telefono: comprador.telefono.trim(),
            email: comprador.email.trim() || null,
            nit_facturacion: comprador.nit.trim() || null,
            razon_social_facturacion: comprador.razon.trim() || null,
          },
          pasajeros: pasajeros.value.map((p) => ({
            numero_asiento: p.numero_asiento,
            tipo_pasajero: p.tipo_pasajero,
            numero_documento: p.numero_documento.trim(),
            nombres: p.nombres.trim(),
            apellidos: p.apellidos.trim(),
            fecha_nacimiento: p.fecha_nacimiento || null,
            permiso_viaje_numero: p.permiso_viaje_numero.trim() || null,
            semanas_gestacion: p.tipo_pasajero === 'embarazada' && p.semanas_gestacion ? Number(p.semanas_gestacion) : null,
            viaja_con_perro_guia: p.viaja_con_perro_guia,
          })),
        },
      }),
    )
  },
  onSuccess: (r) => {
    venta.value = r
    cobro.recibido = ''
  },
  onError: (e) => avisos.error('No se pudo crear la venta', e instanceof ApiError ? e.message : undefined),
})

const cobrar = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/admin/ventas/{codigo}/cobrar', {
        params: { path: { codigo: venta.value!.codigo_reserva } },
        body: {
          metodo: cobro.metodo,
          numero_tarjeta: cobro.metodo === 'tarjeta_debito' ? cobro.tarjeta.replace(/\D/g, '') : null,
          nit_facturacion: comprador.nit.trim() || null,
          razon_social_facturacion: comprador.razon.trim() || null,
        },
      }),
    ),
  onSuccess: (r) => {
    finalizada.value = r
    void cliente.invalidateQueries({ queryKey: ['salida', salidaId.value] })
    void cliente.invalidateQueries({ queryKey: ['admin-salidas'] })
    void cliente.invalidateQueries({ queryKey: ['resumen'] })
  },
  onError: (e) => avisos.error('No se pudo cobrar', e instanceof ApiError ? e.message : undefined),
})

const completo = computed(
  () =>
    pasajeros.value.length > 0 &&
    comprador.telefono.trim().length >= 8 &&
    pasajeros.value.every((p) => p.numero_documento.trim().length >= 4 && p.nombres.trim() && p.apellidos.trim()),
)
function accionPrincipal(): void {
  if (finalizada.value) return
  if (venta.value) {
    if (cobro.metodo === 'efectivo' && cambio.value !== null && cambio.value < 0) {
      avisos.error('El monto recibido no alcanza')
      return
    }
    cobrar.mutate()
  } else if (completo.value) crear.mutate()
}
onKeyStroke('F9', (e) => {
  e.preventDefault()
  accionPrincipal()
})

function nuevaVenta(): void {
  finalizada.value = null
  venta.value = null
  seleccion.value = []
  Object.assign(comprador, { telefono: '', email: '', nit: '', razon: '' })
  cobro.tarjeta = ''
}
function imprimir(): void {
  window.print()
}
const salidaActual = computed(() => vendibles.value.find((s) => s.id === salidaId.value))
</script>

<template>
  <div class="flex flex-col gap-5">
    <PageHeader title="Boletería" :subtitle="`Vendedor: ${auth.usuario?.nombres} ${auth.usuario?.apellidos}`">
      <TextInput v-model="fecha" type="date" label="Fecha" class="w-44" :min="hoyISO()" />
    </PageHeader>

    <div class="flex gap-2 overflow-x-auto pb-1" role="group" aria-label="Salidas del día">
      <SkeletonBlock v-if="salidasDelDia.isLoading.value" class="h-16 w-full rounded-xl" />
      <p v-else-if="!vendibles.length" class="text-sm text-muted">No hay salidas a la venta en esta fecha.</p>
      <button
        v-for="s in vendibles"
        :key="s.id"
        type="button"
        class="flex h-16 shrink-0 flex-col items-start justify-center rounded-xl border px-4 text-left transition-colors"
        :class="salidaId === s.id ? 'border-2 border-carmin-600 bg-carmin-50 text-carmin-800 dark:bg-carmin-800/30 dark:text-carmin-100' : 'border-line bg-surface hover:border-noche-400'"
        :aria-pressed="salidaId === s.id"
        @click="salidaId = s.id"
      >
        <strong class="text-sm">{{ hora(s.fecha_hora_salida) }} {{ s.origen }} → {{ s.destino }}</strong>
        <span class="text-xs" :class="s.estado === 'demorada' ? 'font-semibold text-aviso-700' : 'opacity-80'">
          {{ s.estado === 'demorada' ? `Demorada ${s.minutos_demora} min` : s.estado === 'abordando' ? 'Abordando' : 'Programada' }}
          · {{ (s.asientos_total ?? 0) - (s.asientos_ocupados ?? 0) }} libres
        </span>
      </button>
    </div>

    <EmptyState v-if="!salidaId && !salidasDelDia.isLoading.value" title="Elige una salida" text="Cambia la fecha para ver otras salidas." />
    <div v-else class="grid items-start gap-5 xl:grid-cols-[minmax(300px,340px)_1fr_340px]">
      <section class="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-4" aria-label="Mapa de asientos">
        <div class="flex rounded-control bg-surface-2 p-1">
          <button v-for="p in (['alta', 'baja'] as const)" :key="p" type="button" class="h-9 flex-1 rounded-lg text-[13px] font-semibold" :class="planta === p ? 'bg-surface shadow-suave' : 'text-muted'" @click="planta = p">
            {{ p === 'alta' ? 'Alta · Suite' : 'Baja · Leito' }} {{ bs(precios[p === 'alta' ? 'SUITE_CAMA' : 'LEITO_CAMA']?.precio_bs) }}
          </button>
        </div>
        <SkeletonBlock v-if="mapa.isLoading.value" class="h-96" />
        <SeatMap
          v-else
          v-model="seleccion"
          :asientos="(mapa.data.value?.asientos ?? []).filter((a) => a.planta === planta)"
          :maximo="politicas?.boletos_max_por_venta ?? 6"
          :titulo="planta === 'alta' ? 'Planta alta' : 'Planta baja'"
          :horizontal="false"
          compacto
        />
      </section>

      <section class="flex min-w-0 flex-col gap-4" aria-label="Pasajeros">
        <EmptyState v-if="!pasajeros.length" compact title="Selecciona los asientos" text="Toca los asientos en el mapa para agregar pasajeros." />
        <fieldset v-for="(p, i) in pasajeros" :key="p.numero_asiento" class="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-5">
          <legend class="float-left flex w-full items-center justify-between gap-2">
            <span class="flex items-center gap-3 font-bold">
              <span class="flex size-8 items-center justify-center rounded-lg bg-carmin-600 text-sm text-white">{{ p.numero_asiento }}</span>
              Pasajero {{ i + 1 }}<span v-if="i === 0" class="text-sm font-normal text-muted">· comprador</span>
            </span>
            <span class="font-display font-bold tabular">{{ bs(estimado(p)) }}</span>
          </legend>
          <SegmentedControl v-model="p.tipo_pasajero" label="Tarifa" :options="opcionesTarifa" />
          <p v-if="politicaDe(p.tipo_pasajero)?.requisito && p.tipo_pasajero !== 'adulto'" class="rounded-xl bg-aviso-50 px-4 py-2.5 text-[13px] text-aviso-800 dark:bg-aviso-600/15 dark:text-amber-200">
            Requisito: {{ politicaDe(p.tipo_pasajero)?.requisito }}.
          </p>
          <div class="grid gap-3 sm:grid-cols-3">
            <TextInput v-model="p.numero_documento" label="CI" required autocomplete="off" @blur="buscarCliente(p)">
              <template #sufijo><UserSearch class="size-4 text-muted" aria-hidden="true" /></template>
            </TextInput>
            <TextInput v-model="p.nombres" label="Nombres" required />
            <TextInput v-model="p.apellidos" label="Apellidos" required />
          </div>
          <div class="grid gap-3 sm:grid-cols-3">
            <TextInput
              v-if="['menor', 'adulto_mayor'].includes(p.tipo_pasajero)"
              v-model="p.fecha_nacimiento"
              type="date"
              label="Fecha de nacimiento"
              required
              :hint="edad(p.fecha_nacimiento) !== null ? `${edad(p.fecha_nacimiento)} años` : undefined"
            />
            <TextInput v-if="p.tipo_pasajero === 'menor'" v-model="p.permiso_viaje_numero" label="N.º de permiso de viaje" required />
            <TextInput v-if="p.tipo_pasajero === 'embarazada'" v-model="p.semanas_gestacion" type="number" min="1" max="30" label="Semanas de gestación" required />
          </div>
          <CheckboxInput v-model="p.viaja_con_perro_guia" label="Viaja con perro guía" />
        </fieldset>
        <fieldset v-if="pasajeros.length" class="grid gap-3 rounded-2xl border border-line bg-surface p-5 sm:grid-cols-2">
          <legend class="float-left mb-1 w-full font-bold">Contacto y factura</legend>
          <TextInput v-model="comprador.telefono" label="Celular del comprador" type="tel" required />
          <TextInput v-model="comprador.email" label="Correo (opcional)" type="email" />
          <TextInput v-model="comprador.nit" label="NIT / CI factura" />
          <TextInput v-model="comprador.razon" label="Razón social" />
        </fieldset>
      </section>

      <aside class="flex flex-col overflow-hidden rounded-2xl border border-line bg-surface xl:sticky xl:top-20" aria-label="Cobro">
        <div class="bg-noche-900 p-5 text-white">
          <strong class="block">{{ salidaActual ? `${salidaActual.origen} → ${salidaActual.destino} · ${hora(salidaActual.fecha_hora_salida)}` : '—' }}</strong>
          <span class="text-sm text-noche-200">Bus {{ salidaActual?.bus ?? '—' }} · Andén {{ salidaActual?.anden ?? '—' }}</span>
        </div>
        <div class="flex flex-col gap-3 p-5">
          <div v-for="p in pasajeros" :key="p.numero_asiento" class="flex justify-between text-sm">
            <span>Asiento {{ p.numero_asiento }} · {{ opcionesTarifa.find((o) => o.value === p.tipo_pasajero)?.label }}</span>
            <span class="tabular">{{ bs(estimado(p)) }}</span>
          </div>
          <div class="flex items-baseline justify-between border-t border-line pt-3">
            <strong>{{ venta ? 'Total' : 'Total estimado' }}</strong>
            <span class="font-display text-[26px] font-bold tabular">{{ bsExacto(venta?.total_bs ?? totalEstimado) }}</span>
          </div>

          <template v-if="venta">
            <p class="rounded-xl bg-info-50 px-3 py-2 text-[13px] text-info-800 dark:bg-info-600/15 dark:text-blue-200">
              Venta <span class="codigo">{{ venta.codigo_reserva }}</span> creada. Asientos bloqueados hasta cobrar.
            </p>
            <SegmentedControl
              v-model="cobro.metodo"
              label="Método de pago"
              variant="switch"
              :options="[
                { value: 'efectivo', label: 'Efectivo' },
                { value: 'qr', label: 'QR' },
                { value: 'tarjeta_debito', label: 'Tarjeta' },
              ]"
            />
            <template v-if="cobro.metodo === 'efectivo'">
              <TextInput v-model="cobro.recibido" label="Recibido (Bs)" inputmode="decimal" size="lg" />
              <div v-if="cambio !== null" class="flex items-baseline justify-between rounded-xl px-4 py-3" :class="cambio >= 0 ? 'bg-exito-50 text-exito-800' : 'bg-peligro-50 text-peligro-800'">
                <span class="font-semibold">{{ cambio >= 0 ? 'Cambio' : 'Falta' }}</span>
                <strong class="font-display text-xl tabular">{{ bsExacto(Math.abs(cambio)) }}</strong>
              </div>
            </template>
            <TextInput v-else-if="cobro.metodo === 'tarjeta_debito'" v-model="cobro.tarjeta" label="Número de tarjeta (POS)" inputmode="numeric" />
          </template>

          <BaseButton
            size="lg"
            block
            :disabled="!venta && !completo"
            :loading="crear.isPending.value || cobrar.isPending.value"
            @click="accionPrincipal"
          >
            {{ venta ? `Cobrar ${bsExacto(venta.total_bs)}` : 'Crear venta' }} · F9
          </BaseButton>
          <p v-if="!venta && pasajeros.length && !completo" class="text-[13px] text-muted">Completa CI, nombres y el celular del comprador.</p>
        </div>
      </aside>
    </div>

    <AppDialog :open="!!finalizada" title="Venta cobrada" size="xl" @update:open="(v) => !v && nuevaVenta()">
      <div v-if="finalizada" class="flex flex-col gap-4">
        <p class="no-print flex items-center gap-2 font-semibold text-exito-600">
          <CircleCheck class="size-5" aria-hidden="true" />Reserva {{ finalizada.codigo_reserva }} · {{ bsExacto(finalizada.total_bs) }}
          <template v-if="cobro.metodo === 'efectivo' && cambio !== null && cambio > 0"> · Cambio {{ bsExacto(cambio) }}</template>
        </p>
        <TicketCard v-for="b in finalizada.boletos" :key="b.numero_boleto" :boleto="b" :salida="finalizada.salida" />
      </div>
      <template #footer>
        <BaseButton variant="subtle" @click="imprimir"><Printer class="size-4" aria-hidden="true" />Imprimir boletos</BaseButton>
        <BaseButton @click="nuevaVenta"><RotateCcw class="size-4" aria-hidden="true" />Nueva venta</BaseButton>
      </template>
    </AppDialog>
  </div>
</template>
