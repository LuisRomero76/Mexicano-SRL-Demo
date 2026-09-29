<script setup lang="ts">
import { ShieldAlert } from '@lucide/vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
</script>

<template>
  <EmptyState :icon="ShieldAlert" title="No tienes acceso a esta sección" text="Si crees que deberías tenerlo, pide a un administrador que revise tu rol.">
    <BaseButton :to="{ name: 'admin-tablero' }">Ir al tablero</BaseButton>
  </EmptyState>
</template>
