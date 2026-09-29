<script setup lang="ts">
import { computed } from 'vue'
import type { Schemas } from '@/api/client'
import LogoMark from '@/components/brand/LogoMark.vue'
import QrCode from '@/components/ui/QrCode.vue'
import { bsExacto, fechaHora, fechaLarga, hora, telefono } from '@/lib/format'
import { TIPO_ENVIO } from '@/lib/labels'

const props = defineProps<{ encomienda: Schemas['EncomiendaOut'] }>()
const e = computed(() => props.encomienda)
const urlRastreo = computed(() => `${window.location.origin}/rastreo/${e.value.numero_guia}`)
</script>

<template>
  <article class="print-plain grid gap-5 rounded-2xl border border-line p-5 sm:grid-cols-[1fr_auto]">
    <div class="flex min-w-0 flex-col gap-4">
      <div class="flex items-center gap-2.5">
        <LogoMark :size="32" :wordmark="false" />
        <div>
          <p class="font-display text-sm font-bold tracking-wider">EL MEXICANO</p>
          <p class="text-xs text-muted">Comprobante de envío · {{ fechaHora(e.fecha_registro) }}</p>
        </div>
      </div>
      <div class="flex flex-wrap gap-x-8 gap-y-3">
        <div>
          <p class="text-xs text-muted">Número de guía</p>
          <p class="codigo text-3xl">{{ e.numero_guia }}</p>
        </div>
        <div v-if="e.codigo_retiro">
          <p class="text-xs text-muted">Código de retiro</p>
          <p class="codigo text-3xl text-carmin-600">{{ e.codigo_retiro }}</p>
        </div>
      </div>
      <dl class="grid grid-cols-1 gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
        <div><dt class="text-muted">Remitente</dt><dd class="font-medium">{{ e.remitente }}</dd></div>
        <div><dt class="text-muted">Destinatario</dt><dd class="font-medium">{{ e.destinatario_nombre }} · {{ telefono(e.destinatario_telefono_e164) }}</dd></div>
        <div><dt class="text-muted">Origen</dt><dd>{{ e.oficina_origen }}</dd></div>
        <div>
          <dt class="text-muted">Destino</dt>
          <dd>{{ e.modalidad_entrega === 'puerta_a_puerta' ? `A domicilio: ${e.direccion_entrega}` : e.oficina_destino }}</dd>
        </div>
        <div><dt class="text-muted">Envío</dt><dd>{{ TIPO_ENVIO[e.tipo_envio] }} · {{ e.peso_kg }} kg · {{ e.cantidad_bultos }} bulto(s){{ e.es_fragil ? ' · FRÁGIL' : '' }}</dd></div>
        <div><dt class="text-muted">Contenido</dt><dd>{{ e.descripcion_contenido }}</dd></div>
        <div>
          <dt class="text-muted">Precio</dt>
          <dd class="font-semibold">{{ bsExacto(e.precio_bs) }} · {{ e.estado_pago === 'pendiente' ? 'por cobrar en destino' : e.pago_en === 'credito_corporativo' ? 'crédito corporativo' : 'pagado' }}</dd>
        </div>
        <div v-if="e.fecha_estimada_entrega"><dt class="text-muted">Llegada estimada</dt><dd>{{ fechaLarga(e.fecha_estimada_entrega) }}, {{ hora(e.fecha_estimada_entrega) }}</dd></div>
      </dl>
      <p class="text-xs text-muted">El destinatario retira presentando su documento y el código de retiro. Rastrea el envío en elmexicanosrl.com con el número de guía.</p>
    </div>
    <div class="flex flex-col items-center gap-2">
      <QrCode :value="urlRastreo" :size="132" label="QR para rastrear el envío" />
      <span class="text-xs text-muted">Escanea para rastrear</span>
    </div>
  </article>
</template>
