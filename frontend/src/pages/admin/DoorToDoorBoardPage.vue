<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ChevronLeft, ChevronRight, MapPin, MessageCircle, Package, Phone, Plus, Truck, UserRound } from '@lucide/vue'
import { computed, reactive, ref } from 'vue'
import { z } from 'zod'
import { ApiError, api, unwrap, type Schemas } from '@/api/client'
import AppDialog from '@/components/ui/AppDialog.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import CheckboxInput from '@/components/ui/CheckboxInput.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SelectInput from '@/components/ui/SelectInput.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import TabsBar from '@/components/ui/TabsBar.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { bsExacto, diaSemanaISO, fechaLarga, hoyISO, sumarDias, telefono, whatsappUrl } from '@/lib/format'
import { ESTADO_PUERTA, TRANSICIONES_PUERTA, etiqueta } from '@/lib/labels'
import { celular, documento, erroresDe, nombre } from '@/lib/validacion'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

type Solicitud = Schemas['SolicitudPuertaAdminOut']
type Estado = Schemas['EstadoSolicitudPuerta']

const auth = useAuthStore()
const avisos = useToastStore()
const cliente = useQueryClient()
const esRepartidor = computed(() => auth.usuario?.rol === 'repartidor')
const puedeVerVehiculos = computed(() => auth.puede(['supervisor', 'encargado_bodega', 'repartidor']))

/** Próximo día hábil (el servicio atiende de lunes a viernes). */
function habil(iso: string, paso = 1): string {
  let d = iso
  while (diaSemanaISO(d) > 5) d = sumarDias(d, paso)
  return d
}
const fecha = ref(habil(hoyISO()))
const ciudad = ref<string>('Sucre')
const soloMias = ref(esRepartidor.value)
const pestanaMovil = ref('solicitada')

const lista = useQuery({
  queryKey: computed(() => ['puerta', fecha.value, ciudad.value]),
  queryFn: () => unwrap(api.GET('/api/v1/admin/puerta-a-puerta', { params: { query: { fecha: fecha.value, ciudad: ciudad.value, limit: 100 } } })),
  refetchInterval: 60_000,
})
const repartidores = useQuery({
  queryKey: ['directorio', 'repartidor'],
  queryFn: () => unwrap(api.GET('/api/v1/admin/usuarios/directorio', { params: { query: { rol: 'repartidor' } } })),
})
const vehiculos = useQuery({
  queryKey: ['vehiculos-carga'],
  queryFn: () => unwrap(api.GET('/api/v1/admin/vehiculos-carga', { params: { query: { limit: 100 } } })),
  enabled: puedeVerVehiculos,
})

const visibles = computed(() => {
  const items = lista.data.value?.items ?? []
  return soloMias.value ? items.filter((s) => s.repartidor_usuario_id === auth.usuario?.id) : items
})
const COLUMNAS = [
  { key: 'solicitada', label: 'Por confirmar', estados: ['solicitada'] },
  { key: 'confirmada', label: 'Confirmadas', estados: ['confirmada'] },
  { key: 'en_camino', label: 'En camino', estados: ['en_camino'] },
  { key: 'cerradas', label: 'Cerradas', estados: ['completada', 'fallida', 'cancelada'] },
]
const porColumna = computed(() =>
  Object.fromEntries(COLUMNAS.map((c) => [c.key, visibles.value.filter((s) => c.estados.includes(s.estado))])) as Record<string, Solicitud[]>,
)
const resumen = computed(() => ({
  entregas: visibles.value.filter((s) => s.tipo === 'entrega').length,
  recojos: visibles.value.filter((s) => s.tipo === 'recojo').length,
  sinAsignar: visibles.value.filter((s) => !s.repartidor_usuario_id && !['completada', 'cancelada'].includes(s.estado)).length,
}))

function moverDia(paso: number): void {
  fecha.value = habil(sumarDias(fecha.value, paso), paso)
}

