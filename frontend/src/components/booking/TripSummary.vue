<script setup lang="ts">
import type { Schemas } from '@/api/client'
import { fechaCorta, hora } from '@/lib/format'

defineProps<{ salida: Schemas['SalidaResumen'] | Schemas['SalidaDeReserva']; etiqueta?: string }>()
</script>

<template>
  <div class="flex flex-col gap-1.5 bg-noche-900 px-5 py-5 text-white">
    <span class="text-xs font-semibold tracking-[0.12em] text-carmin-200 uppercase">{{ etiqueta ?? 'Tu viaje' }}</span>
    <strong class="font-display text-xl">{{ salida.origen }} → {{ salida.destino }}</strong>
    <span class="text-sm text-noche-200">
      {{ fechaCorta(salida.fecha_hora_salida) }} · {{ hora(salida.fecha_hora_salida) }} → {{ hora(salida.fecha_hora_llegada_estimada) }}
      <template v-if="salida.anden"> · Andén {{ salida.anden }}</template>
    </span>
    <slot />
  </div>
</template>
