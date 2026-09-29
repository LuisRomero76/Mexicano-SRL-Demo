<script setup lang="ts">
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { refDebounced } from '@vueuse/core'
import { Printer, RotateCcw } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError, api, unwrap, type Schemas } from '@/api/client'
import TicketCard from '@/components/booking/TicketCard.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import DataTable from '@/components/ui/DataTable.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SelectInput from '@/components/ui/SelectInput.vue'
import SideSheet from '@/components/ui/SideSheet.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import TextArea from '@/components/ui/TextArea.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { bsExacto, fechaHora } from '@/lib/format'
import { CANAL, ESTADO_VENTA, METODO_PAGO, etiqueta } from '@/lib/labels'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const router = useRouter()
const avisos = useToastStore()
const cliente = useQueryClient()

const filtros = reactive({ estado: null as string | null, canal: null as string | null, documento: '' })
const documento = refDebounced(computed(() => filtros.documento), 400)
const offset = ref(0)
const LIMITE = 20
watch(() => [filtros.estado, filtros.canal, documento.value], () => (offset.value = 0))

const ventas = useQuery({
  queryKey: computed(() => ['admin-ventas', filtros.estado, filtros.canal, documento.value, offset.value]),
  queryFn: () =>
    unwrap(
      api.GET('/api/v1/admin/ventas', {
        params: {
          query: {
            estado: (filtros.estado ?? undefined) as never,
            canal: (filtros.canal ?? undefined) as never,
            documento: documento.value.trim() || undefined,
            limit: LIMITE,
            offset: offset.value,
          },
        },
      }),
    ),
  placeholderData: keepPreviousData,
})

const codigo = ref<string | null>(typeof route.query.codigo === 'string' ? route.query.codigo : null)
watch(() => route.query.codigo, (c) => (codigo.value = typeof c === 'string' ? c : null))
const abierta = computed({
  get: () => !!codigo.value,
  set: (v) => {
    if (!v) {
      codigo.value = null
      if (route.query.codigo) void router.replace({ query: {} })
    }
  },
})
const detalle = useQuery({
  queryKey: computed(() => ['admin-venta', codigo.value]),
  queryFn: () => unwrap(api.GET('/api/v1/admin/ventas/{codigo}', { params: { path: { codigo: codigo.value! } } })),
  enabled: computed(() => !!codigo.value),
})

function refrescar(): void {
  void cliente.invalidateQueries({ queryKey: ['admin-venta'] })
  void cliente.invalidateQueries({ queryKey: ['admin-ventas'] })
}

const metodo = ref<'efectivo' | 'qr'>('efectivo')
const cobrar = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/admin/ventas/{codigo}/cobrar', {
        params: { path: { codigo: codigo.value! } },
        body: { metodo: metodo.value },
      }),
    ),
  onSuccess: () => {
    avisos.exito('Venta cobrada')
    refrescar()
  },
  onError: (e) => avisos.error('No se pudo cobrar', e instanceof ApiError ? e.message : undefined),
})

const boletoReembolso = ref<Schemas['BoletoOut'] | null>(null)
const motivo = ref('')
const reembolsar = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/admin/boletos/{numero_boleto}/reembolso', {
        params: { path: { numero_boleto: boletoReembolso.value!.numero_boleto } },
        body: { motivo: motivo.value.trim() || 'Solicitud en boletería' },
      }),
    ),
  onSuccess: (r) => {
    avisos.exito('Reembolso registrado', `${bsExacto(r.monto_bs)} a devolver. Queda pendiente de aprobación.`)
    boletoReembolso.value = null
    motivo.value = ''
    refrescar()
  },
  onError: (e) => avisos.error('No se pudo registrar el reembolso', e instanceof ApiError ? e.message : undefined),
})

