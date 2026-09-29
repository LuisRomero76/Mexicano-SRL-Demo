<script setup lang="ts">
defineProps<{ label: string; hint?: string; disabled?: boolean }>()
const modelo = defineModel<boolean>()
</script>

<template>
  <label class="flex cursor-pointer items-start gap-3 text-[15px]" :class="disabled ? 'cursor-not-allowed opacity-60' : ''">
    <input v-model="modelo" type="checkbox" :disabled="disabled" class="mt-0.5 size-[18px] shrink-0 accent-carmin-600" />
    <span class="flex flex-col">
      <span>{{ label }}</span>
      <span v-if="hint" class="text-[13px] text-muted">{{ hint }}</span>
    </span>
  </label>
</template>
