<script setup lang="ts">
withDefaults(defineProps<{ title?: string; subtitle?: string; padded?: boolean; as?: string }>(), { padded: true })
</script>

<template>
  <component :is="as ?? 'section'" class="rounded-2xl border border-line bg-surface text-fg">
    <div v-if="title || $slots.actions" class="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
      <div class="min-w-0">
        <h2 v-if="title" class="font-sans text-base font-bold">{{ title }}</h2>
        <p v-if="subtitle" class="mt-0.5 text-[13px] text-muted">{{ subtitle }}</p>
      </div>
      <div class="flex items-center gap-2"><slot name="actions" /></div>
    </div>
    <div :class="padded === false ? '' : 'p-5'"><slot /></div>
  </component>
</template>
