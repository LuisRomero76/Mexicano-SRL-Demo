<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { CircleAlert, CreditCard, Lock, QrCode as QrIcon, Smartphone, TimerOff } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError, api, unwrap } from '@/api/client'
import BookingSteps from '@/components/booking/BookingSteps.vue'
import TripSummary from '@/components/booking/TripSummary.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import QrCode from '@/components/ui/QrCode.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { useCuentaRegresiva } from '@/composables/useCuentaRegresiva'
import { bs, bsExacto, telefono } from '@/lib/format'
import { formatearNumero, luhnValido, marca, soloDigitos, vencimientoValido } from '@/lib/tarjeta'
import { celular } from '@/lib/validacion'
import { useCompraStore } from '@/stores/compra'
import { useToastStore } from '@/stores/toast'

const clienteQuery = useQueryClient()
const route = useRoute()
const router = useRouter()
const compra = useCompraStore()
const avisos = useToastStore()

const codigo = computed(() => String(route.params.codigo).toUpperCase())
const documento = computed(() =>
  compra.estado.reserva?.codigo === codigo.value ? compra.estado.reserva.documento : ((history.state?.documento as string) ?? ''),
)

const reserva = useQuery({
  queryKey: computed(() => ['reserva', codigo.value, documento.value]),
  queryFn: () =>
    unwrap(api.GET('/api/v1/reservas/{codigo}', { params: { path: { codigo: codigo.value }, query: { documento: documento.value } } })),
  enabled: computed(() => !!documento.value),
})

watch(
  () => reserva.data.value?.estado,
  (estado) => {
    if (estado === 'pagada') void router.replace({ name: 'confirmacion', params: { codigo: codigo.value } })
  },
)

const expira = computed(() => reserva.data.value?.expira_at ?? null)
const { texto: cuenta, vencido, urgente } = useCuentaRegresiva(expira)

type Metodo = 'qr' | 'tarjeta_debito' | 'tarjeta_credito' | 'tigo_money'
const metodo = ref<Metodo>('qr')
const tarjeta = ref({ numero: '', vencimiento: '', cvv: '', titular: '', credito: true })
const tigo = ref('')
const factura = ref({ nit: compra.estado.comprador.nit_facturacion, razon: compra.estado.comprador.razon_social_facturacion })
const errores = ref<Record<string, string>>({})
const errorPago = ref<string | null>(null)
const confirmarCancelacion = ref(false)

watch(
  () => tarjeta.value.numero,
  (v) => {
    const f = formatearNumero(v)
    if (f !== v) tarjeta.value.numero = f
  },
)

function validar(): boolean {
  const e: Record<string, string> = {}
  if (metodo.value === 'tarjeta_credito' || metodo.value === 'tarjeta_debito') {
    if (!luhnValido(tarjeta.value.numero)) e.numero = 'Número de tarjeta no válido'
    else if (!marca(tarjeta.value.numero)) e.numero = 'Aceptamos Visa y Mastercard'
    if (!vencimientoValido(tarjeta.value.vencimiento)) e.vencimiento = 'Fecha no válida o vencida'
    if (!/^\d{3,4}$/.test(tarjeta.value.cvv)) e.cvv = '3 o 4 dígitos'
    if (tarjeta.value.titular.trim().length < 3) e.titular = 'Como figura en la tarjeta'
  }
  if (metodo.value === 'tigo_money' && !celular.safeParse(tigo.value).success) e.tigo = 'Ingresa tu número Tigo Money'
  errores.value = e
  return Object.keys(e).length === 0
}

const pagar = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/reservas/{codigo}/pagar', {
        params: { path: { codigo: codigo.value } },
        body: {
          metodo: metodo.value,
          // Simulación: solo viaja el número (el backend conserva los últimos 4). Vencimiento y CVV no salen del navegador.
          numero_tarjeta: metodo.value.startsWith('tarjeta') ? soloDigitos(tarjeta.value.numero) : null,
          nit_facturacion: factura.value.nit.trim() || null,
          razon_social_facturacion: factura.value.razon.trim() || null,
        },
      }),
    ),
  onSuccess: async () => {
    tarjeta.value = { numero: '', vencimiento: '', cvv: '', titular: '', credito: true }
    // La confirmación comparte esta consulta: se descarta la versión "pendiente de pago".
    await clienteQuery.invalidateQueries({ queryKey: ['reserva', codigo.value] })
    void router.push({ name: 'confirmacion', params: { codigo: codigo.value } })
  },
  onError: (e) => {
    errorPago.value = e instanceof ApiError ? e.message : 'No pudimos procesar el pago.'
    if (e instanceof ApiError && e.code === 'reserva_no_pagable') void reserva.refetch()
  },
})

function enviar(): void {
  errorPago.value = null
  if (metodo.value.startsWith('tarjeta')) metodo.value = tarjeta.value.credito ? 'tarjeta_credito' : 'tarjeta_debito'
  if (validar()) pagar.mutate()
}

