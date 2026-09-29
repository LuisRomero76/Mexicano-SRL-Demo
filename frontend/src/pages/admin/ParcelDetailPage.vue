<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ArrowRight, Banknote, Bus, HandHelping, Printer, Route, Truck } from '@lucide/vue'
import { computed, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ApiError, api, unwrap, type Schemas } from '@/api/client'
import ParcelLabel from '@/components/cargo/ParcelLabel.vue'
import TrackingTimeline from '@/components/tracking/TrackingTimeline.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import CheckboxInput from '@/components/ui/CheckboxInput.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SelectInput from '@/components/ui/SelectInput.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import SurfaceCard from '@/components/ui/SurfaceCard.vue'
import TextArea from '@/components/ui/TextArea.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { bsExacto, fechaHora, hoyISO, hora, sumarDias, telefono } from '@/lib/format'
import { ESTADO_ENCOMIENDA, ESTADO_PAGO, ESTADO_SALIDA, METODO_PAGO, TIPO_ENVIO, TRANSICIONES_ENCOMIENDA, etiqueta } from '@/lib/labels'
import { ACCESO } from '@/lib/roles'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

type Encomienda = Schemas['EncomiendaOut']
type Metodo = Schemas['MetodoPago']

const route = useRoute()
const auth = useAuthStore()
const avisos = useToastStore()
const cliente = useQueryClient()
const guia = computed(() => String(route.params.guia))
const esBodega = computed(() => auth.puede(ACCESO.encomiendasRegistrar))

const detalle = useQuery({
  queryKey: computed(() => ['admin-encomienda', guia.value]),
  queryFn: () => unwrap(api.GET('/api/v1/admin/encomiendas/{numero_guia}', { params: { path: { numero_guia: guia.value } } })),
})
const e = computed(() => detalle.data.value)
const salida = useQuery({
  queryKey: computed(() => ['admin-salida', e.value?.salida_id]),
  queryFn: () => unwrap(api.GET('/api/v1/admin/salidas/{salida_id}', { params: { path: { salida_id: e.value!.salida_id! } } })),
  enabled: computed(() => !!e.value?.salida_id),
})
const vehiculos = useQuery({
  queryKey: ['vehiculos-carga'],
  queryFn: () => unwrap(api.GET('/api/v1/admin/vehiculos-carga', { params: { query: { limit: 100 } } })),
  enabled: esBodega,
})
const vehiculoAsignado = computed(() => vehiculos.data.value?.items.find((v) => v.id === e.value?.vehiculo_carga_id))

function actualizado(r: Encomienda, mensaje: string): void {
  cliente.setQueryData(['admin-encomienda', guia.value], r)
  void cliente.invalidateQueries({ queryKey: ['admin-encomiendas'] })
  avisos.exito(mensaje)
  dialogo.value = null
}
const fallo = (titulo: string) => (err: Error) => avisos.error(titulo, err instanceof ApiError ? err.message : undefined)

type Dialogo = 'evento' | 'despachar' | 'vehiculo' | 'cobrar' | 'entregar' | 'comprobante'
const dialogo = ref<Dialogo | null>(null)

// --- Evento de rastreo ---
const siguientes = computed(() => {
  const x = e.value
  if (!x) return []
  return (TRANSICIONES_ENCOMIENDA[x.estado] ?? []).filter((s) => {
    if (s === 'en_reparto') return x.modalidad_entrega === 'puerta_a_puerta'
    if (s === 'en_transito') return x.tipo_envio === 'carga' || !!x.salida_id
    if (s === 'cancelada' || s === 'devuelta') return esBodega.value
    return true
  })
})
const evento = reactive({ estado: '', descripcion: '', visible: true })
function abrirEvento(estado?: string): void {
  evento.estado = estado ?? siguientes.value[0] ?? ''
  evento.descripcion = ''
  evento.visible = true
  dialogo.value = 'evento'
}
const registrarEvento = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/admin/encomiendas/{numero_guia}/eventos', {
        params: { path: { numero_guia: guia.value } },
        body: {
          estado: evento.estado as Schemas['EstadoEncomienda'],
          descripcion: evento.descripcion.trim() || null,
          visible_cliente: evento.visible,
        },
      }),
    ),
  onSuccess: (r) => actualizado(r, `Estado: ${etiqueta(ESTADO_ENCOMIENDA, r.estado).label}`),
  onError: fallo('No se pudo registrar el evento'),
})

