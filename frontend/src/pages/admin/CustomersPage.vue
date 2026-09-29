<script setup lang="ts">
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { refDebounced } from '@vueuse/core'
import { Mail, MessageCircle, Phone, Search } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, unwrap, type Schemas } from '@/api/client'
import BaseButton from '@/components/ui/BaseButton.vue'
import DataTable from '@/components/ui/DataTable.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import SideSheet from '@/components/ui/SideSheet.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { bsExacto, fechaCorta, fechaHora, iniciales, telefono, whatsappUrl } from '@/lib/format'
import { CANAL, ESTADO_ENCOMIENDA, ESTADO_VENTA, etiqueta } from '@/lib/labels'
import { ACCESO } from '@/lib/roles'
import { useAuthStore } from '@/stores/auth'

type Cliente = Schemas['ClienteOut']

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const texto = ref(typeof route.query.q === 'string' ? route.query.q : '')
const q = refDebounced(texto, 350)
const offset = ref(0)
const LIMITE = 20
watch(q, (v) => {
  offset.value = 0
  void router.replace({ query: v.trim() ? { q: v.trim() } : {} })
})

const lista = useQuery({
  queryKey: computed(() => ['admin-clientes', q.value.trim(), offset.value]),
  queryFn: () => unwrap(api.GET('/api/v1/admin/clientes', { params: { query: { q: q.value.trim() || undefined, limit: LIMITE, offset: offset.value } } })),
  placeholderData: keepPreviousData,
})

const elegido = ref<Cliente | null>(null)
const abierto = computed({ get: () => !!elegido.value, set: (v) => !v && (elegido.value = null) })
const verVentas = computed(() => auth.puede(ACCESO.ventas))
const verCarga = computed(() => auth.puede(ACCESO.encomiendas))
const ventas = useQuery({
  queryKey: computed(() => ['admin-ventas', 'cliente', elegido.value?.numero_documento]),
  queryFn: () => unwrap(api.GET('/api/v1/admin/ventas', { params: { query: { documento: elegido.value!.numero_documento, limit: 10 } } })),
  enabled: computed(() => !!elegido.value && verVentas.value),
})
const envios = useQuery({
  queryKey: computed(() => ['admin-encomiendas', 'cliente', elegido.value?.numero_documento]),
  queryFn: () => unwrap(api.GET('/api/v1/admin/encomiendas', { params: { query: { q: elegido.value!.numero_documento, limit: 10 } } })),
  enabled: computed(() => !!elegido.value && verCarga.value),
})

