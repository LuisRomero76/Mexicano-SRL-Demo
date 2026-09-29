<script setup lang="ts">
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { refDebounced } from '@vueuse/core'
import { PackagePlus } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, unwrap } from '@/api/client'
import { useOficinasPublicas } from '@/api/queries'
import BaseButton from '@/components/ui/BaseButton.vue'
import DataTable from '@/components/ui/DataTable.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import SelectInput from '@/components/ui/SelectInput.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { bsExacto, fechaHora } from '@/lib/format'
import { ESTADO_ENCOMIENDA, ESTADO_PAGO, TIPO_ENVIO, etiqueta } from '@/lib/labels'
import { ACCESO } from '@/lib/roles'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { data: oficinas } = useOficinasPublicas()

const filtros = reactive({
  q: typeof route.query.q === 'string' ? route.query.q : '',
  estado: null as string | null,
  oficina: null as string | null,
})
const q = refDebounced(computed(() => filtros.q), 350)
const offset = ref(0)
const LIMITE = 20
watch(() => [q.value, filtros.estado, filtros.oficina], () => (offset.value = 0))

const lista = useQuery({
  queryKey: computed(() => ['admin-encomiendas', q.value, filtros.estado, filtros.oficina, offset.value]),
  queryFn: () =>
    unwrap(
      api.GET('/api/v1/admin/encomiendas', {
        params: {
          query: {
            q: q.value.trim() || undefined,
            estado: (filtros.estado ?? undefined) as never,
            oficina: filtros.oficina ?? undefined,
            limit: LIMITE,
            offset: offset.value,
          },
        },
      }),
    ),
  placeholderData: keepPreviousData,
})

const opcionesOficina = computed(() => [
  { value: null, label: 'Todas las bodegas' },
  ...(oficinas.value ?? []).filter((o) => o.tipo !== 'boleteria').map((o) => ({ value: o.codigo, label: o.nombre })),
])
const columnas = [
  { key: 'numero_guia', label: 'Guía' },
  { key: 'destinatario', label: 'Destinatario' },
  { key: 'ruta', label: 'Origen → destino', hideSm: true },
  { key: 'envio', label: 'Envío', hideSm: true },
  { key: 'precio', label: 'Precio', align: 'right' as const },
  { key: 'estado', label: 'Estado' },
]
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader title="Encomiendas" subtitle="Guías registradas en todas las bodegas.">
      <BaseButton v-if="auth.puede(ACCESO.encomiendasRegistrar)" :to="{ name: 'admin-encomienda-nueva' }" size="sm" class="h-10">
        <PackagePlus class="size-4" aria-hidden="true" />Nueva encomienda
      </BaseButton>
    </PageHeader>
    <div class="grid gap-3 rounded-2xl border border-line bg-surface p-4 sm:grid-cols-3">
      <TextInput v-model="filtros.q" label="Buscar" placeholder="Guía, destinatario o CI del remitente" type="search" autocomplete="off" />
      <SelectInput v-model="filtros.estado" label="Estado" :options="[{ value: null, label: 'Todos' }, ...Object.entries(ESTADO_ENCOMIENDA).map(([value, e]) => ({ value, label: e.label }))]" />
      <SelectInput v-model="filtros.oficina" label="Bodega (origen o destino)" :options="opcionesOficina" />
    </div>
    <ErrorState v-if="lista.isError.value" :error="lista.error.value" @retry="lista.refetch()" />
    <div v-else class="overflow-hidden rounded-2xl border border-line bg-surface">
      <DataTable
        :columns="columnas"
        :rows="lista.data.value?.items ?? []"
        row-key="numero_guia"
        :loading="lista.isLoading.value"
        clickable
        caption="Encomiendas"
        empty-text="No hay encomiendas con estos filtros."
        @row-click="(e) => router.push({ name: 'admin-encomienda', params: { guia: e.numero_guia } })"
      >
        <template #cell-numero_guia="{ row }">
          <span class="codigo">{{ row.numero_guia }}</span>
          <span class="block text-xs text-muted">{{ fechaHora(row.fecha_registro) }}</span>
        </template>
        <template #cell-destinatario="{ row }">
          <span class="font-medium">{{ row.destinatario_nombre }}</span>
          <span class="block text-xs text-muted">De {{ row.remitente }}</span>
        </template>
        <template #cell-ruta="{ row }">{{ row.oficina_origen }} → {{ row.oficina_destino }}</template>
        <template #cell-envio="{ row }">{{ TIPO_ENVIO[row.tipo_envio] }} · {{ row.peso_kg }} kg<span v-if="row.modalidad_entrega === 'puerta_a_puerta'" class="text-muted"> · a domicilio</span></template>
        <template #cell-precio="{ row }">
          <span class="font-semibold tabular">{{ bsExacto(row.precio_bs) }}</span>
          <span class="block text-xs" :class="row.estado_pago === 'pendiente' ? 'font-semibold text-aviso-700' : 'text-muted'">
            {{ etiqueta(ESTADO_PAGO, row.estado_pago).label }}{{ row.estado_pago === 'pendiente' ? ' en destino' : '' }}
          </span>
        </template>
        <template #cell-estado="{ row }"><StatusBadge size="sm" v-bind="etiqueta(ESTADO_ENCOMIENDA, row.estado)" /></template>
      </DataTable>
      <PaginationBar v-if="lista.data.value" v-model:offset="offset" :total="lista.data.value.total" :limit="LIMITE" />
    </div>
  </div>
</template>