const columnas = [
  { key: 'codigo_reserva', label: 'Reserva' },
  { key: 'comprador', label: 'Comprador' },
  { key: 'canal', label: 'Canal', hideSm: true },
  { key: 'created_at', label: 'Fecha', hideSm: true },
  { key: 'total_bs', label: 'Total', align: 'right' as const },
  { key: 'estado', label: 'Estado' },
]
function imprimir(): void {
  window.print()
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader title="Ventas" subtitle="Reservas y pasajes vendidos por todos los canales." />
    <div class="grid gap-3 rounded-2xl border border-line bg-surface p-4 sm:grid-cols-3">
      <SelectInput v-model="filtros.estado" label="Estado" :options="[{ value: null, label: 'Todos' }, ...Object.entries(ESTADO_VENTA).map(([value, e]) => ({ value, label: e.label }))]" />
      <SelectInput v-model="filtros.canal" label="Canal" :options="[{ value: null, label: 'Todos' }, ...Object.entries(CANAL).map(([value, label]) => ({ value, label }))]" />
      <TextInput v-model="filtros.documento" label="Documento del comprador" autocomplete="off" />
    </div>

    <ErrorState v-if="ventas.isError.value" :error="ventas.error.value" @retry="ventas.refetch()" />
    <div v-else class="overflow-hidden rounded-2xl border border-line bg-surface">
      <DataTable
        :columns="columnas"
        :rows="ventas.data.value?.items ?? []"
        row-key="codigo_reserva"
        :loading="ventas.isLoading.value"
        clickable
        caption="Ventas"
        @row-click="(v) => (codigo = v.codigo_reserva)"
      >
        <template #cell-codigo_reserva="{ row }"><span class="codigo">{{ row.codigo_reserva }}</span></template>
        <template #cell-canal="{ row }">{{ CANAL[row.canal] }}</template>
        <template #cell-created_at="{ row }"><span class="text-muted">{{ fechaHora(row.created_at) }}</span></template>
        <template #cell-total_bs="{ row }"><span class="font-semibold tabular">{{ bsExacto(row.total_bs) }}</span></template>
        <template #cell-estado="{ row }"><StatusBadge size="sm" v-bind="etiqueta(ESTADO_VENTA, row.estado)" /></template>
      </DataTable>
      <PaginationBar v-if="ventas.data.value" v-model:offset="offset" :total="ventas.data.value.total" :limit="LIMITE" />
    </div>

    <SideSheet v-model:open="abierta" :title="`Reserva ${codigo ?? ''}`" :description="detalle.data.value?.mensaje">
      <SkeletonBlock v-if="detalle.isLoading.value" class="h-72" />
      <ErrorState v-else-if="detalle.isError.value" :error="detalle.error.value" @retry="detalle.refetch()" />
      <div v-else-if="detalle.data.value" class="flex flex-col gap-4">
        <dl class="grid grid-cols-2 gap-3 rounded-xl bg-canvas p-4 text-sm">
          <div><dt class="text-muted">Estado</dt><dd><StatusBadge size="sm" v-bind="etiqueta(ESTADO_VENTA, detalle.data.value.estado)" /></dd></div>
          <div><dt class="text-muted">Canal</dt><dd class="font-semibold">{{ CANAL[detalle.data.value.canal] }}</dd></div>
          <div><dt class="text-muted">Comprador</dt><dd class="font-semibold">{{ detalle.data.value.comprador }}</dd></div>
          <div><dt class="text-muted">Total</dt><dd class="font-semibold">{{ bsExacto(detalle.data.value.total_bs) }}</dd></div>
          <div v-if="detalle.data.value.pago"><dt class="text-muted">Pago</dt><dd class="font-semibold">{{ METODO_PAGO[detalle.data.value.pago.metodo] }}</dd></div>
          <div v-if="detalle.data.value.factura"><dt class="text-muted">Factura</dt><dd class="font-semibold">N.º {{ detalle.data.value.factura.numero_factura }}</dd></div>
        </dl>
        <div v-if="detalle.data.value.estado === 'pendiente_pago'" class="flex flex-col gap-3 rounded-xl border border-line p-4">
          <SegmentedControl v-model="metodo" label="Cobrar en ventanilla" variant="switch" :options="[{ value: 'efectivo', label: 'Efectivo' }, { value: 'qr', label: 'QR' }]" />
          <BaseButton :loading="cobrar.isPending.value" @click="cobrar.mutate()">Cobrar {{ bsExacto(detalle.data.value.total_bs) }}</BaseButton>
        </div>
        <div v-for="b in detalle.data.value.boletos" :key="b.numero_boleto" class="flex flex-col gap-2">
          <TicketCard :boleto="b" :salida="detalle.data.value.salida" />
          <button v-if="b.estado === 'emitido'" class="no-print inline-flex items-center gap-1.5 self-end text-sm font-semibold text-carmin-600 hover:underline dark:text-carmin-200" @click="boletoReembolso = b">
            <RotateCcw class="size-4" aria-hidden="true" />Registrar reembolso
          </button>
        </div>
      </div>
      <template #footer>
        <BaseButton variant="subtle" @click="imprimir"><Printer class="size-4" aria-hidden="true" />Imprimir</BaseButton>
      </template>
    </SideSheet>

    <AppDialog :open="!!boletoReembolso" title="Registrar reembolso" :description="`Boleto ${boletoReembolso?.numero_boleto ?? ''}: se devuelve el 85 % si faltan al menos 2 horas para la salida.`" @update:open="(v) => !v && (boletoReembolso = null)">
      <TextArea v-model="motivo" label="Motivo" :rows="3" maxlength="250" />
      <template #footer>
        <BaseButton variant="subtle" @click="boletoReembolso = null">Volver</BaseButton>
        <BaseButton variant="danger" :loading="reembolsar.isPending.value" @click="reembolsar.mutate()">Registrar</BaseButton>
      </template>
    </AppDialog>
  </div>
</template>
