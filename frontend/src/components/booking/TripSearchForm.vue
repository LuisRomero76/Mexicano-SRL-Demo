<script setup lang="ts">
import { ArrowLeftRight, CalendarDays, MapPin, Search, Users } from '@lucide/vue'
import { computed, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useRutas } from '@/api/queries'
import BaseButton from '@/components/ui/BaseButton.vue'
import { hoyISO, sumarDias } from '@/lib/format'

const props = withDefaults(
  defineProps<{
    layout?: 'horizontal' | 'stacked'
    initial?: { origen?: string; destino?: string; fecha?: string; pasajeros?: number }
  }>(),
  { layout: 'horizontal' },
)
const emit = defineEmits<{ submitted: [] }>()
const router = useRouter()
const { data: rutas } = useRutas()

const form = reactive({
  origen: props.initial?.origen ?? 'Sucre',
  destino: props.initial?.destino ?? 'Santa Cruz',
  fecha: props.initial?.fecha ?? sumarDias(hoyISO(), 1),
  pasajeros: props.initial?.pasajeros ?? 1,
})

const origenes = computed(() => [...new Set((rutas.value ?? []).map((r) => r.origen))].sort())
const destinos = computed(() =>
  [...new Set((rutas.value ?? []).filter((r) => r.origen === form.origen).map((r) => r.destino))].sort(),
)
watch(destinos, (lista) => {
  if (lista.length && !lista.includes(form.destino)) form.destino = lista[0]
})

const minimo = hoyISO()
const maximo = sumarDias(hoyISO(), 30)

function intercambiar(): void {
  const destinoPrevio = form.destino
  const valido = (rutas.value ?? []).some((r) => r.origen === destinoPrevio && r.destino === form.origen)
  if (!valido) return
  form.destino = form.origen
  form.origen = destinoPrevio
}

function buscar(): void {
  void router.push({
    name: 'resultados',
    query: { origen: form.origen, destino: form.destino, fecha: form.fecha, pasajeros: String(form.pasajeros) },
  })
  emit('submitted')
}

const campo =
  'flex h-14 items-center gap-2.5 rounded-xl border-[1.5px] border-line-strong bg-surface px-3.5 focus-within:border-noche-900 focus-within:ring-4 focus-within:ring-(--ring)'
const etiqueta = 'text-[11px] font-bold tracking-wider text-muted uppercase'
const control = 'w-full min-w-0 appearance-none bg-transparent text-base font-semibold text-fg outline-none'
</script>

<template>
  <form
    class="flex gap-3"
    :class="layout === 'horizontal' ? 'flex-col lg:flex-row lg:items-end' : 'flex-col'"
    aria-label="Buscar pasajes"
    @submit.prevent="buscar"
  >
    <div class="flex flex-1 items-end gap-2" :class="layout === 'stacked' ? 'relative flex-col items-stretch' : 'flex-col sm:flex-row sm:items-end'">
      <div class="flex w-full flex-1 flex-col gap-1.5">
        <label for="busca-origen" :class="etiqueta">Origen</label>
        <div :class="campo">
          <MapPin class="size-[18px] shrink-0 text-muted" aria-hidden="true" />
          <select id="busca-origen" v-model="form.origen" :class="control">
            <option v-for="c in origenes" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
      </div>
      <button
        type="button"
        class="z-10 flex size-11 shrink-0 items-center justify-center self-center rounded-full border-[1.5px] border-line-strong bg-surface text-noche-900 transition hover:rotate-180 hover:border-noche-900 sm:mb-1.5 sm:self-end dark:text-fg"
        :class="layout === 'stacked' ? 'absolute top-[50px] right-3 sm:self-auto' : ''"
        aria-label="Intercambiar origen y destino"
        @click="intercambiar"
      >
        <ArrowLeftRight class="size-[18px]" :class="layout === 'stacked' ? 'rotate-90' : ''" />
      </button>
      <div class="flex w-full flex-1 flex-col gap-1.5">
        <label for="busca-destino" :class="etiqueta">Destino</label>
        <div :class="campo">
          <MapPin class="size-[18px] shrink-0 text-carmin-600" aria-hidden="true" />
          <select id="busca-destino" v-model="form.destino" :class="control">
            <option v-for="c in destinos" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
      </div>
    </div>
    <div class="grid grid-cols-[1fr_auto] gap-3" :class="layout === 'horizontal' ? 'lg:flex lg:gap-3' : ''">
      <div class="flex flex-col gap-1.5" :class="layout === 'horizontal' ? 'lg:w-52' : ''">
        <label for="busca-fecha" :class="etiqueta">Fecha de viaje</label>
        <div :class="campo">
          <CalendarDays class="size-[18px] shrink-0 text-muted" aria-hidden="true" />
          <input id="busca-fecha" v-model="form.fecha" type="date" :min="minimo" :max="maximo" required :class="control" />
        </div>
      </div>
      <div class="flex w-32 flex-col gap-1.5">
        <label for="busca-pax" :class="etiqueta">Pasajeros</label>
        <div :class="campo">
          <Users class="size-[18px] shrink-0 text-muted" aria-hidden="true" />
          <select id="busca-pax" v-model.number="form.pasajeros" :class="control">
            <option v-for="n in 6" :key="n" :value="n">{{ n }}</option>
          </select>
        </div>
      </div>
    </div>
    <BaseButton type="submit" size="lg" class="h-14 lg:px-8" :block="layout === 'stacked'">
      <Search class="size-5" aria-hidden="true" />Buscar
    </BaseButton>
  </form>
</template>
