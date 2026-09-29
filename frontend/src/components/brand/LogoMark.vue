<script setup lang="ts">
withDefaults(defineProps<{ size?: number; wordmark?: boolean; tone?: 'light' | 'dark'; subtitle?: string }>(), {
  size: 36,
  wordmark: true,
  tone: 'light',
})
</script>

<template>
  <span class="inline-flex items-center gap-3">
    <svg :width="size" :height="size" viewBox="0 0 44 44" aria-hidden="true" class="shrink-0">
      <rect width="44" height="44" rx="11" fill="#B3122E" />
      <path d="M11 30 C17 30 18 14 24 14 S31 24 33 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" />
      <circle cx="11" cy="30" r="3.2" fill="#0B1B33" />
      <circle cx="33" cy="24" r="3.2" fill="#fff" />
    </svg>
    <span v-if="wordmark" class="flex flex-col leading-tight">
      <span
        class="font-display text-[17px] font-bold tracking-[0.06em]"
        :class="tone === 'light' ? 'text-white' : 'text-noche-900 dark:text-white'"
      >
        EL MEXICANO
      </span>
      <span v-if="subtitle" class="text-xs" :class="tone === 'light' ? 'text-noche-200' : 'text-muted'">{{ subtitle }}</span>
    </span>
  </span>
</template>
