<script setup lang="ts">
import QRCode from 'qrcode'
import { ref, watchEffect } from 'vue'

const props = withDefaults(defineProps<{ value: string; size?: number; label?: string }>(), { size: 160 })
const src = ref<string>('')

watchEffect(async () => {
  try {
    src.value = await QRCode.toDataURL(props.value, {
      width: props.size * 2,
      margin: 1,
      errorCorrectionLevel: 'M',
      color: { dark: '#0B1B33', light: '#FFFFFF' },
    })
  } catch {
    src.value = ''
  }
})
</script>

<template>
  <img
    v-if="src"
    :src="src"
    :width="size"
    :height="size"
    :alt="label ?? 'Código QR'"
    class="rounded-lg bg-white p-1.5"
  />
</template>
