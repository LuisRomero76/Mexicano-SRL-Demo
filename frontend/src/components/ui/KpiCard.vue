<script setup lang="ts">
import type { Component } from 'vue'
import SkeletonBlock from './SkeletonBlock.vue'

defineProps<{ label: string; value: string; hint?: string; tone?: 'exito' | 'aviso' | 'neutro'; icon?: Component; loading?: boolean }>()
</script>

<template>
  <div class="flex flex-col gap-1.5 rounded-2xl border border-line bg-surface p-5">
    <div class="flex items-center justify-between gap-2 text-[13px] text-muted">
      <span>{{ label }}</span>
      <component :is="icon" v-if="icon" class="size-4.5" aria-hidden="true" />
    </div>
    <SkeletonBlock v-if="loading" class="h-8 w-32" />
    <span v-else class="font-display text-[28px] leading-tight font-bold tabular">{{ value }}</span>
    <span
      v-if="hint"
      class="text-[13px] font-semibold"
      :class="tone === 'exito' ? 'text-exito-600' : tone === 'aviso' ? 'text-aviso-700 dark:text-amber-300' : 'text-muted'"
    >
      {{ hint }}
    </span>
    <slot />
  </div>
</template>
