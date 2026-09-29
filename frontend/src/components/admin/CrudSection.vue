<script setup lang="ts">
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { Pencil, Plus, Search, Trash2 } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { ApiError } from '@/api/client'
import { pedir, type Fila, type Pagina } from '@/api/crud'
import AppDialog from '@/components/ui/AppDialog.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import CheckboxInput from '@/components/ui/CheckboxInput.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import DataTable from '@/components/ui/DataTable.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import SelectInput, { type Opcion } from '@/components/ui/SelectInput.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import TextArea from '@/components/ui/TextArea.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { DIAS } from '@/lib/labels'
import { useToastStore } from '@/stores/toast'

export interface ColumnaCrud {
  key: string
  label: string
  align?: 'left' | 'right' | 'center'
  hideSm?: boolean
  /** Texto a mostrar; por defecto el valor del campo. */
  valor?: (fila: Fila) => string | number | null | undefined
  mono?: boolean
  /** Muestra un distintivo Activo/Inactivo. */
  estado?: boolean
}

export interface CampoCrud {
  key: string
  label: string
  tipo?: 'text' | 'password' | 'email' | 'number' | 'decimal' | 'select' | 'checkbox' | 'date' | 'time' | 'textarea' | 'dias' | 'lista'
  opciones?: Opcion[]
  requerido?: boolean
  ayuda?: string
  /** Solo al crear (clave, relaciones fijas). */
  soloCrear?: boolean
  /** Solo al editar (p. ej. "activo"). */
  soloEditar?: boolean
  ancho?: 'full'
  valorInicial?: unknown
}

const props = withDefaults(
  defineProps<{
    titulo: string
    descripcion?: string
    ruta: string
    columnas: ColumnaCrud[]
    campos: CampoCrud[]
    clave?: string
    paginado?: boolean
    puedeCrear?: boolean
    puedeEditar?: boolean
    puedeEliminar?: boolean
    nombreItem?: string
    /** Filtro de texto local sobre estos campos. */
    buscarEn?: string[]
    query?: Record<string, unknown>
  }>(),
  { clave: 'id', paginado: true, puedeCrear: true, puedeEditar: true, nombreItem: 'registro' },
)
defineSlots<{ acciones?: (p: { fila: Fila }) => unknown; filtros?: () => unknown }>()

const avisos = useToastStore()
const cliente = useQueryClient()
const offset = ref(0)
const LIMITE = 25
watch(() => props.query, () => (offset.value = 0), { deep: true })

const lista = useQuery({
  queryKey: computed(() => ['crud', props.ruta, props.query ?? {}, props.paginado ? offset.value : 0]),
  queryFn: async (): Promise<Pagina<Fila>> => {
    if (!props.paginado) {
      const items = await pedir<Fila[]>('GET', props.ruta, { params: { query: props.query } })
      return { total: items.length, limit: items.length, offset: 0, items }
    }
    return pedir<Pagina<Fila>>('GET', props.ruta, { params: { query: { ...props.query, limit: LIMITE, offset: offset.value } } })
  },
  placeholderData: keepPreviousData,
})

const texto = ref('')
const filas = computed(() => {
  const items = lista.data.value?.items ?? []
  const t = texto.value.trim().toLowerCase()
  if (!t || !props.buscarEn?.length) return items
  return items.filter((f) => props.buscarEn!.some((k) => String(f[k] ?? '').toLowerCase().includes(t)))
})

const columnasTabla = computed(() => [...props.columnas, { key: '__acciones', label: '', align: 'right' as const }])

function mostrar(c: ColumnaCrud, f: Fila): string {
  const v = c.valor ? c.valor(f) : f[c.key]
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'boolean') return v ? 'Sí' : 'No'
  return String(v)
}

// --- Formulario ---
const editando = ref<Fila | null>(null)
const abierto = ref(false)
const form = reactive<Fila>({})
const errores = ref<Record<string, string>>({})
const camposVisibles = computed(() => props.campos.filter((c) => (editando.value ? !c.soloCrear : !c.soloEditar)))

