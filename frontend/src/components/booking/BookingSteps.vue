<script setup lang="ts">
import { Check } from '@lucide/vue'

const props = defineProps<{ paso: 1 | 2 | 3 | 4 }>()
const pasos = ['Salida', 'Asientos', 'Pasajeros', 'Pago']
const estado = (i: number) => (i + 1 < props.paso ? 'hecho' : i + 1 === props.paso ? 'actual' : 'pendiente')
</script>

<template>
  <nav aria-label="Pasos de la compra" class="border-b border-line bg-surface">
    <ol class="contenedor flex h-14 items-center gap-2 overflow-x-auto text-sm sm:gap-4">
      <li v-for="(p, i) in pasos" :key="p" class="flex shrink-0 items-center gap-2 sm:gap-4">
        <span
          class="flex items-center gap-2"
          :class="{ 'font-semibold text-exito-600': estado(i) === 'hecho', 'font-bold text-fg': estado(i) === 'actual', 'text-muted': estado(i) === 'pendiente' }"
          :aria-current="estado(i) === 'actual' ? 'step' : undefined"
        >
          <span
            class="flex size-6 items-center justify-center rounded-full text-xs font-bold"
            :class="{
              'bg-exito-600 text-white': estado(i) === 'hecho',
              'bg-carmin-600 text-white': estado(i) === 'actual',
              'border-[1.5px] border-muted/60': estado(i) === 'pendiente',
            }"
          >
            <Check v-if="estado(i) === 'hecho'" class="size-3.5" aria-hidden="true" />
            <template v-else>{{ i + 1 }}</template>
          </span>
          <span :class="estado(i) === 'actual' ? '' : 'hidden sm:inline'">{{ p }}</span>
        </span>
        <span v-if="i < pasos.length - 1" class="h-px w-6 bg-line-strong sm:w-10" aria-hidden="true" />
      </li>
    </ol>
  </nav>
</template>
