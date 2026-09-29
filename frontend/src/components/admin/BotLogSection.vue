<script setup lang="ts">
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { api, unwrap, type Schemas } from '@/api/client'
import DataTable from '@/components/ui/DataTable.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SelectInput from '@/components/ui/SelectInput.vue'
import SideSheet from '@/components/ui/SideSheet.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { fechaHora, telefono } from '@/lib/format'

type Consulta = Schemas['BotConsultaOut']

/** Las 10 herramientas del agente, con el nombre que se ve en el panel. */
const TOOLS: Record<string, string> = {
  rastrear_encomienda: 'Rastrear encomienda',
  mis_encomiendas: 'Mis encomiendas',
  consultar_salidas: 'Consultar salidas',
  listar_rutas: 'Rutas',
  cotizar_envio: 'Cotizar envío',
  consultar_reserva: 'Consultar reserva',
  info_oficinas: 'Oficinas',
  buscar_faq: 'Pregunta frecuente',
  info_empresa: 'Datos de la empresa',
  solicitar_puerta_a_puerta: 'Solicitud puerta a puerta',
}

const tool = ref<string | null>(null)
const resultado = ref<'todas' | 'no'>('todas')
const offset = ref(0)
const LIMITE = 30
watch([tool, resultado], () => (offset.value = 0))

const lista = useQuery({
  queryKey: computed(() => ['bot-consultas', tool.value, resultado.value, offset.value]),
  queryFn: () =>
    unwrap(
      api.GET('/api/v1/admin/bot/consultas', {
        params: {
          query: {
            tool: tool.value ?? undefined,
            encontrado: resultado.value === 'no' ? false : undefined,
            limit: LIMITE,
            offset: offset.value,
          },
        },
      }),
    ),
  placeholderData: keepPreviousData,
  refetchInterval: 30_000,
})

const elegido = ref<Consulta | null>(null)
const abierto = computed({ get: () => !!elegido.value, set: (v) => !v && (elegido.value = null) })

const mensaje = (c: Consulta) => String(c.resultado?.mensaje ?? '—')
const parametros = (c: Consulta) =>
  Object.entries(c.parametros ?? {})
    .map(([k, v]) => `${k}: ${v}`)
    .join(' · ') || '—'

const columnas = [
  { key: 'created_at', label: 'Fecha' },
  { key: 'tool', label: 'Consulta' },
  { key: 'mensaje', label: 'Respuesta del agente', hideSm: true, class: 'w-1/2' },
  { key: 'resultado', label: 'Resultado' },
  { key: 'latencia_ms', label: 'Tiempo', align: 'right' as const, hideSm: true },
]
</script>

<template>
  <section class="flex flex-col gap-4">
    <div class="grid gap-3 rounded-2xl border border-line bg-surface p-4 sm:grid-cols-2">
      <SelectInput
        v-model="tool"
        label="Herramienta"
        :options="[
          { value: null, label: 'Todas' },
          ...Object.entries(TOOLS).map(([value, label]) => ({ value, label })),
        ]"
      />
      <SegmentedControl
        v-model="resultado"
        label="Resultado"
        variant="switch"
        :options="[
          { value: 'todas', label: 'Todas' },
          { value: 'no', label: 'Sin resultado' },
        ]"
      />
    </div>

    <ErrorState v-if="lista.isError.value" :error="lista.error.value" @retry="lista.refetch()" />
    <div v-else class="overflow-hidden rounded-2xl border border-line bg-surface">
      <DataTable
        :columns="columnas"
        :rows="lista.data.value?.items ?? []"
        row-key="id"
        :loading="lista.isLoading.value"
        clickable
        caption="Consultas del agente de voz"
        empty-text="El agente aún no recibió consultas con estos filtros."
        @row-click="(c) => (elegido = c)"
      >
        <template #cell-created_at="{ row }"
          ><span class="whitespace-nowrap text-muted tabular">{{ fechaHora(row.created_at) }}</span></template
        >
        <template #cell-tool="{ row }">
          <span class="font-medium">{{ TOOLS[row.tool] ?? row.tool }}</span>
          <span class="block text-xs text-muted">{{
            row.caller_id ? telefono(row.caller_id) : 'Número desconocido'
          }}</span>
        </template>
        <template #cell-mensaje="{ row }"
          ><span class="line-clamp-2 text-[13px] text-fg/80">{{ mensaje(row) }}</span></template
        >
        <template #cell-resultado="{ row }">
          <StatusBadge v-if="row.codigo_http >= 500" size="sm" tono="peligro" label="Error" />
          <StatusBadge v-else-if="!row.encontrado" size="sm" tono="aviso" label="Sin resultado" />
          <StatusBadge
            v-else-if="row.coincide_caller === false"
            size="sm"
            tono="info"
            label="Datos limitados"
          />
          <StatusBadge v-else size="sm" tono="exito" label="Respondida" />
        </template>
        <template #cell-latencia_ms="{ row }"
          ><span class="text-muted tabular">{{ row.latencia_ms }} ms</span></template
        >
      </DataTable>
      <PaginationBar
        v-if="lista.data.value"
        v-model:offset="offset"
        :total="lista.data.value.total"
        :limit="LIMITE"
      />
    </div>

    <SideSheet
      v-model:open="abierto"
      :title="elegido ? (TOOLS[elegido.tool] ?? elegido.tool) : ''"
      :description="
        elegido
          ? `${fechaHora(elegido.created_at)} · ${elegido.caller_id ? telefono(elegido.caller_id) : 'Número desconocido'}`
          : ''
      "
    >
      <div v-if="elegido" class="flex flex-col gap-4">
        <dl class="grid grid-cols-2 gap-3 rounded-xl bg-canvas p-4 text-sm">
          <div>
            <dt class="text-muted">Resultado</dt>
            <dd class="font-semibold">{{ elegido.encontrado ? 'Encontrado' : 'Sin resultado' }}</dd>
          </div>
          <div>
            <dt class="text-muted">Datos completos</dt>
            <dd class="font-semibold">
              {{
                elegido.coincide_caller === null ? '—' : elegido.coincide_caller ? 'Sí' : 'No (otro número)'
              }}
            </dd>
          </div>
          <div>
            <dt class="text-muted">Código HTTP</dt>
            <dd class="font-semibold tabular">{{ elegido.codigo_http }}</dd>
          </div>
          <div>
            <dt class="text-muted">Tiempo</dt>
            <dd class="font-semibold tabular">{{ elegido.latencia_ms }} ms</dd>
          </div>
        </dl>
        <div>
          <h3 class="mb-1.5 font-bold">Lo que preguntó</h3>
          <p class="text-sm text-muted">{{ parametros(elegido) }}</p>
        </div>
        <div>
          <h3 class="mb-1.5 font-bold">Lo que respondió el agente</h3>
          <p class="rounded-xl border border-line p-4 text-sm">{{ mensaje(elegido) }}</p>
        </div>
        <details class="text-sm">
          <summary class="cursor-pointer font-semibold">Respuesta completa (JSON)</summary>
          <pre
            class="mt-2 overflow-x-auto rounded-xl bg-canvas p-3 font-mono text-xs whitespace-pre-wrap break-all"
            >{{ JSON.stringify(elegido.resultado, null, 2) }}</pre>
        </details>
      </div>
    </SideSheet>
  </section>
</template>