// --- Despacho en bus ---
const fechaDespacho = ref(hoyISO())
const salidaElegida = ref<string | null>(null)
const salidas = useQuery({
  queryKey: computed(() => ['admin-salidas-despacho', fechaDespacho.value]),
  queryFn: () => unwrap(api.GET('/api/v1/admin/salidas', { params: { query: { fecha: fechaDespacho.value, limit: 100 } } })),
  enabled: computed(() => dialogo.value === 'despachar'),
})
const opcionesSalida = computed(() => {
  const x = e.value
  const vendibles = (salidas.data.value?.items ?? []).filter((s) => ['programada', 'abordando', 'demorada'].includes(s.estado))
  // Primero las salidas que parten de la ciudad de origen de la encomienda.
  vendibles.sort((a, b) => Number(b.origen === x?.ciudad_origen) - Number(a.origen === x?.ciudad_origen) || a.fecha_hora_salida.localeCompare(b.fecha_hora_salida))
  return vendibles.map((s) => ({
    value: s.id,
    label: `${hora(s.fecha_hora_salida)} · ${s.origen} → ${s.destino} · ${s.codigo}${s.bus ? ` · bus ${s.bus}` : ''}`,
  }))
})
const despachar = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/admin/encomiendas/{numero_guia}/despachar', {
        params: { path: { numero_guia: guia.value } },
        body: { salida_id: salidaElegida.value! },
      }),
    ),
  onSuccess: (r) => {
    actualizado(r, 'Encomienda asignada a la salida')
    void cliente.invalidateQueries({ queryKey: ['admin-salida'] })
  },
  onError: fallo('No se pudo despachar'),
})

// --- Carga en furgón ---
const vehiculoElegido = ref<number | null>(null)
const opcionesVehiculo = computed(() =>
  (vehiculos.data.value?.items ?? [])
    .filter((v) => v.activo && v.capacidad_kg >= (e.value?.peso_kg ?? 0))
    .map((v) => ({ value: v.id, label: `${v.placa} · ${v.tipo} · hasta ${v.capacidad_kg} kg` })),
)
const asignarVehiculo = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/admin/encomiendas/{numero_guia}/vehiculo', {
        params: { path: { numero_guia: guia.value } },
        body: { vehiculo_id: vehiculoElegido.value! },
      }),
    ),
  onSuccess: (r) => actualizado(r, 'Carga despachada en furgón'),
  onError: fallo('No se pudo asignar el vehículo'),
})

// --- Cobro y entrega ---
const METODOS: { value: Metodo; label: string }[] = [
  { value: 'efectivo', label: 'Efectivo' },
  { value: 'qr', label: 'QR' },
  { value: 'tarjeta_debito', label: 'Tarjeta de débito' },
  { value: 'tarjeta_credito', label: 'Tarjeta de crédito' },
]
const metodoCobro = ref<Metodo>('efectivo')
const cobrar = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/admin/encomiendas/{numero_guia}/cobrar', {
        params: { path: { numero_guia: guia.value } },
        body: { metodo: metodoCobro.value },
      }),
    ),
  onSuccess: (r) => actualizado(r, `Cobrado ${bsExacto(r.precio_bs)}`),
  onError: fallo('No se pudo cobrar'),
})

