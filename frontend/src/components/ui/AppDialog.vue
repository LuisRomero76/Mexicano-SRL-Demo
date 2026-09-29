<script setup lang="ts">
import { X } from '@lucide/vue'
import {
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from 'reka-ui'

withDefaults(defineProps<{ title: string; description?: string; size?: 'sm' | 'md' | 'lg' | 'xl' }>(), {
  size: 'md',
})
const abierto = defineModel<boolean>('open', { default: false })
</script>

<template>
  <DialogRoot v-model:open="abierto">
    <DialogPortal>
      <DialogOverlay class="no-print fixed inset-0 z-50 bg-noche-950/55 backdrop-blur-[2px] data-[state=open]:animate-aparecer" />
      <DialogContent
        class="fixed inset-x-0 bottom-0 z-50 flex max-h-[92dvh] flex-col rounded-t-2xl bg-surface text-fg shadow-flotante outline-none data-[state=open]:animate-deslizar sm:inset-auto sm:top-1/2 sm:left-1/2 sm:w-[calc(100vw-2rem)] sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-2xl sm:data-[state=open]:animate-aparecer"
        :class="{ sm: 'sm:max-w-md', md: 'sm:max-w-lg', lg: 'sm:max-w-2xl', xl: 'sm:max-w-4xl' }[size]"
      >
        <div class="flex items-start justify-between gap-4 border-b border-line px-5 py-4 sm:px-6">
          <div class="min-w-0">
            <DialogTitle class="text-lg font-semibold">{{ title }}</DialogTitle>
            <DialogDescription v-if="description" class="mt-1 text-sm text-muted">{{ description }}</DialogDescription>
          </div>
          <DialogClose
            class="-mr-2 flex size-10 shrink-0 items-center justify-center rounded-lg text-muted hover:bg-surface-2 hover:text-fg"
            aria-label="Cerrar"
          >
            <X class="size-5" />
          </DialogClose>
        </div>
        <div class="overflow-y-auto px-5 py-5 sm:px-6"><slot /></div>
        <div v-if="$slots.footer" class="flex flex-col-reverse gap-2 border-t border-line px-5 py-4 sm:flex-row sm:justify-end sm:px-6">
          <slot name="footer" />
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
