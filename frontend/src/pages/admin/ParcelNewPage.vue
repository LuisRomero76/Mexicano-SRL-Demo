<script setup lang="ts">
import { useMutation, useQuery } from '@tanstack/vue-query'
import { refDebounced } from '@vueuse/core'
import { CircleCheck, PackageCheck, Printer, UserSearch } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { z } from 'zod'
import { ApiError, api, unwrap, type Schemas } from '@/api/client'
import { useOficinasPublicas } from '@/api/queries'
import ParcelLabel from '@/components/cargo/ParcelLabel.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import CheckboxInput from '@/components/ui/CheckboxInput.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SelectInput from '@/components/ui/SelectInput.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import SurfaceCard from '@/components/ui/SurfaceCard.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { bsExacto } from '@/lib/format'
import { TIPO_ENVIO } from '@/lib/labels'
import { celular, documento, erroresDe, nombre } from '@/lib/validacion'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

const auth = useAuthStore()
const avisos = useToastStore()
const router = useRouter()
const { data: oficinas } = useOficinasPublicas()
const cuentas = useQuery({
  queryKey: ['cuentas-corporativas'],
  queryFn: () => unwrap(api.GET('/api/v1/admin/cuentas-corporativas', { params: { query: { limit: 100 } } })),
})

const bodegas = computed(() => (oficinas.value ?? []).filter((o) => o.tipo !== 'boleteria'))
const form = reactive({
  origen: '',
  destino: '',
  remitente: { documento: '', nombres: '', apellidos: '', telefono: '' },
  destinatario: { nombre: '', documento: '', telefono: '' },
  tipo: 'auto' as 'auto' | Schemas['TipoEnvio'],
  peso: '',
  bultos: '1',
  contenido: '',
  valor: '',
  fragil: false,
  mudanza: false,
  modalidad: 'retiro_en_oficina' as Schemas['ModalidadEntrega'],
  direccion: '',
  referencia: '',
  pagoEn: 'origen' as Schemas['PagoEn'],
  metodo: 'efectivo' as Schemas['MetodoPago'],
  cuenta: null as string | null,
})
watch(
  bodegas,
  (l) => {
    if (form.origen || !l.length) return
    form.origen = (l.find((o) => o.oficina_id === auth.usuario?.oficina_id) ?? l.find((o) => o.ciudad === 'Sucre') ?? l[0]).codigo
  },
  { immediate: true },
)

const ciudadDe = (codigo: string) => bodegas.value.find((o) => o.codigo === codigo)?.ciudad ?? ''
const origenCiudad = computed(() => ciudadDe(form.origen))
const destinos = computed(() => bodegas.value.filter((o) => o.ciudad !== origenCiudad.value))
watch(destinos, (l) => {
  if (!l.some((o) => o.codigo === form.destino)) form.destino = l[0]?.codigo ?? ''
})
const destinoCiudad = computed(() => ciudadDe(form.destino))
const admitePuerta = computed(() => ['Sucre', 'Santa Cruz'].includes(destinoCiudad.value))
watch(admitePuerta, (v) => !v && (form.modalidad = 'retiro_en_oficina'))

const parametros = computed(() => ({
  origen: origenCiudad.value,
  destino: destinoCiudad.value,
  peso_kg: Number(form.peso.replace(',', '.')),
  tipo: form.tipo === 'auto' ? undefined : form.tipo,
  puerta_a_puerta: form.modalidad === 'puerta_a_puerta',
}))
const debounced = refDebounced(parametros, 350)
const cotizacion = useQuery({
  queryKey: computed(() => ['cotizar', debounced.value]),
  queryFn: () => unwrap(api.GET('/api/v1/carga/cotizar', { params: { query: debounced.value } })),
  enabled: computed(() => debounced.value.peso_kg > 0 && !!debounced.value.origen && !!debounced.value.destino),
  retry: false,
})