const columnas = [
  { key: 'nombre', label: 'Cliente' },
  { key: 'documento', label: 'Documento' },
  { key: 'telefono', label: 'Celular', hideSm: true },
  { key: 'email', label: 'Correo', hideSm: true },
]
const doc = (c: Cliente) => `${c.tipo_documento.toUpperCase()} ${c.numero_documento}${c.complemento ? `-${c.complemento}` : ''}${c.extension ? ` ${c.extension}` : ''}`
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader title="Clientes" subtitle="Pasajeros y remitentes registrados al comprar o enviar." />
    <div class="rounded-2xl border border-line bg-surface p-4">
      <TextInput v-model="texto" label="Buscar cliente" placeholder="Documento, celular o nombre" type="search" autocomplete="off" size="lg" autofocus>
        <template #icono><Search class="size-5" aria-hidden="true" /></template>
      </TextInput>
    </div>

    <ErrorState v-if="lista.isError.value" :error="lista.error.value" @retry="lista.refetch()" />
    <div v-else class="overflow-hidden rounded-2xl border border-line bg-surface">
      <DataTable
        :columns="columnas"
        :rows="lista.data.value?.items ?? []"
        row-key="id"
        :loading="lista.isLoading.value"
        clickable
        caption="Clientes"
        :empty-text="q ? `No encontramos clientes con «${q}».` : 'Aún no hay clientes.'"
        @row-click="(c) => (elegido = c)"
      >
        <template #cell-nombre="{ row }">
          <span class="flex items-center gap-3">
            <span class="flex size-9 shrink-0 items-center justify-center rounded-full bg-noche-100 text-xs font-bold text-noche-800 dark:bg-noche-700 dark:text-white" aria-hidden="true">{{ iniciales(`${row.nombres} ${row.apellidos}`) }}</span>
            <span class="font-medium">{{ row.nombres }} {{ row.apellidos }}</span>
          </span>
        </template>
        <template #cell-documento="{ row }"><span class="tabular">{{ doc(row) }}</span></template>
        <template #cell-telefono="{ row }">{{ telefono(row.telefono_e164) || '—' }}</template>
        <template #cell-email="{ row }"><span class="text-muted">{{ row.email ?? '—' }}</span></template>
      </DataTable>
      <PaginationBar v-if="lista.data.value" v-model:offset="offset" :total="lista.data.value.total" :limit="LIMITE" />
    </div>

    <SideSheet v-model:open="abierto" :title="elegido ? `${elegido.nombres} ${elegido.apellidos}` : ''" :description="elegido ? doc(elegido) : ''">
      <div v-if="elegido" class="flex flex-col gap-6">
        <div class="flex flex-wrap gap-2">
          <BaseButton v-if="elegido.telefono_e164" size="sm" variant="subtle" :href="`tel:${elegido.telefono_e164}`"><Phone class="size-4" aria-hidden="true" />{{ telefono(elegido.telefono_e164) }}</BaseButton>
          <BaseButton v-if="elegido.telefono_e164" size="sm" variant="subtle" :href="whatsappUrl(elegido.telefono_e164)" target="_blank" rel="noopener noreferrer"><MessageCircle class="size-4" aria-hidden="true" />WhatsApp</BaseButton>
          <BaseButton v-if="elegido.email" size="sm" variant="subtle" :href="`mailto:${elegido.email}`"><Mail class="size-4" aria-hidden="true" />Correo</BaseButton>
        </div>
        <dl v-if="elegido.fecha_nacimiento" class="text-sm"><dt class="text-muted">Fecha de nacimiento</dt><dd>{{ fechaCorta(elegido.fecha_nacimiento) }}</dd></dl>

        <section v-if="verVentas" class="flex flex-col gap-3">
          <h3 class="font-bold">Compras recientes</h3>
          <SkeletonBlock v-if="ventas.isLoading.value" class="h-24" />
          <EmptyState v-else-if="!ventas.data.value?.items.length" compact title="Sin compras" />
          <ul v-else class="flex flex-col divide-y divide-line rounded-xl border border-line">
            <li v-for="v in ventas.data.value.items" :key="v.codigo_reserva">
              <RouterLink :to="{ name: 'admin-ventas', query: { codigo: v.codigo_reserva } }" class="flex items-center justify-between gap-3 px-4 py-3 hover:bg-surface-2">
                <span>
                  <span class="codigo text-sm">{{ v.codigo_reserva }}</span>
                  <span class="block text-xs text-muted">{{ fechaHora(v.created_at) }} · {{ CANAL[v.canal] }}</span>
                </span>
                <span class="text-right">
                  <span class="block font-semibold tabular">{{ bsExacto(v.total_bs) }}</span>
                  <StatusBadge size="sm" v-bind="etiqueta(ESTADO_VENTA, v.estado)" />
                </span>
              </RouterLink>
            </li>
          </ul>
        </section>

        <section v-if="verCarga" class="flex flex-col gap-3">
          <h3 class="font-bold">Envíos como remitente</h3>
          <SkeletonBlock v-if="envios.isLoading.value" class="h-24" />
          <EmptyState v-else-if="!envios.data.value?.items.length" compact title="Sin envíos" />
          <ul v-else class="flex flex-col divide-y divide-line rounded-xl border border-line">
            <li v-for="e in envios.data.value.items" :key="e.numero_guia">
              <RouterLink :to="{ name: 'admin-encomienda', params: { guia: e.numero_guia } }" class="flex items-center justify-between gap-3 px-4 py-3 hover:bg-surface-2">
                <span>
                  <span class="codigo text-sm">{{ e.numero_guia }}</span>
                  <span class="block text-xs text-muted">Para {{ e.destinatario_nombre }} · {{ e.oficina_destino }}</span>
                </span>
                <StatusBadge size="sm" v-bind="etiqueta(ESTADO_ENCOMIENDA, e.estado)" />
              </RouterLink>
            </li>
          </ul>
        </section>
      </div>
    </SideSheet>
  </div>
</template>
