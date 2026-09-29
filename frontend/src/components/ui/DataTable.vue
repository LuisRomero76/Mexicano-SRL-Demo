<script setup lang="ts" generic="T extends Record<string, any>">
import SkeletonBlock from './SkeletonBlock.vue'

export interface Columna {
  key: string
  label: string
  class?: string
  align?: 'left' | 'right' | 'center'
  /** Se oculta en pantallas pequeñas. */
  hideSm?: boolean
}

const props = defineProps<{
  columns: Columna[]
  rows: T[]
  rowKey: keyof T | ((fila: T) => string | number)
  loading?: boolean
  emptyText?: string
  clickable?: boolean
  caption?: string
}>()
const emit = defineEmits<{ rowClick: [fila: T] }>()

function clave(fila: T): string | number {
  return typeof props.rowKey === 'function' ? props.rowKey(fila) : (fila[props.rowKey] as string | number)
}
function alinear(c: Columna): string {
  return c.align === 'right' ? 'text-right' : c.align === 'center' ? 'text-center' : 'text-left'
}
function alTeclado(e: KeyboardEvent, fila: T): void {
  if (props.clickable && (e.key === 'Enter' || e.key === ' ')) {
    e.preventDefault()
    emit('rowClick', fila)
  }
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full min-w-[640px] border-collapse text-sm">
      <caption v-if="caption" class="sr-only">{{ caption }}</caption>
      <thead>
        <tr class="text-xs tracking-wide text-muted uppercase">
          <th
            v-for="c in columns"
            :key="c.key"
            scope="col"
            class="px-4 py-3 font-bold whitespace-nowrap first:pl-5 last:pr-5"
            :class="[alinear(c), c.hideSm ? 'hidden md:table-cell' : '', c.class]"
          >
            {{ c.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="n in 6" :key="n" class="border-t border-line">
            <td v-for="c in columns" :key="c.key" class="px-4 py-3.5 first:pl-5 last:pr-5" :class="c.hideSm ? 'hidden md:table-cell' : ''">
              <SkeletonBlock class="h-4 w-3/4" />
            </td>
          </tr>
        </template>
        <tr v-else-if="rows.length === 0">
          <td :colspan="columns.length" class="px-5 py-12 text-center text-[15px] text-muted">
            <slot name="empty">{{ emptyText ?? 'No hay resultados.' }}</slot>
          </td>
        </tr>
        <template v-else>
          <tr
            v-for="fila in rows"
            :key="clave(fila)"
            class="border-t border-line transition-colors"
            :class="clickable ? 'cursor-pointer hover:bg-surface-2 focus-visible:bg-surface-2' : ''"
            :tabindex="clickable ? 0 : undefined"
            @click="clickable && emit('rowClick', fila)"
            @keydown="alTeclado($event, fila)"
          >
            <td
              v-for="c in columns"
              :key="c.key"
              class="px-4 py-3 align-middle first:pl-5 last:pr-5"
              :class="[alinear(c), c.hideSm ? 'hidden md:table-cell' : '', c.class]"
            >
              <slot :name="`cell-${c.key}`" :row="fila" :value="fila[c.key]">{{ fila[c.key] ?? '—' }}</slot>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>
