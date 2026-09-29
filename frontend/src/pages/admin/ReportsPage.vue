<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { Coins, Download, Gauge, Package, Receipt } from '@lucide/vue'
import type { EChartsOption } from 'echarts'
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, unwrap } from '@/api/client'
import type { ReporteEncomiendas, ReporteVentas, SalidaDelDia } from '@/api/reportes'
import EChart from '@/components/charts/EChart.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import DataTable from '@/components/ui/DataTable.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import SurfaceCard from '@/components/ui/SurfaceCard.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { bs, bsExacto, fechaCorta, hora, hoyISO, sumarDias } from '@/lib/format'
import { CANAL, ESTADO_ENCOMIENDA, ESTADO_SALIDA, METODO_PAGO, etiqueta } from '@/lib/labels'
import { useTemaStore } from '@/stores/tema'

const tema = useTemaStore()
const router = useRouter()

// --- Periodo ---
const periodo = ref<'7' | '30' | '90' | 'rango'>('30')
const rango = reactive({ desde: sumarDias(hoyISO(), -29), hasta: hoyISO() })
const fechas = computed(() =>
  periodo.value === 'rango' ? { ...rango } : { desde: sumarDias(hoyISO(), -(Number(periodo.value) - 1)), hasta: hoyISO() },
)
const rangoValido = computed(() => fechas.value.desde <= fechas.value.hasta)

const ventas = useQuery({
  queryKey: computed(() => ['reporte-ventas', fechas.value]),
  queryFn: async () => (await unwrap(api.GET('/api/v1/admin/reportes/ventas', { params: { query: fechas.value } }))) as unknown as ReporteVentas,
  enabled: rangoValido,
})
const fechaOcupacion = ref(hoyISO())
const ocupacion = useQuery({
  queryKey: computed(() => ['reporte-ocupacion', fechaOcupacion.value]),
  queryFn: async () =>
    (await unwrap(api.GET('/api/v1/admin/reportes/ocupacion', { params: { query: { fecha: fechaOcupacion.value } } }))) as unknown as SalidaDelDia[],
})
const encomiendas = useQuery({
  queryKey: ['reporte-encomiendas'],
  queryFn: async () => (await unwrap(api.GET('/api/v1/admin/reportes/encomiendas'))) as unknown as ReporteEncomiendas,
})

const v = computed(() => ventas.data.value)
const total = computed(() => Number(v.value?.total_bs ?? 0))
const cantidad = computed(() => Number(v.value?.ventas ?? 0))
const salidasDia = computed(() =>
  (ocupacion.data.value ?? []).map((s) => ({ ...s, asientos_total: Number(s.asientos_total), asientos_ocupados: Number(s.asientos_ocupados), ocupacion_pct: Number(s.ocupacion_pct) })),
)
const ocupacionMedia = computed(() => {
  const l = salidasDia.value.filter((s) => s.estado !== 'cancelada')
  const t = l.reduce((a, s) => a + s.asientos_total, 0)
  return t ? Math.round((l.reduce((a, s) => a + s.asientos_ocupados, 0) / t) * 100) : 0
})
const porCobrar = computed(() => Number(encomiendas.data.value?.pendiente_de_cobro_bs ?? 0))

// --- Gráficos ---
const colores = computed(() => ({
  texto: tema.oscuro ? '#A3B2CC' : '#586174',
  linea: tema.oscuro ? '#213659' : '#EFEAE1',
  serie: ['#B3122E', tema.oscuro ? '#7D8FB0' : '#1B3358', '#0F8A83', '#C98A0B', '#5B6B8C', '#8E2B4A'],
}))
const ejes = computed(() => ({
  axisLabel: { color: colores.value.texto },
  axisLine: { show: false },
  axisTick: { show: false },
  splitLine: { lineStyle: { color: colores.value.linea } },
}))

