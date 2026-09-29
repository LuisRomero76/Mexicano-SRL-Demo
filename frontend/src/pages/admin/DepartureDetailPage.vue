<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ArrowRight, Bus, Pencil, Printer, Tag, Users } from '@lucide/vue'
import { computed, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ApiError, api, unwrap } from '@/api/client'
import { useTiposAsiento } from '@/api/queries'
import AppDialog from '@/components/ui/AppDialog.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import DataTable from '@/components/ui/DataTable.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SelectInput from '@/components/ui/SelectInput.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import TabsBar from '@/components/ui/TabsBar.vue'
import TextArea from '@/components/ui/TextArea.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { bs, fechaHora, fechaLarga, hora } from '@/lib/format'
import { ESTADO_BOLETO, ESTADO_ENCOMIENDA, ESTADO_SALIDA, TIPO_ENVIO, TIPO_PASAJERO, TRANSICIONES_SALIDA, etiqueta } from '@/lib/labels'
import { ACCESO } from '@/lib/roles'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const auth = useAuthStore()
const avisos = useToastStore()
const cliente = useQueryClient()
const id = computed(() => String(route.params.id))
const puedeOperar = computed(() => auth.puede(ACCESO.salidasOperar))

const manifiesto = useQuery({
  queryKey: computed(() => ['manifiesto', id.value]),
  queryFn: () => unwrap(api.GET('/api/v1/admin/salidas/{salida_id}/manifiesto', { params: { path: { salida_id: id.value } } })),
  refetchInterval: 30_000,
})
const detalle = useQuery({
  queryKey: computed(() => ['admin-salida', id.value]),
  queryFn: () => unwrap(api.GET('/api/v1/admin/salidas/{salida_id}', { params: { path: { salida_id: id.value } } })),
})
const precios = useQuery({
  queryKey: computed(() => ['salida', id.value]),
  queryFn: () => unwrap(api.GET('/api/v1/salidas/{salida_id}', { params: { path: { salida_id: id.value } } })),
  retry: false,
})
const buses = useQuery({
  queryKey: ['admin-buses'],
  queryFn: () => unwrap(api.GET('/api/v1/admin/buses')),
  enabled: puedeOperar,
})
const conductores = useQuery({
  queryKey: ['directorio', 'conductor'],
  queryFn: () => unwrap(api.GET('/api/v1/admin/usuarios/directorio', { params: { query: { rol: 'conductor' } } })),
  enabled: puedeOperar,
})

const s = computed(() => detalle.data.value ?? manifiesto.data.value?.salida)
const estado = computed(() => {
  const e = etiqueta(ESTADO_SALIDA, s.value?.estado)
  return s.value?.estado === 'demorada' ? { ...e, label: `Demorada ${s.value.minutos_demora} min` } : e
})
const posibles = computed(() => TRANSICIONES_SALIDA[s.value?.estado ?? ''] ?? [])
const abordados = computed(() => (manifiesto.data.value?.pasajeros ?? []).filter((p) => p.estado === 'abordado').length)

function refrescar(): void {
  void cliente.invalidateQueries({ queryKey: ['manifiesto', id.value] })
  void cliente.invalidateQueries({ queryKey: ['admin-salida', id.value] })
  void cliente.invalidateQueries({ queryKey: ['salida', id.value] })
  void cliente.invalidateQueries({ queryKey: ['admin-salidas'] })
  void cliente.invalidateQueries({ queryKey: ['resumen'] })
}
const alFallar = (titulo: string) => (e: unknown) => avisos.error(titulo, e instanceof ApiError ? e.message : undefined)

// --- Estado ---
const dialogoEstado = ref<null | 'demorada' | 'cancelada'>(null)
const formEstado = reactive({ minutos: 30, motivo: '' })
const cambiarEstado = useMutation({
  mutationFn: (nuevo: string) =>
    unwrap(
      api.POST('/api/v1/admin/salidas/{salida_id}/estado', {
        params: { path: { salida_id: id.value } },
        body: {
          estado: nuevo as never,
          minutos_demora: nuevo === 'demorada' ? Number(formEstado.minutos) : null,
          motivo: formEstado.motivo.trim() || null,
        },
      }),
    ),
  onSuccess: (r) => {
    dialogoEstado.value = null
    formEstado.motivo = ''
    avisos.exito(`Salida ${etiqueta(ESTADO_SALIDA, r.estado).label.toLowerCase()}`)
    refrescar()
  },
  onError: alFallar('No se pudo cambiar el estado'),
})
const accionesEstado: Record<string, { label: string; variante: 'primary' | 'secondary' | 'outline' | 'subtle' | 'danger' }> = {
  abordando: { label: 'Iniciar abordaje', variante: 'outline' },
  en_ruta: { label: 'Marcar en ruta', variante: 'secondary' },
  llegada: { label: 'Registrar llegada', variante: 'secondary' },
  demorada: { label: 'Registrar demora', variante: 'subtle' },
  cancelada: { label: 'Cancelar salida', variante: 'danger' },
}
function accion(estadoNuevo: string): void {
  if (estadoNuevo === 'demorada' || estadoNuevo === 'cancelada') {
    formEstado.minutos = s.value?.minutos_demora || 30
    dialogoEstado.value = estadoNuevo
  } else cambiarEstado.mutate(estadoNuevo)
}