function aTexto(c: CampoCrud, v: unknown): unknown {
  if (c.tipo === 'checkbox') return !!v
  if (c.tipo === 'dias') return Array.isArray(v) ? [...v] : []
  if (c.tipo === 'lista') return Array.isArray(v) ? v.join(', ') : ''
  if (c.tipo === 'time' && typeof v === 'string') return v.slice(0, 5)
  if (c.tipo === 'select') return v ?? null
  return v === null || v === undefined ? '' : String(v)
}
function abrir(fila?: Fila): void {
  editando.value = fila ?? null
  errores.value = {}
  for (const c of props.campos) form[c.key] = aTexto(c, fila ? fila[c.key] : c.valorInicial ?? (c.tipo === 'checkbox' ? false : c.tipo === 'dias' ? [1, 2, 3, 4, 5, 6, 7] : null))
  abierto.value = true
}
function convertir(c: CampoCrud, v: unknown): unknown {
  if (c.tipo === 'checkbox' || c.tipo === 'dias' || c.tipo === 'select') return v
  if (c.tipo === 'lista') {
    const l = String(v ?? '').split(',').map((s) => s.trim()).filter(Boolean)
    return l.length ? l : null
  }
  const s = String(v ?? '').trim()
  if (!s) return null
  if (c.tipo === 'number') return Number.parseInt(s, 10)
  if (c.tipo === 'decimal') return Number(s.replace(',', '.'))
  return s
}
function cuerpo(): Record<string, unknown> | null {
  const salida: Record<string, unknown> = {}
  const e: Record<string, string> = {}
  for (const c of camposVisibles.value) {
    const v = convertir(c, form[c.key])
    if (c.requerido && (v === null || (Array.isArray(v) && !v.length))) e[c.key] = 'Obligatorio'
    if ((c.tipo === 'number' || c.tipo === 'decimal') && v !== null && Number.isNaN(v)) e[c.key] = 'Número inválido'
    if (editando.value) {
      const original = convertir(c, aTexto(c, editando.value[c.key]))
      if (JSON.stringify(original) === JSON.stringify(v)) continue
    }
    salida[c.key] = v
  }
  errores.value = e
  return Object.keys(e).length ? null : salida
}

const guardar = useMutation({
  mutationFn: (datos: Record<string, unknown>) =>
    editando.value
      ? pedir<Fila>('PATCH', `${props.ruta}/${encodeURIComponent(editando.value[props.clave])}`, { body: datos })
      : pedir<Fila>('POST', props.ruta, { body: datos }),
  onSuccess: () => {
    avisos.exito(editando.value ? 'Cambios guardados' : `${props.nombreItem[0].toUpperCase()}${props.nombreItem.slice(1)} creado`)
    abierto.value = false
    void cliente.invalidateQueries({ queryKey: ['crud', props.ruta] })
  },
  onError: (e) => {
    if (e instanceof ApiError) errores.value = Object.fromEntries(Object.entries(e.camposInvalidos).map(([k, v]) => [k.split('.').pop()!, v]))
    avisos.error('No se pudo guardar', e instanceof ApiError ? e.message : undefined)
  },
})
function enviar(): void {
  const datos = cuerpo()
  if (!datos) return
  if (editando.value && !Object.keys(datos).length) {
    abierto.value = false
    return
  }
  guardar.mutate(datos)
}

// --- Eliminación ---
const eliminando = ref<Fila | null>(null)
const eliminar = useMutation({
  mutationFn: () => pedir('DELETE', `${props.ruta}/${encodeURIComponent(eliminando.value![props.clave])}`),
  onSuccess: () => {
    avisos.exito('Eliminado')
    eliminando.value = null
    void cliente.invalidateQueries({ queryKey: ['crud', props.ruta] })
  },
  onError: (e) => avisos.error('No se pudo eliminar', e instanceof ApiError ? e.message : undefined),
})

function toggleDia(key: string, dia: number): void {
  const actual: number[] = form[key] ?? []
  form[key] = actual.includes(dia) ? actual.filter((d) => d !== dia) : [...actual, dia].sort()
}
defineExpose({ abrir })
</script>