const graficoDias = computed<EChartsOption>(() => {
  const dias = v.value?.por_dia ?? []
  return {
    color: colores.value.serie,
    grid: { left: 8, right: 8, top: 44, bottom: 4, containLabel: true },
    legend: { top: 0, left: 'center', textStyle: { color: colores.value.texto } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: dias.map((d) => fechaCorta(d.fecha).split(' ').slice(0, 2).join(' ')), ...ejes.value, splitLine: { show: false } },
    yAxis: [
      { type: 'value', name: 'Bs', nameTextStyle: { color: colores.value.texto }, ...ejes.value },
      { type: 'value', name: 'Ventas', nameTextStyle: { color: colores.value.texto }, ...ejes.value, splitLine: { show: false } },
    ],
    series: [
      {
        name: 'Ingresos',
        type: 'bar',
        barMaxWidth: 26,
        itemStyle: { borderRadius: [5, 5, 0, 0] },
        data: dias.map((d) => Number(d.total_bs)),
        tooltip: { valueFormatter: (x) => bs(Number(x)) },
      },
      { name: 'Ventas', type: 'line', yAxisIndex: 1, smooth: true, symbol: 'circle', symbolSize: 6, data: dias.map((d) => Number(d.ventas)) },
    ],
  }
})
function dona(datos: { name: string; value: number }[]): EChartsOption {
  return {
    color: colores.value.serie,
    tooltip: { trigger: 'item', valueFormatter: (x) => bs(Number(x)) },
    legend: { bottom: 0, textStyle: { color: colores.value.texto }, itemWidth: 10, itemHeight: 10 },
    series: [
      {
        type: 'pie',
        radius: ['52%', '78%'],
        center: ['50%', '42%'],
        itemStyle: { borderColor: tema.oscuro ? '#0F213D' : '#fff', borderWidth: 2 },
        label: { show: false },
        data: datos,
      },
    ],
  }
}
const graficoCanal = computed(() => dona((v.value?.por_canal ?? []).map((c) => ({ name: CANAL[c.canal] ?? c.canal, value: Number(c.total_bs) }))))
const graficoMetodo = computed(() => dona((v.value?.por_metodo_pago ?? []).map((m) => ({ name: METODO_PAGO[m.metodo] ?? m.metodo, value: Number(m.total_bs) }))))
const graficoOficinas = computed<EChartsOption>(() => {
  const l = [...(encomiendas.data.value?.por_oficina_destino ?? [])].sort((a, b) => Number(a.encomiendas) - Number(b.encomiendas))
  return {
    color: colores.value.serie,
    grid: { left: 8, right: 24, top: 8, bottom: 4, containLabel: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', ...ejes.value },
    yAxis: { type: 'category', data: l.map((o) => o.oficina.replace('Bodega ', '')), ...ejes.value, splitLine: { show: false } },
    series: [{ name: 'Encomiendas', type: 'bar', barMaxWidth: 18, itemStyle: { borderRadius: [0, 5, 5, 0] }, data: l.map((o) => Number(o.encomiendas)) }],
  }
})
const estadosCarga = computed(() =>
  Object.entries(encomiendas.data.value?.por_estado ?? {})
    .map(([estado, n]) => ({ estado, n: Number(n) }))
    .sort((a, b) => b.n - a.n),
)
const totalCarga = computed(() => estadosCarga.value.reduce((a, e) => a + e.n, 0))

// --- Exportar CSV (ventas por día) ---
function exportar(): void {
  const filas = [['fecha', 'ventas', 'total_bs'], ...(v.value?.por_dia ?? []).map((d) => [d.fecha, String(d.ventas), String(d.total_bs)])]
  const csv = filas.map((f) => f.join(',')).join('\n')
  const url = URL.createObjectURL(new Blob([String.fromCharCode(0xfeff), csv], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `ventas_${fechas.value.desde}_${fechas.value.hasta}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

const columnasOcupacion = [
  { key: 'hora', label: 'Hora' },
  { key: 'ruta', label: 'Ruta' },
  { key: 'bus', label: 'Bus', hideSm: true },
  { key: 'ocupacion', label: 'Ocupación', class: 'w-56' },
  { key: 'estado', label: 'Estado' },
]
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader title="Reportes" subtitle="Ventas, ocupación de la flota y movimiento de carga.">
      <BaseButton variant="subtle" size="sm" class="h-10" :disabled="!v?.por_dia.length" @click="exportar"><Download class="size-4" aria-hidden="true" />Exportar CSV</BaseButton>
    </PageHeader>

    <div class="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-4 md:flex-row md:items-end">
      <SegmentedControl
        v-model="periodo"
        label="Periodo"
        variant="switch"
        class="md:w-md"
        :options="[
          { value: '7', label: '7 días' },
          { value: '30', label: '30 días' },
          { value: '90', label: '90 días' },
          { value: 'rango', label: 'Rango' },
        ]"
      />
      <div v-if="periodo === 'rango'" class="grid grid-cols-2 gap-3">
        <TextInput v-model="rango.desde" label="Desde" type="date" :max="rango.hasta" />
        <TextInput v-model="rango.hasta" label="Hasta" type="date" :min="rango.desde" :max="hoyISO()" />
      </div>
      <p class="text-sm text-muted md:ml-auto md:pb-2.5">{{ fechaCorta(fechas.desde) }} – {{ fechaCorta(fechas.hasta) }}</p>
    </div>

    <ErrorState v-if="ventas.isError.value" :error="ventas.error.value" @retry="ventas.refetch()" />
    <template v-else>
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Ingresos por pasajes" :value="bs(total)" :icon="Coins" :loading="ventas.isLoading.value" :hint="`${cantidad} ventas pagadas`" />
        <KpiCard label="Ticket promedio" :value="cantidad ? bsExacto(total / cantidad) : '—'" :icon="Receipt" :loading="ventas.isLoading.value" hint="Por venta" />
        <KpiCard label="Ocupación del día" :value="`${ocupacionMedia} %`" :icon="Gauge" :loading="ocupacion.isLoading.value" :hint="fechaCorta(fechaOcupacion)" :tone="ocupacionMedia >= 70 ? 'exito' : 'neutro'" />
        <KpiCard label="Carga por cobrar" :value="bs(porCobrar)" :icon="Package" :loading="encomiendas.isLoading.value" hint="Pago en destino pendiente" :tone="porCobrar ? 'aviso' : 'neutro'" />
      </div>

      <SurfaceCard title="Ingresos por día">
        <SkeletonBlock v-if="ventas.isLoading.value" class="h-72" />
        <EChart v-else :option="graficoDias" height="300px" label="Ingresos y cantidad de ventas por día" />
      </SurfaceCard>

      <div class="grid gap-6 lg:grid-cols-2">
        <SurfaceCard title="Por canal de venta">
          <SkeletonBlock v-if="ventas.isLoading.value" class="h-64" />
          <EChart v-else-if="v?.por_canal.length" :option="graficoCanal" label="Ingresos por canal de venta" />
          <p v-else class="py-16 text-center text-sm text-muted">Sin ventas en el periodo.</p>
        </SurfaceCard>
        <SurfaceCard title="Por método de pago">
          <SkeletonBlock v-if="ventas.isLoading.value" class="h-64" />
          <EChart v-else-if="v?.por_metodo_pago.length" :option="graficoMetodo" label="Ingresos por método de pago" />
          <p v-else class="py-16 text-center text-sm text-muted">Sin pagos en el periodo.</p>
        </SurfaceCard>
      </div>
    </template>

    <SurfaceCard title="Ocupación por salida" :padded="false">
      <template #actions>
        <TextInput v-model="fechaOcupacion" label="Fecha" type="date" class="w-44" />
      </template>
      <ErrorState v-if="ocupacion.isError.value" :error="ocupacion.error.value" @retry="ocupacion.refetch()" />
      <DataTable
        v-else
        :columns="columnasOcupacion"
        :rows="salidasDia"
        row-key="salida_id"
        :loading="ocupacion.isLoading.value"
        clickable
        caption="Ocupación por salida"
        empty-text="No hay salidas ese día."
        @row-click="(s) => router.push({ name: 'admin-salida', params: { id: s.salida_id } })"
      >
        <template #cell-hora="{ row }"><span class="font-semibold tabular">{{ hora(row.fecha_hora_salida) }}</span></template>
        <template #cell-ruta="{ row }">{{ row.origen }} → {{ row.destino }}<span class="block text-xs text-muted">{{ row.salida }}</span></template>
        <template #cell-bus="{ row }">{{ row.bus ?? '—' }}</template>
        <template #cell-ocupacion="{ row }">
          <ProgressBar :value="row.asientos_ocupados" :max="row.asientos_total" :label="`Ocupación ${row.ocupacion_pct} %`" />
        </template>
        <template #cell-estado="{ row }"><StatusBadge size="sm" v-bind="etiqueta(ESTADO_SALIDA, row.estado)" /></template>
      </DataTable>
    </SurfaceCard>

    <div class="grid gap-6 lg:grid-cols-2">
      <SurfaceCard title="Encomiendas por destino">
        <SkeletonBlock v-if="encomiendas.isLoading.value" class="h-64" />
        <EChart v-else :option="graficoOficinas" height="280px" label="Encomiendas por bodega de destino" />
      </SurfaceCard>
      <SurfaceCard title="Encomiendas por estado" :subtitle="`${totalCarga} en total`">
        <SkeletonBlock v-if="encomiendas.isLoading.value" class="h-64" />
        <ul v-else class="flex flex-col gap-3">
          <li v-for="e in estadosCarga" :key="e.estado" class="flex items-center gap-3">
            <StatusBadge size="sm" class="w-40 shrink-0" v-bind="etiqueta(ESTADO_ENCOMIENDA, e.estado)" />
            <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-2" aria-hidden="true">
              <div class="h-full rounded-full bg-noche-700 dark:bg-sky-400" :style="{ width: `${totalCarga ? (e.n / totalCarga) * 100 : 0}%` }" />
            </div>
            <span class="w-8 text-right text-sm font-semibold tabular">{{ e.n }}</span>
          </li>
        </ul>
      </SurfaceCard>
    </div>
  </div>
</template>
