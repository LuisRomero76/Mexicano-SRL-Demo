<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { CircleAlert, Printer, RotateCcw, Ticket } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError, api, unwrap, type Schemas } from '@/api/client'
import { usePoliticas } from '@/api/queries'
import TicketCard from '@/components/booking/TicketCard.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import TextArea from '@/components/ui/TextArea.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { bsExacto, fechaLarga, hora, telefono } from '@/lib/format'
import { ESTADO_VENTA, etiqueta } from '@/lib/labels'
import { useCompraStore } from '@/stores/compra'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const router = useRouter()
const compra = useCompraStore()
const avisos = useToastStore()
const cliente = useQueryClient()
const { data: politicas } = usePoliticas()

const inicialCodigo = typeof route.query.codigo === 'string' ? route.query.codigo.toUpperCase() : ''
const inicialDoc =
  (history.state?.documento as string | undefined) ??
  (compra.estado.reserva?.codigo === inicialCodigo ? compra.estado.reserva.documento : '')

const form = ref({ codigo: inicialCodigo, documento: inicialDoc })
const consulta = ref<{ codigo: string; documento: string } | null>(
  inicialCodigo && inicialDoc ? { codigo: inicialCodigo, documento: inicialDoc } : null,
)

const reserva = useQuery({
  queryKey: computed(() => ['reserva', consulta.value?.codigo, consulta.value?.documento]),
  queryFn: () =>
    unwrap(
      api.GET('/api/v1/reservas/{codigo}', {
        params: { path: { codigo: consulta.value!.codigo }, query: { documento: consulta.value!.documento } },
      }),
    ),
  enabled: computed(() => !!consulta.value),
})

const errorForm = ref<string | null>(null)
function buscar(): void {
  const codigo = form.value.codigo.replace(/[^A-Za-z0-9]/g, '').toUpperCase()
  const documento = form.value.documento.trim()
  if (codigo.length < 6 || documento.length < 4) {
    errorForm.value = 'Ingresa el código de 6 caracteres y el documento.'
    return
  }
  errorForm.value = null
  consulta.value = { codigo, documento }
}

const r = computed(() => reserva.data.value)
const estado = computed(() => etiqueta(ESTADO_VENTA, r.value?.estado))
const salidaCercana = computed(() => {
  const s = r.value?.salida
  if (!s) return true
  const horas = politicas.value?.reembolso_horas_minimas ?? 2
  return new Date(s.fecha_hora_salida).getTime() - Date.now() < horas * 3600_000
})

function irAPagar(): void {
  compra.fijarReserva(consulta.value!.codigo, consulta.value!.documento)
  void router.push({ name: 'pago', params: { codigo: consulta.value!.codigo } })
}

const confirmarCancelar = ref(false)
const cancelar = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/reservas/{codigo}/cancelar', {
        params: { path: { codigo: consulta.value!.codigo }, query: { documento: consulta.value!.documento } },
      }),
    ),
  onSuccess: () => {
    confirmarCancelar.value = false
    avisos.exito('Reserva cancelada', 'Liberamos tus asientos.')
    void cliente.invalidateQueries({ queryKey: ['reserva'] })
  },
  onError: (e) => avisos.error('No se pudo cancelar', e instanceof ApiError ? e.message : undefined),
})

const boletoReembolso = ref<Schemas['BoletoOut'] | null>(null)
const motivo = ref('')
const reembolsoHecho = ref<Schemas['ReembolsoOut'] | null>(null)
const porcentaje = computed(() => politicas.value?.reembolso_porcentaje_cliente ?? 85)
const montoEstimado = computed(() => (boletoReembolso.value ? (boletoReembolso.value.total_bs * porcentaje.value) / 100 : 0))

const reembolsar = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/boletos/{numero_boleto}/reembolso', {
        params: { path: { numero_boleto: boletoReembolso.value!.numero_boleto } },
        body: { documento: consulta.value!.documento, motivo: motivo.value.trim() || 'Cambio de planes' },
      }),
    ),
  onSuccess: (resultado) => {
    reembolsoHecho.value = resultado
    boletoReembolso.value = null
    motivo.value = ''
    void cliente.invalidateQueries({ queryKey: ['reserva'] })
  },
  onError: (e) => avisos.error('No se pudo solicitar el reembolso', e instanceof ApiError ? e.message : undefined),
})

function imprimir(): void {
  window.print()
}
</script>

