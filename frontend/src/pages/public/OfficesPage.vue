<script setup lang="ts">
import { Clock3, MapPin, MessageCircle, Navigation, Phone } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useOficinasPublicas } from '@/api/queries'
import ErrorState from '@/components/ui/ErrorState.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { telefono, whatsappUrl } from '@/lib/format'
import { TIPO_OFICINA } from '@/lib/labels'

const { data: oficinas, isLoading, isError, error, refetch } = useOficinasPublicas()
const ciudad = ref('Todas')
const ciudades = computed(() => ['Todas', ...new Set((oficinas.value ?? []).map((o) => o.ciudad))])
const filtradas = computed(() => (oficinas.value ?? []).filter((o) => ciudad.value === 'Todas' || o.ciudad === ciudad.value))
const porCiudad = computed(() => {
  const grupos = new Map<string, typeof filtradas.value>()
  for (const o of filtradas.value) grupos.set(o.ciudad, [...(grupos.get(o.ciudad) ?? []), o])
  return [...grupos.entries()]
})
</script>

<template>
  <div>
    <section class="bg-noche-900 text-white">
      <div class="contenedor py-10 sm:py-14">
        <h1 class="text-[34px] font-bold sm:text-[44px]">Boleterías y bodegas</h1>
        <p class="mt-2 max-w-2xl text-noche-200">Boleterías de 07:00 a 20:00 y bodegas de 08:00 a 18:00 en 7 ciudades.</p>
      </div>
    </section>
    <div class="contenedor flex flex-col gap-6 py-8">
      <div class="flex gap-2 overflow-x-auto pb-1" role="group" aria-label="Filtrar por ciudad">
        <button
          v-for="c in ciudades"
          :key="c"
          type="button"
          class="h-10 shrink-0 rounded-full border px-4 text-sm font-semibold transition-colors"
          :class="ciudad === c ? 'border-noche-900 bg-noche-900 text-white' : 'border-line-strong bg-surface hover:border-noche-400'"
          :aria-pressed="ciudad === c"
          @click="ciudad = c"
        >
          {{ c }}
        </button>
      </div>

      <ErrorState v-if="isError" :error="error" @retry="refetch()" />
      <div v-else-if="isLoading" class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <SkeletonBlock v-for="n in 6" :key="n" class="h-56 rounded-2xl" />
      </div>
      <section v-for="[nombre, lista] in porCiudad" v-else :key="nombre" class="flex flex-col gap-3">
        <h2 class="text-xl font-bold text-noche-900">{{ nombre }}</h2>
        <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <article v-for="o in lista" :key="o.oficina_id" class="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-5">
            <div class="flex items-start justify-between gap-2">
              <h3 class="font-sans text-base font-bold">{{ o.nombre }}</h3>
              <StatusBadge size="sm" :dot="false" :tono="o.tipo === 'boleteria' ? 'carmin' : 'info'" :label="TIPO_OFICINA[o.tipo]" />
            </div>
            <p class="flex items-start gap-2 text-sm"><MapPin class="mt-0.5 size-4 shrink-0 text-muted" aria-hidden="true" />{{ o.direccion }}<template v-if="o.referencia">, {{ o.referencia }}</template></p>
            <p v-if="o.horario_texto" class="flex items-center gap-2 text-sm text-muted"><Clock3 class="size-4 shrink-0" aria-hidden="true" />{{ o.horario_texto }}</p>
            <div class="mt-auto flex flex-wrap gap-2 pt-2">
              <a v-if="o.telefono_e164" :href="`tel:+${o.telefono_e164}`" class="inline-flex h-10 items-center gap-1.5 rounded-control border-[1.5px] border-line-strong px-3 text-sm font-semibold hover:bg-surface-2">
                <Phone class="size-4" aria-hidden="true" />{{ telefono(o.telefono_e164) }}
              </a>
              <a v-if="o.whatsapp_e164" :href="whatsappUrl(o.whatsapp_e164)" target="_blank" rel="noopener noreferrer" class="inline-flex h-10 items-center gap-1.5 rounded-control bg-exito-600 px-3 text-sm font-semibold text-white hover:bg-exito-800">
                <MessageCircle class="size-4" aria-hidden="true" />WhatsApp
              </a>
              <a v-if="o.url_mapa" :href="o.url_mapa" target="_blank" rel="noopener noreferrer" class="inline-flex h-10 items-center gap-1.5 rounded-control bg-noche-900 px-3 text-sm font-semibold text-white hover:bg-noche-800">
                <Navigation class="size-4" aria-hidden="true" />Cómo llegar
              </a>
            </div>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>
