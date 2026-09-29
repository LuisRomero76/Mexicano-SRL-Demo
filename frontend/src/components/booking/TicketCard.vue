<script setup lang="ts">
import type { Schemas } from '@/api/client'
import QrCode from '@/components/ui/QrCode.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { bs, fechaCorta, hora } from '@/lib/format'
import { ESTADO_BOLETO, TIPO_PASAJERO, etiqueta } from '@/lib/labels'

defineProps<{ boleto: Schemas['BoletoOut']; salida: Schemas['SalidaDeReserva'] }>()
</script>

<template>
  <article
    :aria-label="`Boleto ${boleto.numero_boleto}`"
    class="print-plain flex flex-col overflow-hidden rounded-2xl border border-line bg-surface break-inside-avoid sm:flex-row"
  >
    <div class="flex flex-1 flex-col gap-4 p-5 sm:p-6">
      <div class="flex items-center justify-between gap-3">
        <span class="font-display font-bold tracking-[0.05em] text-noche-900 dark:text-white">EL MEXICANO</span>
        <span class="codigo text-sm text-muted">{{ boleto.numero_boleto }}</span>
      </div>
      <div class="flex items-center gap-4 sm:gap-6">
        <div>
          <div class="font-display text-[28px] leading-none font-bold tabular">{{ hora(salida.fecha_hora_salida) }}</div>
          <div class="mt-1 text-sm text-muted">{{ salida.origen }} · {{ fechaCorta(salida.fecha_hora_salida) }}</div>
        </div>
        <svg class="h-3.5 flex-1" viewBox="0 0 120 14" preserveAspectRatio="none" aria-hidden="true">
          <path d="M2 7h112M108 2l6 5-6 5" fill="none" stroke="#B3122E" stroke-width="2" stroke-linecap="round" vector-effect="non-scaling-stroke" />
        </svg>
        <div class="text-right">
          <div class="font-display text-[28px] leading-none font-bold tabular">{{ hora(salida.fecha_hora_llegada_estimada) }}</div>
          <div class="mt-1 text-sm text-muted">{{ salida.destino }} · {{ fechaCorta(salida.fecha_hora_llegada_estimada) }}</div>
        </div>
      </div>
      <dl class="grid grid-cols-2 gap-x-4 gap-y-3 border-t border-dashed border-line-strong pt-4 text-sm sm:grid-cols-4">
        <div><dt class="text-xs text-muted">Pasajero</dt><dd class="font-semibold">{{ boleto.pasajero }}</dd></div>
        <div><dt class="text-xs text-muted">Documento</dt><dd class="font-semibold">{{ boleto.documento }}</dd></div>
        <div><dt class="text-xs text-muted">Asiento</dt><dd class="font-semibold">{{ boleto.numero_asiento }} · {{ boleto.clase }}</dd></div>
        <div>
          <dt class="text-xs text-muted">Tarifa</dt>
          <dd class="font-semibold">{{ TIPO_PASAJERO[boleto.tipo_pasajero] ?? boleto.tipo_pasajero }} · {{ bs(boleto.total_bs) }}</dd>
        </div>
      </dl>
      <div class="flex flex-wrap items-center gap-2 text-xs text-muted">
        <StatusBadge size="sm" v-bind="etiqueta(ESTADO_BOLETO, boleto.estado)" :label="etiqueta(ESTADO_BOLETO, boleto.estado).label" />
        <span v-if="salida.oficina_salida">Sale de {{ salida.oficina_salida }}<template v-if="salida.anden"> · Andén {{ salida.anden }}</template></span>
        <span v-if="boleto.viaja_con_perro_guia">· Viaja con perro guía</span>
      </div>
    </div>
    <div
      class="flex flex-col items-center justify-center gap-2 border-t-2 border-dashed border-noche-600 bg-noche-900 p-5 sm:w-52 sm:border-t-0 sm:border-l-2"
    >
      <QrCode v-if="boleto.codigo_qr" :value="boleto.codigo_qr" :size="128" :label="`QR de abordaje del boleto ${boleto.numero_boleto}`" />
      <span v-else class="px-4 text-center text-sm text-noche-200">El QR aparece cuando el pago se confirma</span>
      <span v-if="boleto.codigo_qr" class="text-xs text-noche-200">Mostrar al abordar</span>
    </div>
  </article>
</template>