// --- Cambios de estado y asignación ---
const actualizar = useMutation({
  mutationFn: (v: { codigo: string; body: Schemas['SolicitudPuertaUpdate'] }) =>
    unwrap(api.PATCH('/api/v1/admin/puerta-a-puerta/{codigo}', { params: { path: { codigo: v.codigo } }, body: v.body })),
  onSuccess: (r) => {
    avisos.exito(`${r.codigo}: ${etiqueta(ESTADO_PUERTA, r.estado).label}`)
    asignando.value = null
    void cliente.invalidateQueries({ queryKey: ['puerta'] })
  },
  onError: (e) => avisos.error('No se pudo actualizar', e instanceof ApiError ? e.message : undefined),
})
const TEXTO_ACCION: Record<string, string> = {
  confirmada: 'Confirmar',
  en_camino: 'Salir a ruta',
  completada: 'Completar',
  fallida: 'Marcar fallida',
  cancelada: 'Cancelar',
}

const asignando = ref<Solicitud | null>(null)
const asignacion = reactive({ repartidor: null as string | null, vehiculo: null as number | null })
function abrirAsignar(s: Solicitud): void {
  asignacion.repartidor = s.repartidor_usuario_id ?? null
  asignacion.vehiculo = s.vehiculo_carga_id ?? null
  asignando.value = s
}
function guardarAsignacion(): void {
  if (!asignando.value) return
  actualizar.mutate({
    codigo: asignando.value.codigo,
    body: { repartidor_usuario_id: asignacion.repartidor, vehiculo_carga_id: asignacion.vehiculo },
  })
}

