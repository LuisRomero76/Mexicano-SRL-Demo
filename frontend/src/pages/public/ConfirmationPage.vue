<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { Check, MessageCircle, Printer } from '@lucide/vue'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, unwrap } from '@/api/client'
import { usePoliticas } from '@/api/queries'
import TicketCard from '@/components/booking/TicketCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import { bsExacto, fechaCorta, fechaHora, hora } from '@/lib/format'
import { METODO_PAGO } from '@/lib/labels'
import { useCompraStore } from '@/stores/compra'

const route = useRoute()
const router = useRouter()
const compra = useCompraStore()
const { data: politicas } = usePoliticas()

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

function imprimir(): void {
  window.print()
}
function gestionar(): void {
  void router.push({ name: 'mi-reserva', query: { codigo: codigo.value }, state: { documento: documento.value } })
}

const nombre = computed(() => reserva.data.value?.comprador.split(' ')[0] ?? '')
const compartir = computed(() => {
  const r = reserva.data.value
  if (!r) return ''
  const texto = `Mi viaje con El Mexicano: ${r.salida.origen} → ${r.salida.destino}, ${fechaCorta(r.salida.fecha_hora_salida)} a las ${hora(r.salida.fecha_hora_salida)}. Reserva ${r.codigo_reserva}.`
  return `https://wa.me/?text=${encodeURIComponent(texto)}`
})
</script>

<template>
  <div class="contenedor py-8 sm:py-10">
    <EmptyState v-if="!documento" title="Consulta tu reserva" text="Ingresa con tu código y documento para ver tus boletos.">
      <BaseButton :to="{ name: 'mi-reserva', query: { codigo } }">Ir a Mi reserva</BaseButton>
    </EmptyState>
    <SkeletonBlock v-else-if="reserva.isLoading.value" class="h-96 rounded-2xl" />
    <ErrorState v-else-if="reserva.isError.value" :error="reserva.error.value" @retry="reserva.refetch()" />
    <template v-else-if="reserva.data.value">
      <div class="no-print mb-8 flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
        <div class="flex items-center gap-4">
          <span class="flex size-14 shrink-0 items-center justify-center rounded-full bg-exito-50 text-exito-600">
            <Check class="size-7" stroke-width="2.6" aria-hidden="true" />
          </span>
          <div>
            <h1 class="text-2xl font-bold sm:text-[30px]">
              {{ reserva.data.value.estado === 'pagada' ? `¡Listo, ${nombre}! Tu viaje está confirmado.` : reserva.data.value.mensaje }}
            </h1>
            <p class="mt-1 text-[15px] text-muted">
              Reserva <span class="codigo text-fg">{{ reserva.data.value.codigo_reserva }}</span> · Muestra tus e-tickets impresos o en tu celular al abordar.
            </p>
          </div>
        </div>
        <div class="flex flex-wrap gap-2">
          <BaseButton variant="outline" @click="imprimir"><Printer class="size-4" aria-hidden="true" />Imprimir</BaseButton>
          <BaseButton variant="success" :href="compartir">
            <MessageCircle class="size-4" aria-hidden="true" />Compartir
          </BaseButton>
        </div>
      </div>

      <div class="grid items-start gap-6 lg:grid-cols-[1fr_340px]">
        <div class="flex flex-col gap-4">
          <TicketCard v-for="b in reserva.data.value.boletos" :key="b.numero_boleto" :boleto="b" :salida="reserva.data.value.salida" />
        </div>
        <aside class="no-print flex flex-col gap-4">
          <div v-if="politicas" class="rounded-2xl border border-line bg-surface p-5">
            <h2 class="font-sans text-base font-bold">Antes de viajar</h2>
            <ul class="mt-3 flex list-disc flex-col gap-1.5 pl-5 text-sm text-muted">
              <li>Llega a la terminal 30 minutos antes.</li>
              <li>Lleva el documento que figura en el boleto.</li>
              <li>{{ politicas.equipaje_bodega_kg }} kg en bodega y {{ politicas.equipaje_mano_kg }} kg de mano.</li>
              <li>Solo se permiten perros guía.</li>
            </ul>
          </div>
          <div v-if="reserva.data.value.factura" class="flex flex-col gap-2 rounded-2xl border border-line bg-surface p-5 text-sm">
            <h2 class="font-sans text-base font-bold">Factura</h2>
            <div class="flex justify-between"><span class="text-muted">N.º</span><strong>{{ reserva.data.value.factura.numero_factura }}</strong></div>
            <div class="flex justify-between"><span class="text-muted">NIT / CI</span><strong>{{ reserva.data.value.factura.nit_ci_cliente }}</strong></div>
            <div class="flex justify-between"><span class="text-muted">Emitida</span><strong>{{ fechaHora(reserva.data.value.factura.fecha_emision) }}</strong></div>
            <div class="flex justify-between">
              <span class="text-muted">Pagado{{ reserva.data.value.pago ? ` (${METODO_PAGO[reserva.data.value.pago.metodo]})` : '' }}</span>
              <strong>{{ bsExacto(reserva.data.value.total_bs) }}</strong>
            </div>
          </div>
          <div class="flex flex-col gap-2 rounded-2xl bg-noche-900 p-5 text-sm text-white">
            <strong class="font-display text-base">¿Cambio de planes?</strong>
            <span class="text-noche-200">Puedes pedir la devolución del 85 % hasta 2 horas antes de la salida.</span>
            <button type="button" class="self-start font-semibold text-carmin-200 hover:underline" @click="gestionar">
              Gestionar mi reserva
            </button>
          </div>
        </aside>
      </div>
    </template>
  </div>
</template>
