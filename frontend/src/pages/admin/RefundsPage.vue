<script setup lang="ts">
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { ApiError, api, unwrap, type Schemas } from '@/api/client'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import DataTable from '@/components/ui/DataTable.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import TabsBar from '@/components/ui/TabsBar.vue'
import TextArea from '@/components/ui/TextArea.vue'
import { bsExacto, fechaCorta, fechaHora } from '@/lib/format'
import { ESTADO_REEMBOLSO, etiqueta } from '@/lib/labels'
import { ACCESO } from '@/lib/roles'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

type Reembolso = Schemas['ReembolsoOut']
type Estado = Schemas['EstadoReembolso']

const auth = useAuthStore()
const avisos = useToastStore()
const cliente = useQueryClient()
const puedeResolver = computed(() => auth.puede(ACCESO.reembolsosResolver))

const pestana = ref<string>('solicitado')
const offset = ref(0)
const LIMITE = 20
watch(pestana, () => (offset.value = 0))

const lista = useQuery({
  queryKey: computed(() => ['admin-reembolsos', pestana.value, offset.value]),
  queryFn: () =>
    unwrap(
      api.GET('/api/v1/admin/reembolsos', {
        params: { query: { estado: pestana.value === 'todos' ? undefined : (pestana.value as Estado), limit: LIMITE, offset: offset.value } },
      }),
    ),
  placeholderData: keepPreviousData,
})

const pestanas = [
  { key: 'solicitado', label: 'Por revisar' },
  { key: 'aprobado', label: 'Por pagar' },
  { key: 'pagado', label: 'Pagados' },
  { key: 'rechazado', label: 'Rechazados' },
  { key: 'todos', label: 'Todos' },
]

const accion = ref<{ reembolso: Reembolso; estado: Estado } | null>(null)
const nota = ref('')
const resolver = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/admin/reembolsos/{reembolso_id}/resolver', {
        params: { path: { reembolso_id: accion.value!.reembolso.id } },
        body: { estado: accion.value!.estado, nota: nota.value.trim() || null },
      }),
    ),
  onSuccess: (r) => {
    avisos.exito(`Reembolso ${etiqueta(ESTADO_REEMBOLSO, r.estado).label.toLowerCase()}`)
    accion.value = null
    nota.value = ''
    void cliente.invalidateQueries({ queryKey: ['admin-reembolsos'] })
    void cliente.invalidateQueries({ queryKey: ['resumen'] })
  },
  onError: (e) => avisos.error('No se pudo resolver', e instanceof ApiError ? e.message : undefined),
})
const textos: Record<string, { titulo: string; boton: string }> = {
  aprobado: { titulo: 'Aprobar reembolso', boton: 'Aprobar' },
  rechazado: { titulo: 'Rechazar reembolso', boton: 'Rechazar' },
  pagado: { titulo: 'Marcar como pagado', boton: 'Confirmar pago' },
}

const columnas = [
  { key: 'solicitado_at', label: 'Solicitado' },
  { key: 'boleto', label: 'Boleto · pasajero' },
  { key: 'origen', label: 'Origen', hideSm: true },
  { key: 'monto', label: 'A devolver', align: 'right' as const },
  { key: 'limite', label: 'Pagar hasta', hideSm: true },
  { key: 'estado', label: 'Estado' },
  { key: 'acciones', label: '', align: 'right' as const },
]
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader title="Reembolsos" subtitle="85 % cuando lo pide el cliente con 2 h de anticipación; 100 % cuando la empresa cancela." />
    <ErrorState v-if="lista.isError.value" :error="lista.error.value" @retry="lista.refetch()" />
    <div v-else class="overflow-hidden rounded-2xl border border-line bg-surface">
      <TabsBar v-model="pestana" :tabs="pestanas" label="Estado de los reembolsos" class="px-3" />
      <DataTable :columns="columnas" :rows="lista.data.value?.items ?? []" row-key="id" :loading="lista.isLoading.value" caption="Reembolsos" empty-text="No hay reembolsos en esta bandeja.">
        <template #cell-solicitado_at="{ row }"><span class="text-muted">{{ fechaHora(row.solicitado_at) }}</span></template>
        <template #cell-boleto="{ row }">
          <span class="codigo text-xs">{{ row.numero_boleto ?? '—' }}</span>
          <span class="block text-[13px]">{{ row.pasajero }} <span class="text-muted">· {{ row.codigo_reserva }}</span></span>
        </template>
        <template #cell-origen="{ row }">{{ row.origen === 'cancelacion_empresa' ? 'Cancelación de la empresa' : 'Pedido del cliente' }}</template>
        <template #cell-monto="{ row }">
          <strong class="tabular">{{ bsExacto(row.monto_bs) }}</strong>
          <span class="block text-xs text-muted">de {{ bsExacto(row.monto_original_bs) }}</span>
        </template>
        <template #cell-limite="{ row }">{{ row.fecha_limite_pago ? fechaCorta(row.fecha_limite_pago) : '—' }}</template>
        <template #cell-estado="{ row }"><StatusBadge size="sm" v-bind="etiqueta(ESTADO_REEMBOLSO, row.estado)" /></template>
        <template #cell-acciones="{ row }">
          <div v-if="puedeResolver" class="flex justify-end gap-2">
            <template v-if="row.estado === 'solicitado'">
              <BaseButton size="sm" variant="subtle" @click="accion = { reembolso: row, estado: 'rechazado' }">Rechazar</BaseButton>
              <BaseButton size="sm" @click="accion = { reembolso: row, estado: 'aprobado' }">Aprobar</BaseButton>
            </template>
            <BaseButton v-else-if="row.estado === 'aprobado'" size="sm" variant="success" @click="accion = { reembolso: row, estado: 'pagado' }">Marcar pagado</BaseButton>
          </div>
        </template>
      </DataTable>
      <PaginationBar v-if="lista.data.value" v-model:offset="offset" :total="lista.data.value.total" :limit="LIMITE" />
    </div>

    <ConfirmDialog
      :open="!!accion"
      :title="textos[accion?.estado ?? 'aprobado'].titulo"
      :description="accion ? `${accion.reembolso.pasajero} · ${bsExacto(accion.reembolso.monto_bs)}` : ''"
      :confirm-label="textos[accion?.estado ?? 'aprobado'].boton"
      :danger="accion?.estado === 'rechazado'"
      :loading="resolver.isPending.value"
      @update:open="(v) => !v && (accion = null)"
      @confirm="resolver.mutate()"
    >
      <p v-if="accion?.estado === 'rechazado'" class="mb-3 text-sm text-muted">El boleto vuelve a quedar emitido si el asiento sigue libre.</p>
      <TextArea v-model="nota" label="Nota interna (opcional)" :rows="2" maxlength="250" />
    </ConfirmDialog>
  </div>
</template>
