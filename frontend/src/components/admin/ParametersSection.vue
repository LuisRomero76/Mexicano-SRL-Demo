<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { Pencil } from '@lucide/vue'
import { ref } from 'vue'
import { ApiError, api, unwrap, type Schemas } from '@/api/client'
import AppDialog from '@/components/ui/AppDialog.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import DataTable from '@/components/ui/DataTable.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import TextArea from '@/components/ui/TextArea.vue'
import { useToastStore } from '@/stores/toast'

type Parametro = Schemas['ParametroOut']

const avisos = useToastStore()
const cliente = useQueryClient()
const lista = useQuery({
  queryKey: ['parametros'],
  queryFn: () => unwrap(api.GET('/api/v1/admin/parametros', { params: { query: { limit: 100 } } })),
})

const editando = ref<Parametro | null>(null)
const texto = ref('')
const error = ref<string | null>(null)
function abrir(p: Parametro): void {
  editando.value = p
  texto.value = JSON.stringify(p.valor, null, 2)
  error.value = null
}
const guardar = useMutation({
  mutationFn: (valor: unknown) =>
    unwrap(api.PATCH('/api/v1/admin/parametros/{item_id}', { params: { path: { item_id: editando.value!.clave } }, body: { valor } })),
  onSuccess: () => {
    avisos.exito('Parámetro actualizado')
    editando.value = null
    void cliente.invalidateQueries({ queryKey: ['parametros'] })
  },
  onError: (e) => avisos.error('No se pudo guardar', e instanceof ApiError ? e.message : undefined),
})
function enviar(): void {
  try {
    guardar.mutate(JSON.parse(texto.value))
  } catch {
    error.value = 'No es un valor JSON válido (usa comillas dobles en los textos).'
  }
}
const vista = (v: unknown) => {
  const t = JSON.stringify(v)
  return t.length > 80 ? `${t.slice(0, 80)}…` : t
}
</script>

<template>
  <section class="flex flex-col gap-4">
    <div>
      <h2 class="text-lg font-bold">Parámetros de negocio</h2>
      <p class="mt-0.5 text-sm text-muted">Reglas que usa el sistema (tiempos de reserva, retenciones, franquicias). Solo el administrador los modifica.</p>
    </div>
    <ErrorState v-if="lista.isError.value" :error="lista.error.value" @retry="lista.refetch()" />
    <div v-else class="overflow-hidden rounded-2xl border border-line bg-surface">
      <DataTable
        :columns="[
          { key: 'clave', label: 'Clave' },
          { key: 'descripcion', label: 'Descripción', hideSm: true },
          { key: 'valor', label: 'Valor' },
          { key: 'acciones', label: '', align: 'right' },
        ]"
        :rows="lista.data.value?.items ?? []"
        row-key="clave"
        :loading="lista.isLoading.value"
        caption="Parámetros"
      >
        <template #cell-clave="{ row }"><span class="codigo text-xs">{{ row.clave }}</span></template>
        <template #cell-descripcion="{ row }"><span class="text-muted">{{ row.descripcion ?? '—' }}</span></template>
        <template #cell-valor="{ row }"><code class="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-xs">{{ vista(row.valor) }}</code></template>
        <template #cell-acciones="{ row }">
          <BaseButton size="sm" variant="ghost" icon-only aria-label="Editar parámetro" @click="abrir(row)"><Pencil class="size-4" /></BaseButton>
        </template>
      </DataTable>
    </div>

    <AppDialog :open="!!editando" :title="editando?.clave ?? ''" :description="editando?.descripcion ?? undefined" @update:open="(v) => !v && (editando = null)">
      <TextArea v-model="texto" label="Valor (JSON)" :rows="8" class="font-mono text-sm" :error="error" />
      <template #footer>
        <BaseButton variant="subtle" @click="editando = null">Cancelar</BaseButton>
        <BaseButton :loading="guardar.isPending.value" @click="enviar">Guardar</BaseButton>
      </template>
    </AppDialog>
  </section>
</template>