// --- Bus ---
const dialogoBus = ref(false)
const busElegido = ref<number | null>(null)
const opcionesBus = computed(() =>
  (buses.data.value ?? [])
    .filter((b) => b.activo)
    .map((b) => ({ value: b.id, label: `${b.numero_interno} · ${b.placa} · ${b.marca ?? ''}${b.estado !== 'operativo' ? ` (${b.estado})` : ''}`, disabled: b.estado !== 'operativo' })),
)
const cambiarBus = useMutation({
  mutationFn: () => unwrap(api.PUT('/api/v1/admin/salidas/{salida_id}/bus', { params: { path: { salida_id: id.value } }, body: { bus_id: busElegido.value! } })),
  onSuccess: (r) => {
    dialogoBus.value = false
    avisos.exito(`Bus ${r.bus} asignado`, 'Los pasajeros conservan sus asientos.')
    refrescar()
  },
  onError: alFallar('No se pudo cambiar el bus'),
})

// --- Tripulación ---
const dialogoTripulacion = ref(false)
const tripulacion = reactive({ conductor: null as string | null, relevo: null as string | null })
function abrirTripulacion(): void {
  const t = manifiesto.data.value?.tripulacion ?? []
  tripulacion.conductor = t.find((m) => m.rol === 'conductor')?.usuario_id ?? null
  tripulacion.relevo = t.find((m) => m.rol === 'conductor_relevo')?.usuario_id ?? null
  dialogoTripulacion.value = true
}
const opcionesConductor = computed(() => [
  { value: null, label: 'Sin asignar' },
  ...(conductores.data.value ?? []).map((c) => ({ value: c.id, label: `${c.nombre}${c.licencia_conducir ? ` · ${c.licencia_conducir}` : ''}` })),
])
const guardarTripulacion = useMutation({
  mutationFn: () =>
    unwrap(
      api.PUT('/api/v1/admin/salidas/{salida_id}/tripulacion', {
        params: { path: { salida_id: id.value } },
        body: {
          miembros: [
            ...(tripulacion.conductor ? [{ usuario_id: tripulacion.conductor, rol: 'conductor' as const }] : []),
            ...(tripulacion.relevo ? [{ usuario_id: tripulacion.relevo, rol: 'conductor_relevo' as const }] : []),
          ],
        },
      }),
    ),
  onSuccess: () => {
    dialogoTripulacion.value = false
    avisos.exito('Tripulación actualizada')
    refrescar()
  },
  onError: alFallar('No se pudo asignar la tripulación'),
})

// --- Precios especiales ---
const dialogoPrecios = ref(false)
const nuevosPrecios = ref<Record<string, string>>({})
const { data: tipos } = useTiposAsiento()
const idTipo = (codigo: string) => tipos.value?.find((t) => t.codigo === codigo)?.id ?? 0
function abrirPrecios(): void {
  nuevosPrecios.value = Object.fromEntries((precios.data.value?.precios ?? []).map((p) => [p.tipo_asiento, String(p.precio_bs)]))
  dialogoPrecios.value = true
}
const guardarPrecios = useMutation({
  mutationFn: () =>
    unwrap(
      api.PUT('/api/v1/admin/salidas/{salida_id}/precios', {
        params: { path: { salida_id: id.value } },
        body: Object.entries(nuevosPrecios.value).map(([codigo, precio]) => ({
          tipo_asiento_id: idTipo(codigo),
          precio_bs: precio.replace(',', '.'),
        })),
      }),
    ),
  onSuccess: () => {
    dialogoPrecios.value = false
    avisos.exito('Precios actualizados')
    refrescar()
  },
  onError: alFallar('No se pudieron guardar los precios'),
})

