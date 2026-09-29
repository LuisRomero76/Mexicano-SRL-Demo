<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { CircleAlert, Coins, Gauge, Package, PackagePlus, RotateCcw, ScanLine, Ticket, TicketCheck } from '@lucide/vue'
import type { EChartsOption } from 'echarts'
import { computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { api, unwrap } from '@/api/client'
import type { Resumen } from '@/api/reportes'
import EChart from '@/components/charts/EChart.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import DataTable from '@/components/ui/DataTable.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import SurfaceCard from '@/components/ui/SurfaceCard.vue'
import { bs, fechaCorta, fechaLarga, hora } from '@/lib/format'
import { CANAL, ESTADO_ENCOMIENDA, ESTADO_SALIDA, etiqueta } from '@/lib/labels'
import { ACCESO } from '@/lib/roles'
import { useAuthStore } from '@/stores/auth'
import { useTemaStore } from '@/stores/tema'

const auth = useAuthStore()
const tema = useTemaStore()
const router = useRouter()

const resumen = useQuery({
  queryKey: ['resumen'],
  queryFn: async () => (await unwrap(api.GET('/api/v1/admin/reportes/resumen'))) as unknown as Resumen,
  refetchInterval: 60_000,
})
const r = computed(() => resumen.data.value)

const saludo = computed(() => {
  const h = Number(new Date().toLocaleTimeString('en-GB', { timeZone: 'America/La_Paz', hour: '2-digit' }))
  return h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches'
})
const conNovedad = computed(() => (r.value?.salidas_hoy ?? []).filter((s) => ['demorada', 'cancelada'].includes(s.estado)).length)
const canales = computed(() => {
  const total = (r.value?.por_canal_hoy ?? []).reduce((t, c) => t + c.ventas, 0)
  return (r.value?.por_canal_hoy ?? []).map((c) => `${c.ventas} ${CANAL[c.canal] ?? c.canal}`).join(' · ') || (total ? '' : 'Sin ventas aún')
})

const grafico = computed<EChartsOption>(() => {
  const dias = r.value?.ventas_7_dias ?? []
  const texto = tema.oscuro ? '#A3B2CC' : '#586174'
  return {
    grid: { left: 8, right: 8, top: 16, bottom: 4, containLabel: true },
    tooltip: { trigger: 'axis', valueFormatter: (v) => bs(Number(v)) },
    xAxis: {
      type: 'category',
      data: dias.map((d, i) => (i === dias.length - 1 ? 'Hoy' : fechaCorta(d.fecha).split(' ')[0])),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: texto },
    },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: tema.oscuro ? '#213659' : '#EFEAE1' } }, axisLabel: { color: texto } },
    series: [
      {
        type: 'bar',
        barWidth: '55%',
        data: dias.map((d, i) => ({
          value: Number(d.total_bs),
          itemStyle: { color: i === dias.length - 1 ? '#B3122E' : tema.oscuro ? '#7D8FB0' : '#1B3358', borderRadius: [6, 6, 0, 0] },
        })),
      },
    ],
  }
})

const columnas = [
  { key: 'hora', label: 'Hora' },
  { key: 'ruta', label: 'Ruta' },
  { key: 'bus', label: 'Bus', hideSm: true },
  { key: 'ocupacion', label: 'Ocupación', class: 'w-48' },
  { key: 'estado', label: 'Estado' },
]