<template>
  <div class="contenedor flex flex-col gap-6 py-8 sm:py-10">
    <div class="no-print flex flex-col gap-2">
      <h1 class="text-[28px] font-bold sm:text-[32px]">Mi reserva</h1>
      <p class="text-muted">Consulta tus boletos, termina un pago pendiente o pide un reembolso.</p>
    </div>

    <form class="no-print grid gap-3 rounded-2xl border border-line bg-surface p-5 sm:grid-cols-[1fr_1fr_auto] sm:items-end" @submit.prevent="buscar">
      <TextInput v-model="form.codigo" label="Código de reserva" placeholder="MX7K2P" mono maxlength="8" autocomplete="off" required />
      <TextInput v-model="form.documento" label="Documento del comprador o de un pasajero" autocomplete="off" required />
      <BaseButton type="submit" class="h-11" :loading="reserva.isFetching.value">Consultar</BaseButton>
      <p v-if="errorForm" class="text-sm font-medium text-peligro-600 sm:col-span-3" role="alert">{{ errorForm }}</p>
    </form>

    <div v-if="reembolsoHecho" class="no-print flex gap-3 rounded-2xl bg-exito-50 p-5 text-exito-800" role="status">
      <RotateCcw class="size-5 shrink-0" aria-hidden="true" />
      <p class="text-sm">
        Registramos tu solicitud de reembolso del boleto <strong>{{ reembolsoHecho.numero_boleto }}</strong> por
        <strong>{{ bsExacto(reembolsoHecho.monto_bs) }}</strong>. El pago puede demorar hasta
        {{ politicas?.reembolso_dias_habiles_max ?? 7 }} días hábiles.
      </p>
    </div>

    <SkeletonBlock v-if="reserva.isLoading.value && consulta" class="h-72 rounded-2xl" />
    <ErrorState v-else-if="reserva.isError.value" :error="reserva.error.value" title="No encontramos la reserva" @retry="reserva.refetch()" />

    <template v-else-if="r">
      <section class="overflow-hidden rounded-2xl border border-line bg-surface">
        <div class="flex flex-col gap-4 bg-noche-900 p-5 text-white sm:flex-row sm:items-center sm:justify-between sm:p-6">
          <div>
            <p class="text-xs font-semibold tracking-[0.12em] text-carmin-200 uppercase">Reserva</p>
            <p class="codigo text-2xl">{{ r.codigo_reserva }}</p>
            <p class="mt-1 text-sm text-noche-200">
              {{ r.salida.origen }} → {{ r.salida.destino }} · {{ fechaLarga(r.salida.fecha_hora_salida) }} · {{ hora(r.salida.fecha_hora_salida) }}
            </p>
          </div>
          <StatusBadge :tono="estado.tono" :label="estado.label" class="self-start" />
        </div>
        <div class="flex flex-col gap-4 p-5 sm:p-6">
          <p class="text-[15px]">{{ r.mensaje }}</p>
          <div v-if="r.salida.estado === 'demorada'" class="flex gap-2 rounded-xl bg-aviso-50 px-4 py-3 text-sm font-medium text-aviso-800">
            <CircleAlert class="size-5 shrink-0" aria-hidden="true" />La salida tiene una demora de {{ r.salida.minutos_demora }} minutos.
          </div>
          <div class="no-print flex flex-wrap gap-2">
            <template v-if="r.estado === 'pendiente_pago'">
              <BaseButton @click="irAPagar">Pagar {{ bsExacto(r.total_bs) }}</BaseButton>
              <BaseButton variant="subtle" @click="confirmarCancelar = true">Cancelar reserva</BaseButton>
            </template>
            <BaseButton v-if="r.boletos.some((b) => b.codigo_qr)" variant="outline" @click="imprimir">
              <Printer class="size-4" aria-hidden="true" />Imprimir e-tickets
            </BaseButton>
          </div>
        </div>
      </section>

      <div class="flex flex-col gap-4">
        <div v-for="b in r.boletos" :key="b.numero_boleto" class="flex flex-col gap-2">
          <TicketCard :boleto="b" :salida="r.salida" />
          <div v-if="b.estado === 'emitido'" class="no-print flex justify-end">
            <button
              class="inline-flex items-center gap-1.5 text-sm font-semibold text-carmin-600 hover:underline disabled:cursor-not-allowed disabled:text-muted disabled:no-underline"
              :disabled="salidaCercana"
              :title="salidaCercana ? 'Faltan menos de 2 horas para la salida' : undefined"
              @click="boletoReembolso = b"
            >
              <RotateCcw class="size-4" aria-hidden="true" />
              {{ salidaCercana ? 'Reembolso no disponible (menos de 2 h para la salida)' : 'Solicitar reembolso' }}
            </button>
          </div>
        </div>
      </div>
    </template>

    <div v-else-if="!consulta" class="no-print flex flex-col items-center gap-3 py-10 text-center text-muted">
      <Ticket class="size-10" aria-hidden="true" />
      <p>El código de 6 caracteres está en el correo de confirmación y en tu e-ticket.</p>
    </div>

    <ConfirmDialog
      v-model:open="confirmarCancelar"
      title="¿Cancelar la reserva?"
      description="Liberaremos los asientos. Esta acción no se puede deshacer."
      confirm-label="Sí, cancelar"
      danger
      :loading="cancelar.isPending.value"
      @confirm="cancelar.mutate()"
    />

    <AppDialog
      :open="!!boletoReembolso"
      title="Solicitar reembolso"
      :description="`Boleto ${boletoReembolso?.numero_boleto ?? ''} · ${boletoReembolso?.pasajero ?? ''}`"
      @update:open="(v) => !v && (boletoReembolso = null)"
    >
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-2 gap-3 rounded-xl bg-canvas p-4 text-sm">
          <span class="text-muted">Pagaste</span><strong class="text-right">{{ bsExacto(boletoReembolso?.total_bs) }}</strong>
          <span class="text-muted">Te devolvemos ({{ porcentaje }} %)</span><strong class="text-right text-exito-600">{{ bsExacto(montoEstimado) }}</strong>
        </div>
        <p class="text-sm text-muted">
          La empresa retiene el {{ 100 - porcentaje }} %, incluidos los costos de la factura. El asiento se libera en cuanto confirmes.
          Dudas: {{ telefono('59167640155') }}.
        </p>
        <TextArea v-model="motivo" label="Motivo (opcional)" :rows="3" maxlength="250" />
      </div>
      <template #footer>
        <BaseButton variant="subtle" @click="boletoReembolso = null">Volver</BaseButton>
        <BaseButton variant="danger" :loading="reembolsar.isPending.value" @click="reembolsar.mutate()">Confirmar reembolso</BaseButton>
      </template>
    </AppDialog>
  </div>
</template>
