<script setup lang="ts">
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { CalendarPlus } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError, api, unwrap } from '@/api/client'
import { useRutas } from '@/api/queries'
import AppDialog from '@/components/ui/AppDialog.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import DataTable from '@/components/ui/DataTable.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import SelectInput from '@/components/ui/SelectInput.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { fechaCorta, hora, hoyISO, sumarDias } from '@/lib/format'
import { ESTADO_SALIDA, etiqueta } from '@/lib/labels'
import { ACCESO } from '@/lib/roles'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

const router = useRouter()
const auth = useAuthStore()
const avisos = useToastStore()
const cliente = useQueryClient()
const { data: rutas } = useRutas()

const filtros = reactive({ fecha: hoyISO(), ruta: null as string | null, estado: null as string | null })
const offset = ref(0)
const LIMITE = 25
watch(filtros, () => (offset.value = 0))

const salidas = useQuery({
  queryKey: computed(() => ['admin-salidas', { ...filtros }, offset.value]),
  queryFn: () =>
    unwrap(
      api.GET('/api/v1/admin/salidas', {
        params: {
          query: {
            fecha: filtros.fecha || undefined,
            ruta: filtros.ruta ?? undefined,
            estado: (filtros.estado ?? undefined) as never,
            limit: LIMITE,
            offset: offset.value,
          },
        },
      }),
    ),
  placeholderData: keepPreviousData,
})

const opcionesRuta = computed(() => [
  { value: null, label: 'Todas las rutas' },
  ...(rutas.value ?? []).map((r) => ({ value: r.codigo, label: `${r.origen} → ${r.destino}` })),
])
const opcionesEstado = [
  { value: null, label: 'Todos los estados' },
  ...Object.entries(ESTADO_SALIDA).map(([value, e]) => ({ value, label: e.label })),
]

const columnas = [
  { key: 'hora', label: 'Salida' },
  { key: 'ruta', label: 'Ruta' },
  { key: 'codigo', label: 'Código', hideSm: true },
  { key: 'bus', label: 'Bus · andén', hideSm: true },
  { key: 'ocupacion', label: 'Ocupación', class: 'w-44' },
  { key: 'estado', label: 'Estado' },
]

const generar = ref(false)
const rango = reactive({ desde: hoyISO(), hasta: sumarDias(hoyISO(), 30) })
const generacion = useMutation({
  mutationFn: () => unwrap(api.POST('/api/v1/admin/salidas/generar', { body: { desde: rango.desde, hasta: rango.hasta } })),
  onSuccess: (r) => {
    generar.value = false
    avisos.exito(r.creadas ? `Se crearon ${r.creadas} salidas` : 'No había salidas nuevas por crear')
    void cliente.invalidateQueries({ queryKey: ['admin-salidas'] })
  },
  onError: (e) => avisos.error('No se pudo generar', e instanceof ApiError ? e.message : undefined),
})
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader title="Salidas" subtitle="Programación diaria de viajes, buses y estados.">
      <BaseButton v-if="auth.puede(ACCESO.salidasOperar)" variant="subtle" size="sm" class="h-10" @click="generar = true">
        <CalendarPlus class="size-4" aria-hidden="true" />Generar desde plantillas
      </BaseButton>
    </PageHeader>

    <div class="grid gap-3 rounded-2xl border border-line bg-surface p-4 sm:grid-cols-3">
      <TextInput v-model="filtros.fecha" type="date" label="Fecha" />
      <SelectInput v-model="filtros.ruta" label="Ruta" :options="opcionesRuta" />
      <SelectInput v-model="filtros.estado" label="Estado" :options="opcionesEstado" />
    </div>

    <ErrorState v-if="salidas.isError.value" :error="salidas.error.value" @retry="salidas.refetch()" />
    <div v-else class="overflow-hidden rounded-2xl border border-line bg-surface">
      <DataTable
        :columns="columnas"
        :rows="salidas.data.value?.items ?? []"
        row-key="id"
        :loading="salidas.isLoading.value"
        clickable
        caption="Salidas"
        empty-text="No hay salidas con estos filtros."
        @row-click="(s) => router.push({ name: 'admin-salida', params: { id: s.id } })"
      >
        <template #cell-hora="{ row }">
          <span class="font-bold tabular">{{ hora(row.fecha_hora_salida) }}</span>
          <span class="ml-1.5 text-xs text-muted">{{ fechaCorta(row.fecha_hora_salida) }}</span>
        </template>
        <template #cell-ruta="{ row }">{{ row.origen }} → {{ row.destino }}</template>
        <template #cell-codigo="{ row }"><span class="codigo text-xs text-muted">{{ row.codigo }}</span></template>
        <template #cell-bus="{ row }">{{ row.bus ?? 'Sin bus' }}<span v-if="row.anden" class="text-muted"> · {{ row.anden }}</span></template>
        <template #cell-ocupacion="{ row }">
          <ProgressBar v-if="row.asientos_total" :value="row.asientos_ocupados ?? 0" :max="row.asientos_total" />
          <span v-else class="text-sm text-muted">—</span>
        </template>
        <template #cell-estado="{ row }">
          <StatusBadge
            size="sm"
            :tono="etiqueta(ESTADO_SALIDA, row.estado).tono"
            :label="row.estado === 'demorada' ? `Demorada ${row.minutos_demora} min` : etiqueta(ESTADO_SALIDA, row.estado).label"
          />
        </template>
      </DataTable>
      <PaginationBar v-if="salidas.data.value" v-model:offset="offset" :total="salidas.data.value.total" :limit="LIMITE" />
    </div>

    <AppDialog v-model:open="generar" title="Generar salidas" description="Crea las salidas de las plantillas de horario activas. Las que ya existen no se duplican.">
      <div class="grid gap-4 sm:grid-cols-2">
        <TextInput v-model="rango.desde" type="date" label="Desde" />
        <TextInput v-model="rango.hasta" type="date" label="Hasta" hint="Máximo 90 días" />
      </div>
      <template #footer>
        <BaseButton variant="subtle" @click="generar = false">Cancelar</BaseButton>
        <BaseButton :loading="generacion.isPending.value" @click="generacion.mutate()">Generar</BaseButton>
      </template>
    </AppDialog>
  </div>
</template>