async function buscarRemitente(): Promise<void> {
  const q = form.remitente.documento.trim()
  if (q.length < 5 || form.remitente.nombres) return
  try {
    const r = await unwrap(api.GET('/api/v1/admin/clientes', { params: { query: { q, limit: 1 } } }))
    const c = r.items.find((x) => x.numero_documento === q.toUpperCase())
    if (c) {
      form.remitente.nombres = c.nombres
      form.remitente.apellidos = c.apellidos
      form.remitente.telefono = c.telefono_e164 ?? ''
      avisos.info('Cliente frecuente', `${c.nombres} ${c.apellidos}`)
    }
  } catch {
    /* ayuda opcional */
  }
}

const esquema = z.object({
  remitente: z.object({ documento, nombres: nombre, apellidos: nombre, telefono: celular }),
  destinatario: z.object({ nombre: z.string().trim().min(3, 'Nombre completo'), telefono: celular }),
  peso: z.string().refine((v) => Number(v.replace(',', '.')) > 0, 'Indica el peso'),
  contenido: z.string().trim().min(3, 'Describe el contenido'),
})
const errores = ref<Record<string, string>>({})
const creada = ref<Schemas['EncomiendaOut'] | null>(null)

const registrar = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/admin/encomiendas', {
        body: {
          tipo_envio: form.tipo === 'auto' ? null : form.tipo,
          remitente: {
            numero_documento: form.remitente.documento.trim(),
            nombres: form.remitente.nombres.trim(),
            apellidos: form.remitente.apellidos.trim(),
            telefono: form.remitente.telefono.trim(),
          },
          cuenta_corporativa_codigo: form.pagoEn === 'credito_corporativo' ? form.cuenta : null,
          destinatario_nombre: form.destinatario.nombre.trim(),
          destinatario_numero_documento: form.destinatario.documento.trim() || null,
          destinatario_telefono: form.destinatario.telefono.trim(),
          oficina_origen_codigo: form.origen,
          oficina_destino_codigo: form.destino,
          modalidad_entrega: form.modalidad,
          direccion_entrega: form.modalidad === 'puerta_a_puerta' ? form.direccion.trim() : null,
          referencia_entrega: form.referencia.trim() || null,
          descripcion_contenido: form.contenido.trim(),
          cantidad_bultos: Number(form.bultos) || 1,
          peso_kg: Number(form.peso.replace(',', '.')),
          valor_declarado_bs: form.valor ? Number(form.valor.replace(',', '.')) : null,
          es_fragil: form.fragil,
          es_mudanza: form.mudanza,
          pago_en: form.pagoEn,
          metodo_pago: form.pagoEn === 'origen' ? form.metodo : null,
        },
      }),
    ),
  onSuccess: (e) => (creada.value = e),
  onError: (e) => {
    if (e instanceof ApiError && e.code === 'datos_invalidos') errores.value = e.camposInvalidos
    avisos.error('No se pudo registrar', e instanceof ApiError ? e.message : undefined)
  },
})