const cancelar = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/reservas/{codigo}/cancelar', {
        params: { path: { codigo: codigo.value }, query: { documento: documento.value } },
      }),
    ),
  onSuccess: () => {
    confirmarCancelacion.value = false
    compra.reiniciar()
    avisos.info('Reserva cancelada', 'Liberamos tus asientos.')
    void router.push({ name: 'inicio' })
  },
  onError: (e) => avisos.error('No se pudo cancelar', e instanceof ApiError ? e.message : undefined),
})

const opciones = [
  { value: 'qr', label: 'QR', hint: 'Bancos bolivianos', icono: QrIcon },
  { value: 'tarjeta_credito', label: 'Tarjeta', hint: 'Visa · Mastercard', icono: CreditCard },
  { value: 'tigo_money', label: 'Tigo Money', hint: 'Billetera móvil', icono: Smartphone },
] as const
const esTarjeta = computed(() => metodo.value === 'tarjeta_credito' || metodo.value === 'tarjeta_debito')
const textoBoton = computed(() => {
  const total = bsExacto(reserva.data.value?.total_bs)
  if (metodo.value === 'qr') return `Ya pagué ${total} con QR`
  if (metodo.value === 'tigo_money') return `Pagar ${total} con Tigo Money`
  return `Pagar ${total}`
})
</script>

