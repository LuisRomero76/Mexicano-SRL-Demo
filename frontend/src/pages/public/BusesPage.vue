<script setup lang="ts">
import { Armchair, Bath, Luggage, PawPrint, Snowflake, Thermometer, Tv, Usb } from '@lucide/vue'
import type { Component } from 'vue'
import { usePoliticas, useTiposAsiento } from '@/api/queries'
import BaseButton from '@/components/ui/BaseButton.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'

const { data: tipos, isLoading } = useTiposAsiento()
const { data: politicas } = usePoliticas()

const iconos: Record<string, Component> = {
  asientos_reclinables: Armchair,
  cargadores_usb: Usb,
  calefaccion: Thermometer,
  bano_unisex: Bath,
  tv_individual: Tv,
  tv_cabina: Tv,
  aire_acondicionado: Snowflake,
}
</script>

<template>
  <div>
    <section class="bg-noche-900 text-white">
      <div class="contenedor py-10 sm:py-14">
        <h1 class="text-[34px] font-bold sm:text-[44px]">Nuestros buses</h1>
        <p class="mt-2 max-w-2xl text-noche-200">
          Flota de dos pisos pensada para viajar de noche: Suite Cama en la planta alta y Leito Cama en la planta baja.
        </p>
      </div>
    </section>
    <div class="contenedor flex flex-col gap-10 py-10">
      <div class="grid gap-6 lg:grid-cols-2">
        <template v-if="isLoading"><SkeletonBlock v-for="n in 2" :key="n" class="h-80 rounded-2xl" /></template>
        <article
          v-for="(t, i) in tipos ?? []"
          :key="t.id"
          class="flex flex-col gap-5 overflow-hidden rounded-3xl p-7 sm:p-8"
          :class="i === 0 ? 'bg-noche-900 text-white' : 'border border-line bg-surface'"
        >
          <div class="flex items-start justify-between gap-4">
            <div>
              <span class="text-xs font-bold tracking-[0.14em] uppercase" :class="i === 0 ? 'text-carmin-200' : 'text-carmin-600'">
                Planta {{ t.planta }}
              </span>
              <h2 class="mt-1 text-[30px] font-bold" :class="i === 0 ? '' : 'text-noche-900'">{{ t.nombre }}</h2>
            </div>
            <div class="text-right">
              <span class="font-display text-5xl font-bold" :class="i === 0 ? 'text-white' : 'text-noche-900'">{{ t.inclinacion_grados }}°</span>
              <p class="text-xs" :class="i === 0 ? 'text-noche-300' : 'text-muted'">de reclinación</p>
            </div>
          </div>
          <p :class="i === 0 ? 'text-noche-200' : 'text-muted'">{{ t.descripcion }}</p>
          <ul class="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <li
              v-for="c in t.comodidades"
              :key="c.codigo"
              class="flex flex-col items-start gap-2 rounded-2xl p-4 text-sm font-medium"
              :class="i === 0 ? 'bg-white/5' : 'bg-canvas'"
            >
              <component :is="iconos[c.codigo] ?? Armchair" class="size-5" :class="i === 0 ? 'text-carmin-200' : 'text-carmin-600'" aria-hidden="true" />
              {{ c.nombre }}
            </li>
          </ul>
        </article>
      </div>

      <section class="grid gap-4 md:grid-cols-2">
        <div class="flex gap-4 rounded-2xl border border-line bg-surface p-6">
          <Luggage class="size-7 shrink-0 text-noche-700" aria-hidden="true" />
          <div>
            <h2 class="font-sans text-lg font-bold">Equipaje</h2>
            <p class="mt-1 text-sm text-muted">
              {{ politicas?.equipaje_bodega_kg ?? 20 }} kg en bodega y {{ politicas?.equipaje_mano_kg ?? 5 }} kg de mano por pasajero.
              El exceso se cobra por kilo según la ruta.
            </p>
          </div>
        </div>
        <div class="flex gap-4 rounded-2xl border border-line bg-surface p-6">
          <PawPrint class="size-7 shrink-0 text-noche-700" aria-hidden="true" />
          <div>
            <h2 class="font-sans text-lg font-bold">Mascotas</h2>
            <p class="mt-1 text-sm text-muted">{{ politicas?.mascotas }}</p>
          </div>
        </div>
      </section>
      <BaseButton :to="{ name: 'inicio' }" size="lg" class="self-center">Buscar pasajes</BaseButton>
    </div>
  </div>
</template>
