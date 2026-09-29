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

defineProps<{ title: string; description?: string }>()
const abierto = defineModel<boolean>('open', { default: false })
</script>

<template>
  <DialogRoot v-model:open="abierto">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-50 bg-noche-950/50 data-[state=open]:animate-aparecer" />
      <DialogContent
        class="fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col bg-surface text-fg shadow-flotante outline-none data-[state=open]:animate-aparecer"
      >
        <div class="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div class="min-w-0">
            <DialogTitle class="text-lg font-semibold">{{ title }}</DialogTitle>
            <DialogDescription v-if="description" class="mt-1 text-sm text-muted">{{ description }}</DialogDescription>
          </div>
          <DialogClose class="-mr-2 flex size-10 items-center justify-center rounded-lg text-muted hover:bg-surface-2" aria-label="Cerrar">
            <X class="size-5" />
          </DialogClose>
        </div>
        <div class="flex-1 overflow-y-auto px-5 py-5"><slot /></div>
        <div v-if="$slots.footer" class="flex flex-wrap justify-end gap-2 border-t border-line px-5 py-4"><slot name="footer" /></div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
