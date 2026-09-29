<script setup lang="ts">
defineProps<{ tabs: { key: string; label: string; count?: number | null }[]; label: string }>()
const activo = defineModel<string>({ required: true })

function mover(e: KeyboardEvent, tabs: { key: string }[]): void {
  const i = tabs.findIndex((t) => t.key === activo.value)
  if (e.key === 'ArrowRight') activo.value = tabs[(i + 1) % tabs.length].key
  else if (e.key === 'ArrowLeft') activo.value = tabs[(i - 1 + tabs.length) % tabs.length].key
  else return
  e.preventDefault()
  ;(e.currentTarget as HTMLElement).querySelector<HTMLElement>('[aria-selected="true"]')?.focus()
}
</script>

<template>
  <div role="tablist" :aria-label="label" class="flex gap-1 overflow-x-auto border-b border-line" @keydown="mover($event, tabs)">
    <button
      v-for="t in tabs"
      :key="t.key"
      role="tab"
      type="button"
      :aria-selected="activo === t.key"
      :tabindex="activo === t.key ? 0 : -1"
      class="-mb-px flex h-12 shrink-0 items-center gap-2 border-b-[3px] px-3.5 text-sm transition-colors"
      :class="activo === t.key ? 'border-carmin-600 font-bold text-fg' : 'border-transparent font-semibold text-muted hover:text-fg'"
      @click="activo = t.key"
    >
      {{ t.label }}
      <span v-if="t.count != null" class="rounded-full bg-surface-2 px-2 py-0.5 text-xs font-bold text-muted">{{ t.count }}</span>
    </button>
  </div>
</template>