const entrega = reactive({ pin: '', nombre: '', documento: '', metodo: 'efectivo' as Metodo })
const erroresEntrega = ref<Record<string, string>>({})
function abrirEntrega(): void {
  Object.assign(entrega, { pin: '', nombre: e.value?.destinatario_nombre ?? '', documento: '', metodo: 'efectivo' })
  erroresEntrega.value = {}
  dialogo.value = 'entregar'
}
const entregar = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/admin/encomiendas/{numero_guia}/entregar', {
        params: { path: { numero_guia: guia.value } },
        body: {
          codigo_retiro: entrega.pin,
          recibido_por_nombre: entrega.nombre.trim(),
          recibido_por_documento: entrega.documento.trim(),
          metodo_pago: e.value?.estado_pago === 'pendiente' ? entrega.metodo : null,
        },
      }),
    ),
  onSuccess: (r) => actualizado(r, 'Encomienda entregada'),
  onError: (err) => {
    if (err instanceof ApiError && err.code === 'codigo_retiro_incorrecto') erroresEntrega.value = { pin: err.message }
    else fallo('No se pudo entregar')(err)
  },
})
function confirmarEntrega(): void {
  const errores: Record<string, string> = {}
  if (!/^\d{4}$/.test(entrega.pin)) errores.pin = 'El código tiene 4 dígitos'
  if (entrega.nombre.trim().length < 3) errores.nombre = 'Nombre de quien recibe'
  if (entrega.documento.trim().length < 4) errores.documento = 'Documento de quien recibe'
  erroresEntrega.value = errores
  if (!Object.keys(errores).length) entregar.mutate()
}

