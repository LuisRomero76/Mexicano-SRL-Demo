<script setup lang="ts">
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { refDebounced } from '@vueuse/core'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, unwrap, type Schemas } from '@/api/client'
import BotLogSection from '@/components/admin/BotLogSection.vue'
import DataTable from '@/components/ui/DataTable.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import SelectInput from '@/components/ui/SelectInput.vue'
import SideSheet from '@/components/ui/SideSheet.vue'
import TabsBar from '@/components/ui/TabsBar.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { fechaHora } from '@/lib/format'

type Registro = Schemas['AuditoriaOut']

const route = useRoute()
const router = useRouter()
const vista = computed({
  get: () => (route.query.vista === 'bot' ? 'bot' : 'cambios'),
  set: (v: string) => void router.replace({ query: v === 'bot' ? { vista: 'bot' } : {} }),
})

const tabla = ref<string | null>(null)
const registroTexto = ref('')
const registro = refDebounced(registroTexto, 400)
const offset = ref(0)
const LIMITE = 30
watch([tabla, registro], () => (offset.value = 0))

const tablas = useQuery({
  queryKey: ['auditoria-tablas'],
  queryFn: () => unwrap(api.GET('/api/v1/admin/auditoria/tablas')),
  enabled: computed(() => vista.value === 'cambios'),
})
const lista = useQuery({
  queryKey: computed(() => ['auditoria', tabla.value, registro.value.trim(), offset.value]),
  enabled: computed(() => vista.value === 'cambios'),
  queryFn: () =>
    unwrap(
      api.GET('/api/v1/admin/auditoria', {
        params: {
          query: {
            tabla: tabla.value ?? undefined,
            registro_id: registro.value.trim() || undefined,
            limit: LIMITE,
            offset: offset.value,
          },
        },
      }),
    ),
  placeholderData: keepPreviousData,
})

const elegido = ref<Registro | null>(null)
const abierto = computed({ get: () => !!elegido.value, set: (v) => !v && (elegido.value = null) })

/** "ventas.cobrar" → "Ventas · cobrar" */
function accion(a: string): string {
  const [recurso, ...resto] = a.split('.')
  const r = recurso.replaceAll('_', ' ')
  return resto.length
    ? `${r[0].toUpperCase()}${r.slice(1)} · ${resto.join('.').replaceAll('_', ' ')}`
    : `${r[0].toUpperCase()}${r.slice(1)}`
}
function resumen(c: Registro['cambios']): string {
  if (!c) return '—'
  const claves = Object.keys(c)
  return claves.length ? claves.slice(0, 4).join(', ') + (claves.length > 4 ? '…' : '') : '—'
}
function valor(v: unknown): string {
  return typeof v === 'string' ? v : JSON.stringify(v, null, 2)
}

const columnas = [
  { key: 'created_at', label: 'Fecha' },
  { key: 'usuario', label: 'Usuario' },
  { key: 'accion', label: 'Acción' },
  { key: 'registro', label: 'Registro', hideSm: true },
  { key: 'cambios', label: 'Campos', hideSm: true },
]
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader
      title="Auditoría"
      subtitle="Quién cambió qué y cuándo, y qué consultan los clientes al agente de voz. Los registros no se pueden editar ni borrar."
    />
    <TabsBar
      v-model="vista"
      label="Registros"
      :tabs="[
        { key: 'cambios', label: 'Cambios del personal' },
        { key: 'bot', label: 'Consultas del agente de voz' },
      ]"
    />
    <BotLogSection v-if="vista === 'bot'" />
    <template v-else>
      <div class="grid gap-3 rounded-2xl border border-line bg-surface p-4 sm:grid-cols-2">
        <SelectInput
          v-model="tabla"
          label="Tabla"
          :options="[
            { value: null, label: 'Todas' },
            ...(tablas.data.value ?? []).map((t) => ({ value: t, label: t })),
          ]"
        />
        <TextInput
          v-model="registroTexto"
          label="Identificador del registro"
          placeholder="ID, código o guía"
          autocomplete="off"
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
          caption="Registro de auditoría"
          empty-text="No hay registros con estos filtros."
          @row-click="(r) => (elegido = r)"
        >
          <template #cell-created_at="{ row }"
            ><span class="whitespace-nowrap text-muted tabular">{{
              fechaHora(row.created_at)
            }}</span></template
          >
          <template #cell-usuario="{ row }">{{
            row.usuario ?? (row.usuario_id ? 'Usuario eliminado' : 'Sistema / cliente')
          }}</template>
          <template #cell-accion="{ row }"
            ><span class="font-medium">{{ accion(row.accion) }}</span></template
          >
          <template #cell-registro="{ row }"
            ><span class="text-muted">{{ row.tabla }}</span>
            <span class="codigo text-xs">{{
              row.registro_id.length > 14 ? `${row.registro_id.slice(0, 8)}…` : row.registro_id
            }}</span></template
          >
          <template #cell-cambios="{ row }"
            ><span class="text-muted">{{ resumen(row.cambios) }}</span></template
          >
        </DataTable>
        <PaginationBar
          v-if="lista.data.value"
          v-model:offset="offset"
          :total="lista.data.value.total"
          :limit="LIMITE"
        />
      </div>
    </template>

    <SideSheet
      v-model:open="abierto"
      :title="elegido ? accion(elegido.accion) : ''"
      :description="
        elegido ? `${fechaHora(elegido.created_at)} · ${elegido.usuario ?? 'Sistema / cliente'}` : ''
      "
    >
      <div v-if="elegido" class="flex flex-col gap-4">
        <dl class="grid grid-cols-2 gap-3 rounded-xl bg-canvas p-4 text-sm">
          <div>
            <dt class="text-muted">Tabla</dt>
            <dd class="font-semibold">{{ elegido.tabla }}</dd>
          </div>
          <div class="min-w-0">
            <dt class="text-muted">Registro</dt>
            <dd class="codigo text-xs break-all">{{ elegido.registro_id }}</dd>
          </div>
        </dl>
        <h3 class="font-bold">Datos registrados</h3>
        <p v-if="!elegido.cambios || !Object.keys(elegido.cambios).length" class="text-sm text-muted">
          Sin detalle de cambios.
        </p>
        <dl v-else class="flex flex-col divide-y divide-line rounded-xl border border-line">
          <div v-for="(val, clave) in elegido.cambios" :key="clave" class="flex flex-col gap-1 px-4 py-3">
            <dt class="text-xs font-semibold text-muted">{{ clave }}</dt>
            <dd>
              <pre class="font-mono text-xs whitespace-pre-wrap break-all">{{ valor(val) }}</pre>
            </dd>
          </div>
        </dl>
      </div>
    </SideSheet>
  </div>
</template>