function enviar(): void {
  errores.value = erroresDe(esquema.safeParse(form))
  if (form.modalidad === 'puerta_a_puerta' && form.direccion.trim().length < 5) errores.value.direccion = 'Indica la dirección de entrega'
  if (form.pagoEn === 'credito_corporativo' && !form.cuenta) errores.value.cuenta = 'Elige la cuenta'
  if (Object.keys(errores.value).length) return
  registrar.mutate()
}
function otra(): void {
  creada.value = null
  Object.assign(form.destinatario, { nombre: '', documento: '', telefono: '' })
  Object.assign(form, { peso: '', contenido: '', valor: '', fragil: false, mudanza: false, direccion: '', referencia: '' })
}
function imprimir(): void {
  window.print()
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader title="Registrar encomienda" :crumbs="[{ label: 'Encomiendas', to: { name: 'admin-encomiendas' } }, { label: 'Nueva' }]">
      <SelectInput v-model="form.origen" label="Bodega de origen" class="w-72" :options="bodegas.map((o) => ({ value: o.codigo, label: o.nombre }))" />
    </PageHeader>

    <form class="grid items-start gap-6 xl:grid-cols-[1fr_360px]" novalidate @submit.prevent="enviar">
      <div class="flex min-w-0 flex-col gap-5">
        <SurfaceCard>
          <div class="grid gap-6 md:grid-cols-2">
            <fieldset class="flex flex-col gap-3">
              <legend class="mb-2 font-bold">Remitente</legend>
              <TextInput v-model="form.remitente.documento" label="CI" required :error="errores['remitente.documento']" @blur="buscarRemitente">
                <template #sufijo><UserSearch class="size-4 text-muted" aria-hidden="true" /></template>
              </TextInput>
              <div class="grid gap-3 sm:grid-cols-2">
                <TextInput v-model="form.remitente.nombres" label="Nombres" required :error="errores['remitente.nombres']" />
                <TextInput v-model="form.remitente.apellidos" label="Apellidos" required :error="errores['remitente.apellidos']" />
              </div>
              <TextInput v-model="form.remitente.telefono" label="Celular" type="tel" required :error="errores['remitente.telefono']" />
            </fieldset>
            <fieldset class="flex flex-col gap-3">
              <legend class="mb-2 font-bold">Destinatario</legend>
              <TextInput v-model="form.destinatario.nombre" label="Nombre completo" required :error="errores['destinatario.nombre']" />
              <div class="grid gap-3 sm:grid-cols-2">
                <TextInput v-model="form.destinatario.documento" label="CI" hint="Para validar el retiro" />
                <TextInput v-model="form.destinatario.telefono" label="Celular" type="tel" required :error="errores['destinatario.telefono']" />
              </div>
            </fieldset>
          </div>
        </SurfaceCard>

        <SurfaceCard title="Envío">
          <div class="flex flex-col gap-4">
            <div class="grid gap-3 md:grid-cols-4">
              <SelectInput v-model="form.destino" label="Bodega de destino" class="md:col-span-2" :options="destinos.map((o) => ({ value: o.codigo, label: `${o.ciudad} · ${o.nombre}` }))" />
              <TextInput v-model="form.peso" label="Peso (kg)" inputmode="decimal" required :error="errores.peso" />
              <TextInput v-model="form.bultos" label="Bultos" type="number" min="1" />
            </div>
            <SegmentedControl
              v-model="form.tipo"
              label="Tipo de envío"
              variant="switch"
              :options="[
                { value: 'auto', label: 'Según el peso' },
                { value: 'sobre', label: 'Sobre' },
                { value: 'paquete', label: 'Paquete' },
                { value: 'carga', label: 'Carga' },
              ]"
            />
            <div class="grid gap-3 md:grid-cols-[1fr_200px]">
              <TextInput v-model="form.contenido" label="Contenido" required :error="errores.contenido" />
              <TextInput v-model="form.valor" label="Valor declarado (Bs)" inputmode="decimal" />
            </div>
            <div class="flex flex-wrap gap-x-6 gap-y-2">
              <CheckboxInput v-model="form.fragil" label="Frágil" />
              <CheckboxInput v-model="form.mudanza" label="Mudanza" :disabled="cotizacion.data.value?.tipo_envio !== 'carga'" />
            </div>
            <SegmentedControl
              v-model="form.modalidad"
              label="Entrega"
              :options="[
                { value: 'retiro_en_oficina', label: 'Retiro en oficina', hint: 'Con documento y código de retiro' },
                { value: 'puerta_a_puerta', label: 'Puerta a puerta', hint: admitePuerta ? 'Recargo según tarifa' : 'Solo Sucre y Santa Cruz', disabled: !admitePuerta },
              ]"
            />
            <div v-if="form.modalidad === 'puerta_a_puerta'" class="grid gap-3 md:grid-cols-2">
              <TextInput v-model="form.direccion" label="Dirección de entrega" required :error="errores.direccion" />
              <TextInput v-model="form.referencia" label="Referencia" />
            </div>
          </div>
        </SurfaceCard>

        <SurfaceCard title="Pago">
          <div class="grid gap-4 md:grid-cols-2">
            <SegmentedControl
              v-model="form.pagoEn"
              label="¿Quién paga?"
              variant="switch"
              :options="[
                { value: 'origen', label: 'En origen' },
                { value: 'destino', label: 'En destino' },
                { value: 'credito_corporativo', label: 'Corporativo' },
              ]"
            />
            <SelectInput
              v-if="form.pagoEn === 'origen'"
              v-model="form.metodo"
              label="Método"
              :options="[
                { value: 'efectivo', label: 'Efectivo' },
                { value: 'qr', label: 'QR' },
                { value: 'tarjeta_debito', label: 'Tarjeta de débito' },
                { value: 'tarjeta_credito', label: 'Tarjeta de crédito' },
              ]"
            />
            <SelectInput
              v-else-if="form.pagoEn === 'credito_corporativo'"
              v-model="form.cuenta"
              label="Cuenta corporativa"
              placeholder="Elige la cuenta"
              :error="errores.cuenta"
              :options="(cuentas.data.value?.items ?? []).filter((c) => c.activo).map((c) => ({ value: c.codigo, label: `${c.razon_social} · disponible ${bsExacto(c.limite_credito_bs - c.saldo_pendiente_bs)}` }))"
            />
            <p v-else class="self-end text-sm text-muted">El destinatario paga al recoger; no se entrega sin cobrar.</p>
          </div>
        </SurfaceCard>
      </div>

      <aside class="flex flex-col gap-4 xl:sticky xl:top-20">
        <div class="overflow-hidden rounded-2xl border border-line bg-surface">
          <div class="flex items-center justify-between bg-noche-900 px-5 py-4 text-white">
            <strong>Cotización</strong>
            <span v-if="cotizacion.data.value" class="rounded-full bg-noche-700 px-2.5 py-1 text-xs font-semibold">{{ TIPO_ENVIO[cotizacion.data.value.tipo_envio] }}</span>
          </div>
          <div class="flex flex-col gap-2.5 p-5 text-sm" aria-live="polite">
            <SkeletonBlock v-if="cotizacion.isFetching.value && !cotizacion.data.value" class="h-24" />
            <p v-else-if="cotizacion.isError.value" class="rounded-xl bg-peligro-50 p-3 text-peligro-800">{{ (cotizacion.error.value as Error).message }}</p>
            <template v-else-if="cotizacion.data.value">
              <div class="flex justify-between"><span>Base</span><span class="tabular">{{ bsExacto(cotizacion.data.value.precio_base_bs) }}</span></div>
              <div v-if="cotizacion.data.value.kg_adicionales" class="flex justify-between">
                <span>{{ cotizacion.data.value.kg_adicionales }} kg × {{ bsExacto(cotizacion.data.value.precio_kg_adicional_bs) }}</span>
                <span class="tabular">{{ bsExacto(cotizacion.data.value.cargo_peso_adicional_bs) }}</span>
              </div>
              <div v-if="cotizacion.data.value.puerta_a_puerta" class="flex justify-between"><span>Puerta a puerta</span><span class="tabular">{{ bsExacto(cotizacion.data.value.recargo_puerta_a_puerta_bs) }}</span></div>
              <div class="flex items-baseline justify-between border-t border-line pt-3">
                <strong>Total</strong><span class="font-display text-[28px] font-bold tabular">{{ bsExacto(cotizacion.data.value.total_bs) }}</span>
              </div>
            </template>
            <p v-else class="text-muted">Indica el peso para cotizar.</p>
          </div>
        </div>
        <BaseButton type="submit" size="lg" block :loading="registrar.isPending.value" :disabled="cotizacion.isError.value">
          <PackageCheck class="size-5" aria-hidden="true" />{{ form.pagoEn === 'origen' && cotizacion.data.value ? `Registrar y cobrar ${bsExacto(cotizacion.data.value.total_bs)}` : 'Registrar encomienda' }}
        </BaseButton>
      </aside>
    </form>

    <AppDialog :open="!!creada" title="Encomienda registrada" size="lg" @update:open="(v) => !v && otra()">
      <div v-if="creada" class="flex flex-col gap-5">
        <div class="no-print flex items-center gap-2 font-semibold text-exito-600"><CircleCheck class="size-5" aria-hidden="true" />Entrega el comprobante al remitente.</div>
        <ParcelLabel :encomienda="creada" />
      </div>
      <template #footer>
        <BaseButton variant="subtle" @click="router.push({ name: 'admin-encomienda', params: { guia: creada!.numero_guia } })">Ver detalle</BaseButton>
        <BaseButton variant="subtle" @click="imprimir"><Printer class="size-4" aria-hidden="true" />Imprimir</BaseButton>
        <BaseButton @click="otra">Registrar otra</BaseButton>
      </template>
    </AppDialog>
  </div>
</template>