// --- Nueva solicitud (recibida por teléfono o WhatsApp) ---
const creando = ref(false)
const nueva = reactive({
  tipo: 'recojo' as Schemas['TipoSolicitudPuerta'],
  canal: 'telefono' as 'telefono' | 'whatsapp_chat',
  documento: '',
  nombres: '',
  apellidos: '',
  telefono: '',
  direccion: '',
  referencia: '',
  fecha: habil(sumarDias(hoyISO(), 1)),
  peso: '',
  descripcion: '',
  guia: '',
})
const erroresNueva = ref<Record<string, string>>({})
const esquemaNueva = z.object({
  documento,
  nombres: nombre,
  apellidos: nombre,
  telefono: celular,
  direccion: z.string().trim().min(5, 'Indica la dirección'),
  fecha: z.string().refine((f) => diaSemanaISO(f) <= 5, 'Solo de lunes a viernes'),
})
const crear = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/admin/puerta-a-puerta', {
        params: { query: { canal: nueva.canal } },
        body: {
          tipo: nueva.tipo,
          ciudad: ciudad.value,
          cliente: { numero_documento: nueva.documento.trim(), nombres: nueva.nombres.trim(), apellidos: nueva.apellidos.trim() },
          telefono: nueva.telefono.trim(),
          direccion: nueva.direccion.trim(),
          referencia: nueva.referencia.trim() || null,
          fecha_programada: nueva.fecha,
          peso_estimado_kg: nueva.peso ? Number(nueva.peso.replace(',', '.')) : null,
          descripcion: nueva.descripcion.trim() || null,
          numero_guia: nueva.tipo === 'entrega' && nueva.guia.trim() ? nueva.guia.trim() : null,
        },
      }),
    ),
  onSuccess: (r) => {
    avisos.exito(`Solicitud ${r.codigo} registrada`, r.mensaje)
    creando.value = false
    fecha.value = r.fecha_programada
    void cliente.invalidateQueries({ queryKey: ['puerta'] })
  },
  onError: (e) => {
    if (e instanceof ApiError && e.code === 'datos_invalidos') erroresNueva.value = e.camposInvalidos
    avisos.error('No se pudo registrar', e instanceof ApiError ? e.message : undefined)
  },
})
function enviarNueva(): void {
  erroresNueva.value = erroresDe(esquemaNueva.safeParse(nueva))
  if (nueva.tipo === 'entrega' && !/^\d{8}$/.test(nueva.guia.trim())) erroresNueva.value.guia = 'Guía de 8 dígitos'
  if (!Object.keys(erroresNueva.value).length) crear.mutate()
}
const placa = (id: number | null | undefined) => vehiculos.data.value?.items.find((v) => v.id === id)?.placa
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader title="Puerta a puerta" subtitle="Entregas de 08:00 a 12:00 y recojos de 14:00 a 17:00, de lunes a viernes.">
      <BaseButton size="sm" class="h-10" @click="creando = true"><Plus class="size-4" aria-hidden="true" />Nueva solicitud</BaseButton>
    </PageHeader>

    <div class="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-4 md:flex-row md:items-end md:justify-between">
      <div class="flex flex-wrap items-end gap-3">
        <SegmentedControl v-model="ciudad" label="Ciudad" variant="switch" :options="[{ value: 'Sucre', label: 'Sucre' }, { value: 'Santa Cruz', label: 'Santa Cruz' }]" />
        <div class="flex items-end gap-1">
          <BaseButton variant="subtle" icon-only aria-label="Día hábil anterior" @click="moverDia(-1)"><ChevronLeft class="size-4" /></BaseButton>
          <TextInput v-model="fecha" label="Fecha" type="date" class="w-44" />
          <BaseButton variant="subtle" icon-only aria-label="Día hábil siguiente" @click="moverDia(1)"><ChevronRight class="size-4" /></BaseButton>
        </div>
        <CheckboxInput v-if="esRepartidor" v-model="soloMias" label="Solo mis asignaciones" class="mb-2.5" />
      </div>
      <dl class="flex gap-5 text-sm">
        <div><dt class="text-muted">Entregas</dt><dd class="text-xl font-bold tabular">{{ resumen.entregas }}</dd></div>
        <div><dt class="text-muted">Recojos</dt><dd class="text-xl font-bold tabular">{{ resumen.recojos }}</dd></div>
        <div><dt class="text-muted">Sin repartidor</dt><dd class="text-xl font-bold tabular" :class="resumen.sinAsignar ? 'text-aviso-700' : ''">{{ resumen.sinAsignar }}</dd></div>
      </dl>
    </div>

    <p class="-mt-2 text-sm font-medium text-muted">{{ fechaLarga(fecha) }}</p>

    <ErrorState v-if="lista.isError.value" :error="lista.error.value" @retry="lista.refetch()" />
    <template v-else>
      <TabsBar v-model="pestanaMovil" class="xl:hidden" label="Columnas del tablero" :tabs="COLUMNAS.map((c) => ({ key: c.key, label: `${c.label} (${porColumna[c.key]?.length ?? 0})` }))" />
      <div class="grid gap-4 xl:grid-cols-4">
        <section
          v-for="c in COLUMNAS"
          :key="c.key"
          class="flex-col gap-3 rounded-2xl bg-surface-2/60 p-3"
          :class="pestanaMovil === c.key ? 'flex' : 'hidden xl:flex'"
          :aria-label="c.label"
        >
          <header class="hidden items-center justify-between px-1 xl:flex">
            <h2 class="text-sm font-bold">{{ c.label }}</h2>
            <span class="rounded-full bg-surface px-2 py-0.5 text-xs font-semibold tabular">{{ porColumna[c.key]?.length ?? 0 }}</span>
          </header>
          <SkeletonBlock v-if="lista.isLoading.value" class="h-40" />
          <p v-else-if="!porColumna[c.key]?.length" class="rounded-xl border border-dashed border-line-strong p-6 text-center text-sm text-muted">Nada por aquí.</p>
          <article v-for="s in porColumna[c.key]" :key="s.id" class="flex flex-col gap-3 rounded-xl border border-line bg-surface p-4 shadow-suave">
            <div class="flex items-start justify-between gap-2">
              <div>
                <p class="codigo text-sm">{{ s.codigo }}</p>
                <p class="text-xs font-semibold tracking-wide uppercase" :class="s.tipo === 'entrega' ? 'text-turquesa-700 dark:text-turquesa-200' : 'text-carmin-600 dark:text-carmin-200'">
                  {{ s.tipo === 'entrega' ? 'Entrega' : 'Recojo' }} · {{ s.franja_texto }}
                </p>
              </div>
              <StatusBadge size="sm" v-bind="etiqueta(ESTADO_PUERTA, s.estado)" />
            </div>
            <div class="flex flex-col gap-1.5 text-sm">
              <p class="font-semibold">{{ s.cliente }}</p>
              <p class="flex gap-1.5 text-fg/85"><MapPin class="mt-0.5 size-4 shrink-0 text-muted" aria-hidden="true" /><span>{{ s.direccion }}<span v-if="s.referencia" class="block text-xs text-muted">{{ s.referencia }}</span></span></p>
              <p v-if="s.peso_estimado_kg || s.descripcion" class="flex gap-1.5 text-fg/85">
                <Package class="mt-0.5 size-4 shrink-0 text-muted" aria-hidden="true" />
                <span>{{ [s.peso_estimado_kg ? `${s.peso_estimado_kg} kg` : '', s.descripcion].filter(Boolean).join(' · ') }}</span>
              </p>
              <RouterLink v-if="s.numero_guia" :to="{ name: 'admin-encomienda', params: { guia: s.numero_guia } }" class="codigo text-xs text-carmin-600 hover:underline dark:text-carmin-200">Guía {{ s.numero_guia }}</RouterLink>
              <p v-if="s.costo_bs" class="text-xs text-muted">Costo {{ bsExacto(s.costo_bs) }}</p>
            </div>
            <div class="flex items-center gap-2">
              <a :href="`tel:${s.contacto_telefono_e164}`" class="inline-flex h-8 items-center gap-1.5 rounded-lg bg-surface-2 px-2.5 text-xs font-semibold hover:bg-line" :aria-label="`Llamar a ${s.cliente}`">
                <Phone class="size-3.5" aria-hidden="true" />{{ telefono(s.contacto_telefono_e164) }}
              </a>
              <a :href="whatsappUrl(s.contacto_telefono_e164, s.mensaje)" target="_blank" rel="noopener noreferrer" class="inline-flex size-8 items-center justify-center rounded-lg bg-exito-50 text-exito-700 hover:bg-exito-100" aria-label="Escribir por WhatsApp">
                <MessageCircle class="size-4" aria-hidden="true" />
              </a>
            </div>
            <button
              type="button"
              class="flex items-center gap-2 rounded-lg border border-dashed border-line-strong px-2.5 py-2 text-left text-xs hover:border-noche-400 disabled:cursor-default disabled:hover:border-line-strong"
              :disabled="['completada', 'cancelada'].includes(s.estado)"
              @click="abrirAsignar(s)"
            >
              <UserRound class="size-4 text-muted" aria-hidden="true" />
              <span class="flex-1" :class="s.repartidor ? 'font-semibold' : 'text-aviso-700'">{{ s.repartidor ?? 'Asignar repartidor' }}</span>
              <span v-if="s.vehiculo || placa(s.vehiculo_carga_id)" class="inline-flex items-center gap-1 text-muted"><Truck class="size-3.5" aria-hidden="true" />{{ s.vehiculo ?? placa(s.vehiculo_carga_id) }}</span>
            </button>
            <div v-if="TRANSICIONES_PUERTA[s.estado]?.length" class="flex flex-wrap gap-2">
              <BaseButton
                v-for="t in TRANSICIONES_PUERTA[s.estado]"
                :key="t"
                size="sm"
                :variant="t === 'cancelada' || t === 'fallida' ? 'ghost' : t === 'completada' ? 'success' : 'primary'"
                :class="t === 'cancelada' || t === 'fallida' ? 'text-peligro-600' : 'flex-1'"
                :loading="actualizar.isPending.value && actualizar.variables.value?.codigo === s.codigo && actualizar.variables.value?.body.estado === t"
                @click="actualizar.mutate({ codigo: s.codigo, body: { estado: t as Estado } })"
              >
                {{ TEXTO_ACCION[t] ?? t }}
              </BaseButton>
            </div>
          </article>
        </section>
      </div>
    </template>

    <AppDialog :open="!!asignando" title="Asignar" :description="asignando ? `${asignando.codigo} · ${asignando.cliente}` : ''" @update:open="(v) => !v && (asignando = null)">
      <div class="flex flex-col gap-4">
        <SelectInput
          v-model="asignacion.repartidor"
          label="Repartidor"
          placeholder="Sin asignar"
          :options="(repartidores.data.value ?? []).map((r) => ({ value: r.id, label: r.nombre }))"
        />
        <SelectInput
          v-if="puedeVerVehiculos"
          v-model="asignacion.vehiculo"
          label="Vehículo"
          placeholder="Sin vehículo"
          :options="(vehiculos.data.value?.items ?? []).filter((v) => v.activo).map((v) => ({ value: v.id, label: `${v.placa} · ${v.tipo.replace('_', ' ')} · ${v.capacidad_kg} kg` }))"
        />
      </div>
      <template #footer>
        <BaseButton variant="subtle" @click="asignando = null">Cancelar</BaseButton>
        <BaseButton :loading="actualizar.isPending.value" @click="guardarAsignacion">Guardar</BaseButton>
      </template>
    </AppDialog>

    <AppDialog v-model:open="creando" :title="`Nueva solicitud en ${ciudad}`" description="Registra un pedido recibido por teléfono o WhatsApp." size="lg">
      <form id="form-puerta" class="flex flex-col gap-4" novalidate @submit.prevent="enviarNueva">
        <div class="grid gap-4 sm:grid-cols-2">
          <SegmentedControl v-model="nueva.tipo" label="Servicio" variant="switch" :options="[{ value: 'recojo', label: 'Recojo (14–17 h)' }, { value: 'entrega', label: 'Entrega (08–12 h)' }]" />
          <SegmentedControl v-model="nueva.canal" label="Canal" variant="switch" :options="[{ value: 'telefono', label: 'Teléfono' }, { value: 'whatsapp_chat', label: 'WhatsApp' }]" />
        </div>
        <div class="grid gap-3 sm:grid-cols-3">
          <TextInput v-model="nueva.documento" label="CI" required :error="erroresNueva.documento" />
          <TextInput v-model="nueva.nombres" label="Nombres" required :error="erroresNueva.nombres" />
          <TextInput v-model="nueva.apellidos" label="Apellidos" required :error="erroresNueva.apellidos" />
        </div>
        <div class="grid gap-3 sm:grid-cols-[1fr_2fr]">
          <TextInput v-model="nueva.telefono" label="Celular" type="tel" required :error="erroresNueva.telefono" />
          <TextInput v-model="nueva.direccion" label="Dirección" required :error="erroresNueva.direccion" />
        </div>
        <div class="grid gap-3 sm:grid-cols-3">
          <TextInput v-model="nueva.referencia" label="Referencia" class="sm:col-span-2" />
          <TextInput v-model="nueva.fecha" label="Fecha" type="date" :min="hoyISO()" required :error="erroresNueva.fecha" />
        </div>
        <div class="grid gap-3 sm:grid-cols-3">
          <TextInput v-model="nueva.peso" label="Peso estimado (kg)" inputmode="decimal" />
          <TextInput v-model="nueva.descripcion" label="Descripción" :class="nueva.tipo === 'entrega' ? '' : 'sm:col-span-2'" />
          <TextInput v-if="nueva.tipo === 'entrega'" v-model="nueva.guia" label="Guía a entregar" mono required :error="erroresNueva.guia" />
        </div>
      </form>
      <template #footer>
        <BaseButton variant="subtle" @click="creando = false">Cancelar</BaseButton>
        <BaseButton type="submit" form="form-puerta" :loading="crear.isPending.value">Registrar</BaseButton>
      </template>
    </AppDialog>
  </div>
</template>