<template>
  <section class="flex flex-col gap-4">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h2 class="text-lg font-bold">{{ titulo }}</h2>
        <p v-if="descripcion" class="mt-0.5 text-sm text-muted">{{ descripcion }}</p>
      </div>
      <div class="flex flex-wrap items-end gap-2">
        <slot name="filtros" />
        <TextInput v-if="buscarEn?.length" v-model="texto" label="Buscar" type="search" class="w-56" autocomplete="off">
          <template #icono><Search class="size-4" aria-hidden="true" /></template>
        </TextInput>
        <BaseButton v-if="puedeCrear" size="sm" class="h-11" @click="abrir()"><Plus class="size-4" aria-hidden="true" />Nuevo</BaseButton>
      </div>
    </div>

    <ErrorState v-if="lista.isError.value" :error="lista.error.value" @retry="lista.refetch()" />
    <div v-else class="overflow-hidden rounded-2xl border border-line bg-surface">
      <DataTable :columns="columnasTabla" :rows="filas" :row-key="(f: Fila) => String(f[clave])" :loading="lista.isLoading.value" :caption="titulo">
        <template v-for="c in columnas" :key="c.key" #[`cell-${c.key}`]="{ row }">
          <StatusBadge v-if="c.estado" size="sm" :tono="row[c.key] ? 'exito' : 'neutro'" :label="row[c.key] ? 'Activo' : 'Inactivo'" />
          <span v-else :class="c.mono ? 'codigo' : ''">{{ mostrar(c, row) }}</span>
        </template>
        <template #cell-__acciones="{ row }">
          <div class="flex justify-end gap-1">
            <slot name="acciones" :fila="row" />
            <BaseButton v-if="puedeEditar" size="sm" variant="ghost" icon-only :aria-label="`Editar ${nombreItem}`" @click="abrir(row)"><Pencil class="size-4" /></BaseButton>
            <BaseButton v-if="puedeEliminar" size="sm" variant="ghost" icon-only class="text-peligro-600" :aria-label="`Eliminar ${nombreItem}`" @click="eliminando = row"><Trash2 class="size-4" /></BaseButton>
          </div>
        </template>
      </DataTable>
      <PaginationBar v-if="paginado && lista.data.value && lista.data.value.total > LIMITE" v-model:offset="offset" :total="lista.data.value.total" :limit="LIMITE" />
    </div>

    <AppDialog v-model:open="abierto" :title="editando ? `Editar ${nombreItem}` : `Nuevo ${nombreItem}`" size="lg">
      <form :id="`form-${ruta}`" class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="enviar">
        <template v-for="c in camposVisibles" :key="c.key">
          <CheckboxInput v-if="c.tipo === 'checkbox'" v-model="form[c.key]" :label="c.label" :hint="c.ayuda" class="self-center" />
          <SelectInput
            v-else-if="c.tipo === 'select'"
            v-model="form[c.key]"
            :label="c.label"
            :options="c.opciones ?? []"
            :required="c.requerido"
            :hint="c.ayuda"
            :error="errores[c.key]"
            placeholder="Elige una opción"
            :class="c.ancho === 'full' ? 'sm:col-span-2' : ''"
          />
          <TextArea
            v-else-if="c.tipo === 'textarea'"
            v-model="form[c.key]"
            :label="c.label"
            :required="c.requerido"
            :hint="c.ayuda"
            :error="errores[c.key]"
            :rows="4"
            class="sm:col-span-2"
          />
          <fieldset v-else-if="c.tipo === 'dias'" class="sm:col-span-2">
            <legend class="mb-2 text-[13px] font-semibold">{{ c.label }}</legend>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="(d, i) in DIAS"
                :key="d"
                type="button"
                class="h-9 min-w-11 rounded-lg border px-2 text-sm font-semibold"
                :class="(form[c.key] ?? []).includes(i + 1) ? 'border-carmin-600 bg-carmin-50 text-carmin-800 dark:bg-carmin-800/30 dark:text-carmin-100' : 'border-line-strong text-muted'"
                :aria-pressed="(form[c.key] ?? []).includes(i + 1)"
                @click="toggleDia(c.key, i + 1)"
              >
                {{ d.slice(0, 3) }}
              </button>
            </div>
            <p v-if="errores[c.key]" class="mt-1 text-[13px] text-peligro-600">{{ errores[c.key] }}</p>
          </fieldset>
          <TextInput
            v-else
            v-model="form[c.key]"
            :label="c.label"
            :type="c.tipo === 'date' || c.tipo === 'time' || c.tipo === 'password' || c.tipo === 'email' ? c.tipo : 'text'"
            :autocomplete="c.tipo === 'password' ? 'new-password' : 'off'"
            :inputmode="c.tipo === 'number' ? 'numeric' : c.tipo === 'decimal' ? 'decimal' : undefined"
            :required="c.requerido"
            :hint="c.ayuda"
            :error="errores[c.key]"
            :class="c.ancho === 'full' ? 'sm:col-span-2' : ''"
          />
        </template>
      </form>
      <template #footer>
        <BaseButton variant="subtle" @click="abierto = false">Cancelar</BaseButton>
        <BaseButton type="submit" :form="`form-${ruta}`" :loading="guardar.isPending.value">{{ editando ? 'Guardar cambios' : 'Crear' }}</BaseButton>
      </template>
    </AppDialog>

    <ConfirmDialog
      :open="!!eliminando"
      :title="`Eliminar ${nombreItem}`"
      description="Esta acción no se puede deshacer."
      confirm-label="Eliminar"
      danger
      :loading="eliminar.isPending.value"
      @update:open="(v) => !v && (eliminando = null)"
      @confirm="eliminar.mutate()"
    />
  </section>
</template>
