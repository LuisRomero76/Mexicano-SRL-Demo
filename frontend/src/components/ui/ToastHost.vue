<script setup lang="ts">
import { CircleAlert, CircleCheck, Info, X } from '@lucide/vue'
import { useToastStore } from '@/stores/toast'

const avisos = useToastStore()
const iconos = { exito: CircleCheck, error: CircleAlert, info: Info }
const colores = { exito: 'text-exito-600', error: 'text-peligro-600', info: 'text-info-600' }
</script>

<template>
  <div
    class="no-print pointer-events-none fixed inset-x-0 bottom-20 z-[60] flex flex-col items-center gap-2 px-4 sm:inset-x-auto sm:right-5 sm:bottom-5 sm:items-end"
    aria-live="polite"
    aria-relevant="additions"
  >
    <TransitionGroup
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="translate-y-2 opacity-0"
      leave-active-class="transition duration-150 ease-in"
      leave-to-class="opacity-0"
    >
      <div
        v-for="a in avisos.avisos"
        :key="a.id"
        class="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border border-line bg-surface p-4 text-fg shadow-flotante"
        :role="a.tipo === 'error' ? 'alert' : 'status'"
      >
        <component :is="iconos[a.tipo]" class="mt-0.5 size-5 shrink-0" :class="colores[a.tipo]" aria-hidden="true" />
        <div class="min-w-0 flex-1">
          <p class="text-sm font-semibold">{{ a.titulo }}</p>
          <p v-if="a.detalle" class="mt-0.5 text-sm text-muted">{{ a.detalle }}</p>
        </div>
        <button class="-m-1 flex size-8 items-center justify-center rounded-md text-muted hover:bg-surface-2" aria-label="Cerrar aviso" @click="avisos.cerrar(a.id)">
          <X class="size-4" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>
