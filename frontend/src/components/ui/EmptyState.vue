<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{ title: string; text?: string; icon?: Component; compact?: boolean }>()
</script>

<template>
  <div class="flex flex-col items-center text-center" :class="compact ? 'gap-2 py-8' : 'gap-3 py-14'">
    <span v-if="icon" class="flex size-12 items-center justify-center rounded-full bg-surface-2 text-muted">
      <component :is="icon" class="size-6" aria-hidden="true" />
    </span>
    <p class="font-display text-lg font-semibold">{{ title }}</p>
    <p v-if="text" class="max-w-md text-[15px] text-muted">{{ text }}</p>
    <div v-if="$slots.default" class="mt-2 flex flex-wrap justify-center gap-2"><slot /></div>
  </div>
</template>
