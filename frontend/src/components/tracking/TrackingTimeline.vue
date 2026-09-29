<script setup lang="ts">
import type { Schemas } from '@/api/client'
import { fechaCorta, hora } from '@/lib/format'
import { ESTADO_ENCOMIENDA, etiqueta } from '@/lib/labels'

defineProps<{ eventos: Schemas['EventoOut'][]; /** El primero es el más reciente */ recienteArriba?: boolean }>()
</script>

<template>
  <ol class="flex flex-col">
    <li v-for="(e, i) in eventos" :key="i" class="flex gap-4">
      <div class="flex flex-col items-center" aria-hidden="true">
        <span
          class="mt-1 rounded-full"
          :class="i === 0 ? 'size-3.5 bg-turquesa-600 ring-4 ring-turquesa-50 dark:ring-turquesa-600/25' : 'size-3 bg-muted/60'"
        />
        <span v-if="i < eventos.length - 1" class="w-0.5 flex-1 bg-line-strong" />
      </div>
      <div class="flex flex-col gap-0.5 pb-5">
        <strong class="text-[15px]">{{ etiqueta(ESTADO_ENCOMIENDA, e.estado).label }}</strong>
        <span class="text-sm text-fg/80">{{ e.descripcion }}</span>
        <span class="text-[13px] text-muted">{{ fechaCorta(e.ocurrido_at) }}, {{ hora(e.ocurrido_at) }}<template v-if="e.ciudad"> · {{ e.ciudad }}</template></span>
      </div>
    </li>
  </ol>
</template>