const puedeDespachar = computed(() => esBodega.value && e.value?.estado === 'recibida_en_origen')
const puedeEntregar = computed(() => ['lista_para_retiro', 'en_reparto'].includes(e.value?.estado ?? ''))
const cerrada = computed(() => ['entregada', 'devuelta', 'cancelada'].includes(e.value?.estado ?? ''))
function imprimir(): void {
  window.print()
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader :title="`Guía ${guia}`" :crumbs="[{ label: 'Encomiendas', to: { name: 'admin-encomiendas' } }, { label: guia }]">
      <template #meta>
        <div v-if="e" class="mt-2 flex flex-wrap items-center gap-2">
          <StatusBadge v-bind="etiqueta(ESTADO_ENCOMIENDA, e.estado)" />
          <StatusBadge v-bind="etiqueta(ESTADO_PAGO, e.estado_pago)" :label="`Pago: ${etiqueta(ESTADO_PAGO, e.estado_pago).label.toLowerCase()}`" />
          <span class="text-sm text-muted">Registrada {{ fechaHora(e.fecha_registro) }}</span>
        </div>
      </template>
      <BaseButton v-if="e" variant="subtle" size="sm" class="h-10" @click="dialogo = 'comprobante'"><Printer class="size-4" aria-hidden="true" />Comprobante</BaseButton>
    </PageHeader>

    <SkeletonBlock v-if="detalle.isLoading.value" class="h-96" />
    <ErrorState v-else-if="detalle.isError.value" :error="detalle.error.value" @retry="detalle.refetch()" />
    <div v-else-if="e" class="grid items-start gap-6 lg:grid-cols-[1fr_380px]">
      <div class="flex min-w-0 flex-col gap-6">
        <SurfaceCard>
          <div class="flex flex-col gap-5">
            <div class="flex flex-wrap items-center gap-3 text-lg font-bold">
              <span>{{ e.ciudad_origen ?? e.oficina_origen }}</span>
              <ArrowRight class="size-5 text-carmin-600" aria-hidden="true" />
              <span>{{ e.ciudad_destino ?? e.oficina_destino }}</span>
              <span class="rounded-full bg-surface-2 px-2.5 py-1 text-xs font-semibold">{{ TIPO_ENVIO[e.tipo_envio] }}</span>
              <span v-if="e.es_fragil" class="rounded-full bg-aviso-50 px-2.5 py-1 text-xs font-semibold text-aviso-800">Frágil</span>
              <span v-if="e.es_mudanza" class="rounded-full bg-info-50 px-2.5 py-1 text-xs font-semibold text-info-800">Mudanza</span>
            </div>
            <dl class="grid gap-x-6 gap-y-4 text-sm sm:grid-cols-2 xl:grid-cols-3">
              <div><dt class="text-muted">Remitente</dt><dd class="font-semibold">{{ e.remitente }}</dd></div>
              <div>
                <dt class="text-muted">Destinatario</dt>
                <dd class="font-semibold">{{ e.destinatario_nombre }}</dd>
                <dd><a :href="`tel:${e.destinatario_telefono_e164}`" class="text-carmin-600 hover:underline dark:text-carmin-200">{{ telefono(e.destinatario_telefono_e164) }}</a></dd>
              </div>
              <div><dt class="text-muted">Contenido</dt><dd>{{ e.descripcion_contenido }}</dd></div>
              <div><dt class="text-muted">Bodega de origen</dt><dd>{{ e.oficina_origen }}</dd></div>
              <div>
                <dt class="text-muted">Entrega</dt>
                <dd v-if="e.modalidad_entrega === 'puerta_a_puerta'">A domicilio: {{ e.direccion_entrega }}<span v-if="e.referencia_entrega" class="block text-muted">{{ e.referencia_entrega }}</span></dd>
                <dd v-else>Retiro en {{ e.oficina_destino }}</dd>
              </div>
              <div><dt class="text-muted">Peso y bultos</dt><dd>{{ e.peso_kg }} kg · {{ e.cantidad_bultos }} bulto(s)</dd></div>
              <div>
                <dt class="text-muted">Precio</dt>
                <dd class="font-semibold">{{ bsExacto(e.precio_bs) }}</dd>
                <dd class="text-muted">{{ e.pago_en === 'destino' ? 'Paga el destinatario' : e.pago_en === 'credito_corporativo' ? 'Crédito corporativo' : 'Pagado en origen' }}</dd>
              </div>
              <div v-if="e.valor_declarado_bs"><dt class="text-muted">Valor declarado</dt><dd>{{ bsExacto(e.valor_declarado_bs) }}</dd></div>
              <div v-if="e.fecha_estimada_entrega"><dt class="text-muted">Llegada estimada</dt><dd>{{ fechaHora(e.fecha_estimada_entrega) }}</dd></div>
              <div v-if="e.fecha_entrega"><dt class="text-muted">Entregada</dt><dd>{{ fechaHora(e.fecha_entrega) }} a {{ e.entregado_a_nombre }}</dd></div>
            </dl>
          </div>
        </SurfaceCard>

        <SurfaceCard title="Transporte">
          <div v-if="e.salida_id" class="flex flex-wrap items-center gap-3 text-sm">
            <Bus class="size-5 text-noche-500" aria-hidden="true" />
            <template v-if="salida.data.value">
              <RouterLink :to="{ name: 'admin-salida', params: { id: e.salida_id } }" class="font-semibold hover:underline">
                {{ salida.data.value.codigo }} · {{ salida.data.value.origen }} → {{ salida.data.value.destino }}
              </RouterLink>
              <span class="text-muted">{{ fechaHora(salida.data.value.fecha_hora_salida) }}{{ salida.data.value.bus ? ` · bus ${salida.data.value.bus}` : '' }}</span>
              <StatusBadge size="sm" v-bind="etiqueta(ESTADO_SALIDA, salida.data.value.estado)" />
            </template>
            <SkeletonBlock v-else class="h-5 w-64" />
          </div>
          <div v-else-if="e.vehiculo_carga_id" class="flex items-center gap-3 text-sm">
            <Truck class="size-5 text-noche-500" aria-hidden="true" />
            <span class="font-semibold">Furgón {{ vehiculoAsignado?.placa ?? `#${e.vehiculo_carga_id}` }}</span>
            <span class="text-muted">con GPS</span>
          </div>
          <p v-else class="text-sm text-muted">
            Aún no tiene transporte asignado.
            <template v-if="e.estado === 'registrada'">Márcala como recibida en origen para despacharla.</template>
          </p>
        </SurfaceCard>

        <SurfaceCard title="Historial de rastreo" subtitle="Lo que ve el cliente al rastrear la guía.">
          <TrackingTimeline v-if="e.eventos.length" :eventos="[...e.eventos].reverse()" />
          <EmptyState v-else compact title="Sin eventos" text="Aún no hay movimientos registrados." />
        </SurfaceCard>
      </div>

      <aside class="flex flex-col gap-4 lg:sticky lg:top-20">
        <SurfaceCard title="Acciones">
          <div class="flex flex-col gap-2.5">
            <p v-if="cerrada" class="text-sm text-muted">Esta encomienda ya está cerrada.</p>
            <BaseButton v-if="puedeEntregar" variant="success" block @click="abrirEntrega"><HandHelping class="size-4" aria-hidden="true" />Entregar al destinatario</BaseButton>
            <BaseButton v-if="puedeDespachar && e.tipo_envio !== 'carga'" block @click="dialogo = 'despachar'"><Bus class="size-4" aria-hidden="true" />Asignar a un bus</BaseButton>
            <BaseButton v-if="puedeDespachar && e.tipo_envio === 'carga'" block @click="dialogo = 'vehiculo'"><Truck class="size-4" aria-hidden="true" />Despachar en furgón</BaseButton>
            <BaseButton v-if="e.estado_pago === 'pendiente' && !puedeEntregar && !cerrada" variant="secondary" block @click="dialogo = 'cobrar'">
              <Banknote class="size-4" aria-hidden="true" />Cobrar {{ bsExacto(e.precio_bs) }}
            </BaseButton>
            <template v-if="siguientes.length">
              <p class="mt-2 text-xs font-semibold tracking-wide text-muted uppercase">Actualizar estado</p>
              <button
                v-for="s in siguientes"
                :key="s"
                type="button"
                class="flex min-h-11 items-center justify-between gap-2 rounded-control border border-line px-3.5 text-left text-sm font-medium transition-colors hover:border-noche-400 hover:bg-surface-2"
                @click="abrirEvento(s)"
              >
                <span class="flex items-center gap-2"><Route class="size-4 text-muted" aria-hidden="true" />{{ etiqueta(ESTADO_ENCOMIENDA, s).label }}</span>
                <ArrowRight class="size-4 text-muted" aria-hidden="true" />
              </button>
            </template>
            <p v-if="puedeDespachar && e.tipo_envio !== 'carga' && !e.salida_id" class="text-xs text-muted">Para pasar a «En tránsito» primero asígnala a un bus.</p>
          </div>
        </SurfaceCard>
        <SurfaceCard v-if="e.codigo_retiro && !cerrada" title="Código de retiro">
          <p class="codigo text-3xl text-carmin-600">{{ e.codigo_retiro }}</p>
          <p class="mt-1 text-xs text-muted">Solo se comparte con el remitente. Pídeselo al destinatario al entregar.</p>
        </SurfaceCard>
      </aside>
    </div>

    <!-- Evento -->
    <AppDialog :open="dialogo === 'evento'" title="Actualizar estado" :description="`Guía ${guia}`" @update:open="(v) => !v && (dialogo = null)">
      <div class="flex flex-col gap-4">
        <SelectInput v-model="evento.estado" label="Nuevo estado" :options="siguientes.map((s) => ({ value: s, label: etiqueta(ESTADO_ENCOMIENDA, s).label }))" />
        <TextArea v-model="evento.descripcion" label="Detalle (opcional)" hint="Si lo dejas vacío se genera un texto claro para el cliente." :rows="2" maxlength="250" />
        <CheckboxInput v-model="evento.visible" label="Visible para el cliente en el rastreo" />
      </div>
      <template #footer>
        <BaseButton variant="subtle" @click="dialogo = null">Cancelar</BaseButton>
        <BaseButton :variant="['cancelada', 'devuelta'].includes(evento.estado) ? 'danger' : 'primary'" :loading="registrarEvento.isPending.value" :disabled="!evento.estado" @click="registrarEvento.mutate()">
          Guardar
        </BaseButton>
      </template>
    </AppDialog>

    <!-- Despacho en bus -->
    <AppDialog :open="dialogo === 'despachar'" title="Asignar a un bus" description="La encomienda viaja en la bodega del bus elegido." @update:open="(v) => !v && (dialogo = null)">
      <div class="flex flex-col gap-4">
        <SelectInput
          v-model="fechaDespacho"
          label="Fecha"
          :options="[0, 1, 2].map((d) => ({ value: sumarDias(hoyISO(), d), label: d === 0 ? 'Hoy' : d === 1 ? 'Mañana' : 'Pasado mañana' }))"
        />
        <SkeletonBlock v-if="salidas.isLoading.value" class="h-11" />
        <SelectInput v-else v-model="salidaElegida" label="Salida" placeholder="Elige la salida" :options="opcionesSalida" :hint="opcionesSalida.length ? undefined : 'No hay salidas disponibles ese día.'" />
      </div>
      <template #footer>
        <BaseButton variant="subtle" @click="dialogo = null">Cancelar</BaseButton>
        <BaseButton :disabled="!salidaElegida" :loading="despachar.isPending.value" @click="despachar.mutate()">Asignar</BaseButton>
      </template>
    </AppDialog>

    <!-- Furgón -->
    <AppDialog :open="dialogo === 'vehiculo'" title="Despachar en furgón" :description="`Carga de ${e?.peso_kg ?? ''} kg: viaja en un vehículo con GPS.`" @update:open="(v) => !v && (dialogo = null)">
      <SelectInput v-model="vehiculoElegido" label="Vehículo" placeholder="Elige el vehículo" :options="opcionesVehiculo" :hint="opcionesVehiculo.length ? undefined : 'Ningún vehículo activo tiene capacidad suficiente.'" />
      <template #footer>
        <BaseButton variant="subtle" @click="dialogo = null">Cancelar</BaseButton>
        <BaseButton :disabled="!vehiculoElegido" :loading="asignarVehiculo.isPending.value" @click="asignarVehiculo.mutate()">Despachar</BaseButton>
      </template>
    </AppDialog>

    <!-- Cobro -->
    <AppDialog :open="dialogo === 'cobrar'" title="Cobrar encomienda" :description="e ? `${bsExacto(e.precio_bs)} pendientes` : ''" size="sm" @update:open="(v) => !v && (dialogo = null)">
      <SelectInput v-model="metodoCobro" label="Método de pago" :options="METODOS" />
      <template #footer>
        <BaseButton variant="subtle" @click="dialogo = null">Cancelar</BaseButton>
        <BaseButton :loading="cobrar.isPending.value" @click="cobrar.mutate()">Cobrar</BaseButton>
      </template>
    </AppDialog>

    <!-- Entrega -->
    <AppDialog :open="dialogo === 'entregar'" title="Entregar encomienda" description="Verifica el documento de quien recibe y pide el código de retiro de 4 dígitos." @update:open="(v) => !v && (dialogo = null)">
      <form id="form-entrega" class="flex flex-col gap-4" novalidate @submit.prevent="confirmarEntrega">
        <TextInput v-model="entrega.pin" label="Código de retiro" inputmode="numeric" maxlength="4" mono size="lg" autocomplete="off" required :error="erroresEntrega.pin" />
        <div class="grid gap-3 sm:grid-cols-2">
          <TextInput v-model="entrega.nombre" label="Recibe" required :error="erroresEntrega.nombre" />
          <TextInput v-model="entrega.documento" label="Documento de quien recibe" required :error="erroresEntrega.documento" />
        </div>
        <div v-if="e?.estado_pago === 'pendiente'" class="flex flex-col gap-3 rounded-xl bg-aviso-50 p-4 text-aviso-800 dark:bg-aviso-600/15 dark:text-amber-200">
          <p class="text-sm font-semibold">Cobrar {{ bsExacto(e.precio_bs) }} antes de entregar</p>
          <SelectInput v-model="entrega.metodo" label="Método de pago" :options="METODOS" />
        </div>
      </form>
      <template #footer>
        <BaseButton variant="subtle" @click="dialogo = null">Cancelar</BaseButton>
        <BaseButton type="submit" form="form-entrega" variant="success" :loading="entregar.isPending.value">
          {{ e?.estado_pago === 'pendiente' ? `Cobrar y entregar (${METODO_PAGO[entrega.metodo]})` : 'Confirmar entrega' }}
        </BaseButton>
      </template>
    </AppDialog>

    <!-- Comprobante -->
    <AppDialog :open="dialogo === 'comprobante'" title="Comprobante de envío" size="lg" @update:open="(v) => !v && (dialogo = null)">
      <ParcelLabel v-if="e" :encomienda="e" />
      <template #footer>
        <BaseButton variant="subtle" @click="dialogo = null">Cerrar</BaseButton>
        <BaseButton @click="imprimir"><Printer class="size-4" aria-hidden="true" />Imprimir</BaseButton>
      </template>
    </AppDialog>
  </div>
</template>
