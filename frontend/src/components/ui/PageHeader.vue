<script setup lang="ts">
import { ChevronRight } from '@lucide/vue'
import { RouterLink, type RouteLocationRaw } from 'vue-router'

defineProps<{ title: string; subtitle?: string; crumbs?: { label: string; to?: RouteLocationRaw }[] }>()
</script>

<template>
  <header class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
    <div class="min-w-0">
      <nav v-if="crumbs?.length" aria-label="Ruta de navegación" class="mb-1 flex flex-wrap items-center gap-1 text-[13px] text-muted">
        <template v-for="(c, i) in crumbs" :key="i">
          <RouterLink v-if="c.to" :to="c.to" class="hover:text-fg hover:underline">{{ c.label }}</RouterLink>
          <span v-else class="font-medium text-fg">{{ c.label }}</span>
          <ChevronRight v-if="i < crumbs.length - 1" class="size-3.5" aria-hidden="true" />
        </template>
      </nav>
      <h1 class="text-2xl font-bold text-fg md:text-[26px]">{{ title }}</h1>
      <p v-if="subtitle" class="mt-1 text-sm text-muted">{{ subtitle }}</p>
      <slot name="meta" />
    </div>
    <div v-if="$slots.default" class="flex flex-wrap items-center gap-2"><slot /></div>
  </header>
</template>
