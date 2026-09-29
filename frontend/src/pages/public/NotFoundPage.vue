<script setup lang="ts">
import { MapPinOff } from '@lucide/vue'
import BaseButton from '@/components/ui/BaseButton.vue'
</script>

<template>
  <div class="contenedor flex flex-col items-center gap-4 py-24 text-center">
    <span class="flex size-16 items-center justify-center rounded-full bg-carmin-50 text-carmin-600"><MapPinOff class="size-8" aria-hidden="true" /></span>
    <p class="codigo text-sm text-muted">404</p>
    <h1 class="text-3xl font-bold">Esta ruta no existe</h1>
    <p class="max-w-md text-muted">La página que buscas no está disponible. Revisa la dirección o vuelve al inicio.</p>
    <div class="flex flex-wrap justify-center gap-3">
      <BaseButton :to="{ name: 'inicio' }">Ir al inicio</BaseButton>
      <BaseButton variant="outline" :to="{ name: 'ayuda' }">Centro de ayuda</BaseButton>
    </div>
  </div>
</template>
