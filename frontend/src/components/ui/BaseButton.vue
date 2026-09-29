<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, type RouteLocationRaw } from 'vue-router'
import SpinnerIcon from './SpinnerIcon.vue'

const props = withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'subtle' | 'white' | 'success'
    size?: 'sm' | 'md' | 'lg'
    type?: 'button' | 'submit' | 'reset'
    to?: RouteLocationRaw
    href?: string
    loading?: boolean
    disabled?: boolean
    block?: boolean
    iconOnly?: boolean
  }>(),
  { variant: 'primary', size: 'md', type: 'button' },
)

const clases = computed(() => {
  const base =
    'relative inline-flex items-center justify-center gap-2 font-semibold whitespace-nowrap rounded-control transition-colors select-none disabled:cursor-not-allowed aria-disabled:cursor-not-allowed'
  const tam = {
    sm: props.iconOnly ? 'size-9' : 'h-9 px-3 text-sm',
    md: props.iconOnly ? 'size-11' : 'h-11 px-4 text-[15px]',
    lg: props.iconOnly ? 'size-13' : 'h-13 px-6 text-base',
  }[props.size]
  const variante = {
    primary:
      'bg-carmin-600 text-white hover:bg-carmin-700 active:bg-carmin-800 disabled:bg-arena-300 disabled:text-muted',
    secondary: 'bg-noche-900 text-white hover:bg-noche-800 dark:bg-noche-700 dark:hover:bg-noche-600 disabled:opacity-50',
    outline:
      'border-[1.5px] border-noche-900 text-noche-900 bg-surface hover:bg-noche-100 dark:border-noche-300 dark:text-fg dark:hover:bg-surface-2 disabled:opacity-50',
    ghost: 'text-fg hover:bg-surface-2 disabled:opacity-50',
    subtle: 'border-[1.5px] border-line-strong bg-surface text-fg hover:bg-surface-2 disabled:opacity-50',
    danger: 'bg-peligro-600 text-white hover:bg-peligro-800 disabled:opacity-50',
    white: 'bg-white text-noche-900 hover:bg-noche-100',
    success: 'bg-exito-600 text-white hover:bg-exito-800 disabled:opacity-50',
  }[props.variant]
  return [base, tam, variante, props.block ? 'w-full' : ''].join(' ')
})

const inactivo = computed(() => props.disabled || props.loading)
</script>

<template>
  <RouterLink v-if="to && !inactivo" :to="to" :class="clases"><slot /></RouterLink>
  <a v-else-if="href && !inactivo" :href="href" :class="clases" target="_blank" rel="noopener noreferrer"><slot /></a>
  <button v-else :type="type" :class="clases" :disabled="inactivo" :aria-busy="loading || undefined">
    <span v-if="loading" class="absolute inset-0 flex items-center justify-center"><SpinnerIcon class="size-5" /></span>
    <span class="inline-flex items-center gap-2" :class="loading ? 'invisible' : ''"><slot /></span>
  </button>
</template>