const acciones = computed(() =>
  [
    { to: { name: 'admin-boleteria' }, label: 'Nueva venta', icono: Ticket, roles: ACCESO.boleteria },
    { to: { name: 'admin-abordaje' }, label: 'Abordaje', icono: ScanLine, roles: ACCESO.abordaje },
    { to: { name: 'admin-encomienda-nueva' }, label: 'Nueva encomienda', icono: PackagePlus, roles: ACCESO.encomiendasRegistrar },
    { to: { name: 'admin-reembolsos' }, label: 'Reembolsos', icono: RotateCcw, roles: ACCESO.reembolsos },
  ].filter((a) => auth.puede(a.roles)),
)
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader
      :title="`${saludo}, ${auth.usuario?.nombres ?? ''}`"
      :subtitle="r ? `${fechaLarga(r.fecha)} · ${r.salidas_hoy.length} salidas hoy${conNovedad ? ` · ${conNovedad} con novedades` : ''}` : undefined"
    >
      <BaseButton v-for="a in acciones" :key="a.label" :to="a.to" :variant="a.label === 'Nueva venta' ? 'primary' : 'subtle'" size="sm" class="h-10">
        <component :is="a.icono" class="size-4" aria-hidden="true" />{{ a.label }}
      </BaseButton>
    </PageHeader>

    <ErrorState v-if="resumen.isError.value" :error="resumen.error.value" @retry="resumen.refetch()" />
    <template v-else>
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Ventas de hoy" :icon="Coins" :loading="resumen.isLoading.value" :value="bs(r?.ventas_hoy_bs ?? 0)" :hint="`${r?.ventas_hoy ?? 0} ventas`" />
        <KpiCard label="Boletos emitidos hoy" :icon="TicketCheck" :loading="resumen.isLoading.value" :value="String(r?.boletos_hoy ?? 0)" :hint="canales" />
        <KpiCard label="Ocupación de hoy" :icon="Gauge" :loading="resumen.isLoading.value" :value="`${r?.ocupacion_hoy_pct ?? 0} %`">
          <div class="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2">
            <div class="h-full rounded-full bg-noche-700 dark:bg-sky-400" :style="{ width: `${r?.ocupacion_hoy_pct ?? 0}%` }" />
          </div>
        </KpiCard>
        <KpiCard
          label="Encomiendas por cobrar"
          :icon="Package"
          :loading="resumen.isLoading.value"
          :value="bs(r?.pendiente_de_cobro_bs ?? 0)"
          tone="aviso"
          :hint="r?.reembolsos_pendientes ? `${r.reembolsos_pendientes} reembolsos por resolver` : 'Sin reembolsos pendientes'"
        />
      </div>

      <div class="grid items-start gap-6 xl:grid-cols-[1fr_380px]">
        <SurfaceCard title="Salidas de hoy" :padded="false">
          <template #actions>
            <RouterLink v-if="auth.puede(ACCESO.salidas)" :to="{ name: 'admin-salidas' }" class="text-sm font-semibold text-carmin-600 hover:underline dark:text-carmin-200">Ver todas</RouterLink>
          </template>
          <DataTable
            :columns="columnas"
            :rows="r?.salidas_hoy ?? []"
            row-key="salida_id"
            :loading="resumen.isLoading.value"
            empty-text="No hay salidas programadas para hoy."
            :clickable="auth.puede(ACCESO.salidas)"
            caption="Salidas de hoy"
            @row-click="(s) => router.push({ name: 'admin-salida', params: { id: s.salida_id } })"
          >
            <template #cell-hora="{ row }"><span class="font-bold tabular">{{ hora(row.fecha_hora_salida) }}</span></template>
            <template #cell-ruta="{ row }">{{ row.origen }} → {{ row.destino }}</template>
            <template #cell-bus="{ row }"><span class="text-muted">{{ row.bus ?? '—' }}</span></template>
            <template #cell-ocupacion="{ row }"><ProgressBar :value="row.asientos_ocupados" :max="row.asientos_total" /></template>
            <template #cell-estado="{ row }">
              <StatusBadge
                size="sm"
                :tono="etiqueta(ESTADO_SALIDA, row.estado).tono"
                :label="row.estado === 'demorada' ? `Demorada ${row.minutos_demora} min` : etiqueta(ESTADO_SALIDA, row.estado).label"
              />
            </template>
          </DataTable>
        </SurfaceCard>

        <div class="flex flex-col gap-6">
          <SurfaceCard title="Requiere atención">
            <ul class="flex flex-col gap-3">
              <li v-if="!r?.novedades.length && !r?.reembolsos_pendientes" class="text-sm text-muted">Todo en orden por ahora.</li>
              <li v-for="n in r?.novedades ?? []" :key="n.salida_id">
                <RouterLink :to="{ name: 'admin-salida', params: { id: n.salida_id } }" class="flex gap-3 text-sm hover:underline">
                  <span class="mt-1.5 size-2 shrink-0 rounded-full" :class="n.estado === 'cancelada' ? 'bg-peligro-600' : 'bg-aviso-600'" aria-hidden="true" />
                  <span>
                    <strong>{{ n.ruta }} · {{ fechaCorta(n.fecha_hora_salida) }} {{ hora(n.fecha_hora_salida) }}</strong>
                    {{ n.estado === 'cancelada' ? 'cancelada' : `demorada ${n.minutos_demora} min` }}<template v-if="n.motivo">: {{ n.motivo }}</template>
                  </span>
                </RouterLink>
              </li>
              <li v-if="r?.reembolsos_pendientes">
                <RouterLink :to="{ name: 'admin-reembolsos' }" class="flex gap-3 text-sm hover:underline">
                  <CircleAlert class="mt-0.5 size-4 shrink-0 text-carmin-600" aria-hidden="true" />
                  <span><strong>{{ r.reembolsos_pendientes }} reembolsos por resolver</strong> · {{ bs(r.reembolsos_pendientes_bs) }}</span>
                </RouterLink>
              </li>
            </ul>
          </SurfaceCard>
          <SurfaceCard title="Ventas · últimos 7 días">
            <EChart :option="grafico" height="200px" label="Ventas de los últimos 7 días" />
          </SurfaceCard>
          <SurfaceCard title="Encomiendas por estado">
            <div class="flex flex-wrap gap-2">
              <StatusBadge
                v-for="(n, estado) in r?.encomiendas_por_estado ?? {}"
                :key="estado"
                size="sm"
                :tono="etiqueta(ESTADO_ENCOMIENDA, String(estado)).tono"
                :label="`${etiqueta(ESTADO_ENCOMIENDA, String(estado)).label}: ${n}`"
              />
            </div>
          </SurfaceCard>
        </div>
      </div>
    </template>
  </div>
</template>