<template>
  <div>
    <BookingSteps :paso="4" />
    <div class="contenedor py-6 sm:py-8">
      <EmptyState
        v-if="!documento"
        title="Necesitamos verificar tu reserva"
        text="Ingresa a «Mi reserva» con tu código y documento para continuar con el pago."
      >
        <BaseButton :to="{ name: 'mi-reserva', query: { codigo } }">Ir a Mi reserva</BaseButton>
      </EmptyState>
      <div v-else-if="reserva.isLoading.value" class="grid gap-6 lg:grid-cols-[1fr_380px]">
        <SkeletonBlock class="h-96 rounded-2xl" /><SkeletonBlock class="h-80 rounded-2xl" />
      </div>
      <ErrorState v-else-if="reserva.isError.value" :error="reserva.error.value" @retry="reserva.refetch()" />

      <template v-else-if="reserva.data.value">
        <EmptyState
          v-if="reserva.data.value.estado !== 'pendiente_pago' || vencido"
          :icon="TimerOff"
          title="Esta reserva ya no se puede pagar"
          :text="vencido ? 'Se terminó el tiempo y los asientos se liberaron. Puedes buscarlos de nuevo.' : reserva.data.value.mensaje"
        >
          <BaseButton :to="{ name: 'inicio' }">Buscar pasajes</BaseButton>
        </EmptyState>

        <form v-else class="grid items-start gap-6 lg:grid-cols-[1fr_380px]" novalidate @submit.prevent="enviar">
          <div class="flex min-w-0 flex-col gap-5">
            <div
              class="flex items-center justify-between gap-3 rounded-2xl px-5 py-3.5 text-sm font-semibold"
              :class="urgente ? 'bg-peligro-50 text-peligro-800' : 'bg-aviso-50 text-aviso-800'"
              role="timer"
              aria-live="off"
            >
              <span>Tus asientos están reservados por</span>
              <span class="codigo text-lg tabular">{{ cuenta }}</span>
            </div>

            <section class="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-5">
              <h1 class="text-xl font-bold">¿Cómo quieres pagar?</h1>
              <div role="radiogroup" aria-label="Método de pago" class="grid gap-3 sm:grid-cols-3">
                <label
                  v-for="o in opciones"
                  :key="o.value"
                  class="flex cursor-pointer items-center gap-3 rounded-xl border-[1.5px] p-4 transition-colors has-focus-visible:outline-2 has-focus-visible:outline-carmin-600"
                  :class="(o.value === 'tarjeta_credito' ? esTarjeta : metodo === o.value) ? 'border-carmin-600 bg-carmin-50' : 'border-line-strong hover:border-noche-400'"
                >
                  <input
                    type="radio"
                    class="sr-only"
                    name="metodo"
                    :value="o.value"
                    :checked="o.value === 'tarjeta_credito' ? esTarjeta : metodo === o.value"
                    @change="metodo = o.value"
                  />
                  <component :is="o.icono" class="size-6 text-noche-900" aria-hidden="true" />
                  <span class="flex flex-col">
                    <strong>{{ o.label }}</strong><span class="text-xs text-muted">{{ o.hint }}</span>
                  </span>
                </label>
              </div>

              <div v-if="metodo === 'qr'" class="flex flex-col items-center gap-5 rounded-xl bg-canvas p-5 sm:flex-row">
                <QrCode :value="`EM-QR|${codigo}|BOB|${reserva.data.value.total_bs}`" :size="168" label="Código QR para pagar la reserva" />
                <ol class="flex list-decimal flex-col gap-2 pl-5 text-sm text-muted">
                  <li>Abre la app de tu banco y elige «Pagar con QR».</li>
                  <li>Escanea el código y confirma {{ bsExacto(reserva.data.value.total_bs) }}.</li>
                  <li>Presiona «Ya pagué» y te mostramos tus boletos.</li>
                </ol>
              </div>

              <div v-else-if="esTarjeta" class="flex flex-col gap-4">
                <div class="flex w-fit rounded-control bg-surface-2 p-1 text-[13px] font-semibold">
                  <button type="button" class="h-9 rounded-lg px-4" :class="tarjeta.credito ? 'bg-surface shadow-suave' : 'text-muted'" @click="tarjeta.credito = true">Crédito</button>
                  <button type="button" class="h-9 rounded-lg px-4" :class="!tarjeta.credito ? 'bg-surface shadow-suave' : 'text-muted'" @click="tarjeta.credito = false">Débito</button>
                </div>
                <TextInput
                  v-model="tarjeta.numero"
                  label="Número de tarjeta"
                  inputmode="numeric"
                  autocomplete="cc-number"
                  placeholder="0000 0000 0000 0000"
                  :error="errores.numero"
                >
                  <template #sufijo>
                    <span v-if="marca(tarjeta.numero)" class="text-xs font-bold text-noche-700">{{ marca(tarjeta.numero) }}</span>
                  </template>
                </TextInput>
                <div class="grid grid-cols-2 gap-4">
                  <TextInput v-model="tarjeta.vencimiento" label="Vencimiento" placeholder="MM/AA" inputmode="numeric" maxlength="5" autocomplete="cc-exp" :error="errores.vencimiento" />
                  <TextInput v-model="tarjeta.cvv" label="CVV" type="password" inputmode="numeric" maxlength="4" autocomplete="cc-csc" :error="errores.cvv" />
                </div>
                <TextInput v-model="tarjeta.titular" label="Nombre del titular" autocomplete="cc-name" :error="errores.titular" />
                <p class="flex items-start gap-2 text-[13px] text-muted">
                  <CircleAlert class="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                  Demostración: no ingreses datos reales. Usa 4111 1111 1111 1111; una tarjeta terminada en 0002 simula un rechazo.
                </p>
              </div>

              <div v-else class="flex flex-col gap-3">
                <TextInput v-model="tigo" label="Número Tigo Money" type="tel" inputmode="tel" placeholder="71234567" :error="errores.tigo" />
                <p class="text-[13px] text-muted">Recibirás una solicitud de pago en tu celular para confirmarla con tu PIN.</p>
              </div>
            </section>

            <section class="grid gap-4 rounded-2xl border border-line bg-surface p-5 sm:grid-cols-2">
              <h2 class="font-sans text-base font-bold sm:col-span-2">Factura <span class="font-normal text-muted">· tu e-ticket es tu factura</span></h2>
              <TextInput v-model="factura.nit" label="NIT o CI" hint="Si lo dejas vacío usamos tu documento" maxlength="20" />
              <TextInput v-model="factura.razon" label="Razón social" maxlength="150" />
            </section>
          </div>

          <aside class="overflow-hidden rounded-2xl border border-line bg-surface lg:sticky lg:top-24">
            <TripSummary :salida="reserva.data.value.salida" etiqueta="Reserva">
              <span class="codigo mt-1 text-xl text-white">{{ reserva.data.value.codigo_reserva }}</span>
            </TripSummary>
            <div class="flex flex-col gap-3 p-5 text-[15px]">
              <div v-for="b in reserva.data.value.boletos" :key="b.numero_boleto" class="flex justify-between gap-3 text-sm">
                <span>Asiento {{ b.numero_asiento }} · {{ b.pasajero }}</span><span class="tabular">{{ bs(b.total_bs) }}</span>
              </div>
              <div class="flex items-baseline justify-between border-t border-line pt-3">
                <strong>Total a pagar</strong>
                <span class="font-display text-[28px] font-bold tabular">{{ bsExacto(reserva.data.value.total_bs) }}</span>
              </div>
              <p v-if="errorPago" class="rounded-xl bg-peligro-50 px-4 py-3 text-sm font-medium text-peligro-800" role="alert">{{ errorPago }}</p>
              <BaseButton type="submit" size="lg" block :loading="pagar.isPending.value">
                <Lock class="size-4" aria-hidden="true" />{{ textoBoton }}
              </BaseButton>
              <p class="text-[13px] text-muted">
                Al pagar aceptas los términos y la política de reembolsos (85 % hasta 2 h antes de la salida).
                Contacto: {{ telefono('59167640155') }}.
              </p>
              <button type="button" class="self-start text-sm font-semibold text-carmin-600 hover:underline" @click="confirmarCancelacion = true">
                Cancelar la reserva
              </button>
            </div>
          </aside>
        </form>
      </template>
    </div>

    <ConfirmDialog
      v-model:open="confirmarCancelacion"
      title="¿Cancelar la reserva?"
      description="Liberaremos tus asientos y no podrás recuperarlos."
      confirm-label="Sí, cancelar"
      danger
      :loading="cancelar.isPending.value"
      @confirm="cancelar.mutate()"
    />
  </div>
</template>