const pestana = ref('pasajeros')
const pestanas = computed(() => [
  { key: 'pasajeros', label: 'Manifiesto', count: manifiesto.data.value?.total_pasajeros ?? null },
  { key: 'encomiendas', label: 'Encomiendas', count: manifiesto.data.value?.encomiendas.length ?? null },
  { key: 'precios', label: 'Precios' },
])
const colPasajeros = [
  { key: 'numero_asiento', label: 'Asiento' },
  { key: 'pasajero', label: 'Pasajero' },
  { key: 'documento', label: 'Documento', hideSm: true },
  { key: 'tipo_pasajero', label: 'Tarifa', hideSm: true },
  { key: 'numero_boleto', label: 'Boleto', hideSm: true },
  { key: 'equipaje_kg', label: 'Equipaje', align: 'right' as const },
  { key: 'estado', label: 'Estado' },
]
const colEncomiendas = [
  { key: 'numero_guia', label: 'Guía' },
  { key: 'tipo_envio', label: 'Tipo' },
  { key: 'bultos', label: 'Bultos', align: 'right' as const },
  { key: 'peso_kg', label: 'Peso', align: 'right' as const },
  { key: 'destino', label: 'Destino' },
  { key: 'estado', label: 'Estado' },
]
function imprimir(): void {
  window.print()
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <ErrorState v-if="detalle.isError.value" :error="detalle.error.value" @retry="detalle.refetch()" />
    <template v-else>
      <PageHeader
        :title="s ? `${s.origen} → ${s.destino} · ${hora(s.fecha_hora_salida)}` : 'Salida'"
        :crumbs="[{ label: 'Salidas', to: { name: 'admin-salidas' } }, { label: s?.codigo ?? '…' }]"
      >
        <template #meta>
          <div v-if="s" class="mt-2 flex flex-wrap items-center gap-3 text-sm text-muted">
            <StatusBadge :tono="estado.tono" :label="estado.label" />
            <span>{{ fechaLarga(s.fecha_hora_salida) }}</span>
            <span>Llegada estimada {{ hora(s.fecha_hora_llegada_estimada) }}</span>
            <span v-if="s.motivo_estado">· {{ s.motivo_estado }}</span>
          </div>
        </template>
        <template v-if="puedeOperar">
          <BaseButton
            v-for="e in posibles"
            :key="e"
            :variant="accionesEstado[e]?.variante ?? 'subtle'"
            size="sm"
            class="h-10"
            :loading="cambiarEstado.isPending.value && cambiarEstado.variables.value === e"
            @click="accion(e)"
          >
            {{ e === 'demorada' && s?.estado === 'demorada' ? 'Actualizar demora' : accionesEstado[e]?.label }}
          </BaseButton>
        </template>
      </PageHeader>

      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div class="flex flex-col gap-1 rounded-2xl border border-line bg-surface p-5">
          <span class="text-[13px] text-muted">Ocupación</span>
          <SkeletonBlock v-if="!s" class="h-7 w-24" />
          <strong v-else class="font-display text-2xl">{{ s.asientos_ocupados ?? '—' }} / {{ s.asientos_total ?? '—' }}</strong>
          <span class="text-[13px] text-muted">{{ abordados }} abordaron</span>
        </div>
        <div class="flex flex-col gap-1 rounded-2xl border border-line bg-surface p-5">
          <span class="flex items-center gap-1.5 text-[13px] text-muted"><Bus class="size-4" aria-hidden="true" />Bus · andén</span>
          <strong class="font-display text-2xl">{{ s?.bus ?? 'Sin bus' }}<template v-if="s?.anden"> · {{ s.anden }}</template></strong>
          <button v-if="puedeOperar && ['programada', 'demorada', 'abordando'].includes(s?.estado ?? '')" class="self-start text-[13px] font-semibold text-carmin-600 hover:underline dark:text-carmin-200" @click="busElegido = null; dialogoBus = true">
            Cambiar bus
          </button>
        </div>
        <div class="flex flex-col gap-1 rounded-2xl border border-line bg-surface p-5">
          <span class="flex items-center gap-1.5 text-[13px] text-muted"><Users class="size-4" aria-hidden="true" />Tripulación</span>
          <template v-if="manifiesto.data.value?.tripulacion.length">
            <span v-for="t in manifiesto.data.value.tripulacion" :key="t.usuario_id" class="text-sm">
              <strong>{{ t.nombre }}</strong> <span class="text-muted">· {{ t.rol === 'conductor' ? 'conductor' : t.rol === 'conductor_relevo' ? 'relevo' : 'ayudante' }}</span>
            </span>
          </template>
          <span v-else class="text-sm text-muted">Sin asignar</span>
          <button v-if="puedeOperar" class="self-start text-[13px] font-semibold text-carmin-600 hover:underline dark:text-carmin-200" @click="abrirTripulacion">
            Editar tripulación
          </button>
        </div>
        <div class="flex flex-col gap-1 rounded-2xl border border-line bg-surface p-5">
          <span class="text-[13px] text-muted">Carga a bordo</span>
          <strong class="font-display text-2xl">{{ manifiesto.data.value?.encomiendas.length ?? 0 }} guías</strong>
          <span class="text-[13px] text-muted">{{ manifiesto.data.value?.total_encomiendas_kg ?? 0 }} kg</span>
        </div>
      </div>

      <section class="overflow-hidden rounded-2xl border border-line bg-surface print-plain">
        <div class="print-only px-5 pt-5">
          <p class="font-display text-lg font-bold">Transportes El Mexicano S.R.L. · Manifiesto de pasajeros</p>
          <p class="text-sm">
            {{ s?.codigo }} · {{ s?.origen }} → {{ s?.destino }} · {{ fechaHora(s?.fecha_hora_salida) }} · Bus {{ s?.bus }} ·
            Tripulación: {{ manifiesto.data.value?.tripulacion.map((t) => t.nombre).join(', ') }}
          </p>
        </div>
        <div class="no-print flex flex-wrap items-center justify-between gap-3 px-4 pt-1">
          <TabsBar v-model="pestana" :tabs="pestanas" label="Detalle de la salida" class="flex-1 border-b-0" />
          <BaseButton variant="subtle" size="sm" class="h-9" @click="imprimir"><Printer class="size-4" aria-hidden="true" />Imprimir manifiesto</BaseButton>
        </div>
        <div class="border-t border-line">
          <DataTable
            v-if="pestana === 'pasajeros'"
            :columns="colPasajeros"
            :rows="manifiesto.data.value?.pasajeros ?? []"
            row-key="numero_boleto"
            :loading="manifiesto.isLoading.value"
            caption="Manifiesto de pasajeros"
            empty-text="Aún no hay boletos emitidos para esta salida."
          >
            <template #cell-numero_asiento="{ row }"><strong>{{ row.numero_asiento }}</strong> <span class="text-muted">{{ row.clase.split(' ')[0] }}</span></template>
            <template #cell-tipo_pasajero="{ row }">{{ TIPO_PASAJERO[row.tipo_pasajero] ?? row.tipo_pasajero }}</template>
            <template #cell-numero_boleto="{ row }"><span class="codigo text-xs">{{ row.numero_boleto }}</span></template>
            <template #cell-equipaje_kg="{ row }">{{ row.equipaje_kg ? `${row.equipaje_kg} kg` : '—' }}</template>
            <template #cell-estado="{ row }"><StatusBadge size="sm" v-bind="etiqueta(ESTADO_BOLETO, row.estado)" /></template>
          </DataTable>
          <DataTable
            v-else-if="pestana === 'encomiendas'"
            :columns="colEncomiendas"
            :rows="manifiesto.data.value?.encomiendas ?? []"
            row-key="numero_guia"
            caption="Encomiendas a bordo"
            empty-text="No hay encomiendas asignadas a esta salida."
          >
            <template #cell-numero_guia="{ row }">
              <RouterLink :to="{ name: 'admin-encomienda', params: { guia: row.numero_guia } }" class="codigo text-sm text-carmin-600 hover:underline dark:text-carmin-200">{{ row.numero_guia }}</RouterLink>
            </template>
            <template #cell-tipo_envio="{ row }">{{ TIPO_ENVIO[row.tipo_envio] }}</template>
            <template #cell-peso_kg="{ row }">{{ row.peso_kg }} kg</template>
            <template #cell-estado="{ row }"><StatusBadge size="sm" v-bind="etiqueta(ESTADO_ENCOMIENDA, row.estado)" /></template>
          </DataTable>
          <div v-else class="flex flex-col gap-4 p-5">
            <p v-if="precios.isError.value" class="text-sm text-muted">Asigna un bus para ver los precios de esta salida.</p>
            <ul v-else class="grid gap-3 sm:grid-cols-2">
              <li v-for="p in precios.data.value?.precios ?? []" :key="p.tipo_asiento" class="flex items-center justify-between rounded-xl border border-line p-4">
                <div>
                  <p class="font-semibold">{{ p.nombre }}</p>
                  <p class="text-[13px] text-muted">Máximo referencial {{ bs(p.precio_maximo_referencial_bs) }}</p>
                </div>
                <div class="text-right">
                  <p class="font-display text-2xl font-bold">{{ bs(p.precio_bs) }}</p>
                  <StatusBadge v-if="p.es_precio_especial" size="sm" tono="exito" label="Precio especial" />
                </div>
              </li>
            </ul>
            <BaseButton v-if="puedeOperar && precios.data.value" variant="subtle" size="sm" class="h-10 self-start" @click="abrirPrecios">
              <Tag class="size-4" aria-hidden="true" />Definir precio especial
            </BaseButton>
          </div>
        </div>
      </section>
    </template>

    <AppDialog
      :open="!!dialogoEstado"
      :title="dialogoEstado === 'cancelada' ? 'Cancelar salida' : 'Registrar demora'"
      :description="dialogoEstado === 'cancelada' ? 'Se reembolsará el 100 % a todos los boletos pagados y se liberarán las encomiendas asignadas.' : 'Los pasajeros verán la demora en su reserva y en el tablero de salidas.'"
      @update:open="(v) => !v && (dialogoEstado = null)"
    >
      <div class="flex flex-col gap-4">
        <TextInput v-if="dialogoEstado === 'demorada'" v-model.number="formEstado.minutos" type="number" min="1" max="1440" label="Minutos de demora" />
        <TextArea v-model="formEstado.motivo" label="Motivo" :rows="3" maxlength="250" :required="dialogoEstado === 'cancelada'" hint="Se muestra a los pasajeros." />
      </div>
      <template #footer>
        <BaseButton variant="subtle" @click="dialogoEstado = null">Volver</BaseButton>
        <BaseButton
          :variant="dialogoEstado === 'cancelada' ? 'danger' : 'primary'"
          :loading="cambiarEstado.isPending.value"
          :disabled="dialogoEstado === 'cancelada' && formEstado.motivo.trim().length < 3"
          @click="cambiarEstado.mutate(dialogoEstado!)"
        >
          {{ dialogoEstado === 'cancelada' ? 'Cancelar salida y reembolsar' : 'Guardar demora' }}
        </BaseButton>
      </template>
    </AppDialog>

    <AppDialog v-model:open="dialogoBus" title="Cambiar bus" description="Solo buses operativos y libres en ese horario. Los pasajeros conservan su número de asiento.">
      <SelectInput v-model="busElegido" label="Bus" placeholder="Elige un bus" :options="opcionesBus" />
      <template #footer>
        <BaseButton variant="subtle" @click="dialogoBus = false">Cancelar</BaseButton>
        <BaseButton :disabled="!busElegido" :loading="cambiarBus.isPending.value" @click="cambiarBus.mutate()">Asignar bus</BaseButton>
      </template>
    </AppDialog>

    <AppDialog v-model:open="dialogoTripulacion" title="Tripulación" description="Un viaje de más de 8 horas requiere conductor de relevo.">
      <div class="flex flex-col gap-4">
        <SelectInput v-model="tripulacion.conductor" label="Conductor" :options="opcionesConductor" />
        <SelectInput v-model="tripulacion.relevo" label="Conductor de relevo" :options="opcionesConductor" />
      </div>
      <template #footer>
        <BaseButton variant="subtle" @click="dialogoTripulacion = false">Cancelar</BaseButton>
        <BaseButton :disabled="!tripulacion.conductor" :loading="guardarTripulacion.isPending.value" @click="guardarTripulacion.mutate()">
          <Pencil class="size-4" aria-hidden="true" />Guardar
        </BaseButton>
      </template>
    </AppDialog>

    <AppDialog v-model:open="dialogoPrecios" title="Precio especial" description="Solo para esta salida (feriados, temporada, promociones). No puede superar la tarifa máxima referencial.">
      <div class="flex flex-col gap-4">
        <TextInput
          v-for="p in precios.data.value?.precios ?? []"
          :key="p.tipo_asiento"
          v-model="nuevosPrecios[p.tipo_asiento]"
          :label="`${p.nombre} (máx. ${bs(p.precio_maximo_referencial_bs)})`"
          inputmode="decimal"
        >
          <template #icono><span class="text-sm text-muted">Bs</span></template>
        </TextInput>
      </div>
      <template #footer>
        <BaseButton variant="subtle" @click="dialogoPrecios = false">Cancelar</BaseButton>
        <BaseButton :loading="guardarPrecios.isPending.value" @click="guardarPrecios.mutate()"><ArrowRight class="size-4" aria-hidden="true" />Guardar precios</BaseButton>
      </template>
    </AppDialog>
  </div>
</template>
