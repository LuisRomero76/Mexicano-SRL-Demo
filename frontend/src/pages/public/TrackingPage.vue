<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { ArrowRight, Clock3, IdCard, MapPin, Package, Phone, Search, Wallet } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, unwrap } from '@/api/client'
import TrackingTimeline from '@/components/tracking/TrackingTimeline.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { fechaLarga, hora, telefono } from '@/lib/format'
import { ESTADO_ENCOMIENDA, TIPO_ENVIO, etiqueta } from '@/lib/labels'

const route = useRoute()
const router = useRouter()
const guiaRuta = computed(() => (typeof route.params.guia === 'string' ? route.params.guia : ''))
const entrada = ref(guiaRuta.value)
watch(guiaRuta, (g) => (entrada.value = g))
const errorEntrada = ref<string | null>(null)

const rastreo = useQuery({
  queryKey: computed(() => ['rastreo', guiaRuta.value]),
  queryFn: () => unwrap(api.GET('/api/v1/encomiendas/rastreo/{numero_guia}', { params: { path: { numero_guia: guiaRuta.value } } })),
  enabled: computed(() => guiaRuta.value.length === 8),
  refetchInterval: 120_000,
})

function buscar(): void {
  const limpia = entrada.value.replace(/\D/g, '')
  if (limpia.length !== 8) {
    errorEntrada.value = 'La guía tiene 8 dígitos.'
    return
  }
  errorEntrada.value = null
  void router.replace({ name: 'rastreo', params: { guia: limpia } })
}

const PASOS = ['Recibida', 'En camino', 'Llegó', 'Para recoger', 'Entregada']
const paso = computed(() => {
  const e = rastreo.data.value?.estado
  const mapa: Record<string, number> = {
    registrada: 0,
    recibida_en_origen: 1,
    en_transito: 2,
    llegada_a_destino: 3,
    lista_para_retiro: 4,
    en_reparto: 4,
    intento_fallido: 4,
    entregada: 5,
  }
  return e ? (mapa[e] ?? 0) : 0
})
const pasos = computed(() =>
  rastreo.data.value?.modalidad_entrega === 'puerta_a_puerta' ? [...PASOS.slice(0, 3), 'En reparto', 'Entregada'] : PASOS,
)
const estado = computed(() => etiqueta(ESTADO_ENCOMIENDA, rastreo.data.value?.estado))
</script>

<template>
  <div>
    <section class="bg-noche-900 text-white">
      <div class="contenedor flex flex-col gap-5 py-8 sm:py-10">
        <div>
          <h1 class="text-[28px] font-bold sm:text-[34px]">Rastrea tu envío</h1>
          <p class="mt-1 text-noche-200">Sigue tu encomienda o carga en tiempo real con el número de guía.</p>
        </div>
        <form class="flex max-w-xl gap-2" @submit.prevent="buscar">
          <label for="rastreo-guia" class="sr-only">Número de guía</label>
          <input
            id="rastreo-guia"
            v-model="entrada"
            inputmode="numeric"
            maxlength="12"
            placeholder="Número de guía (8 dígitos)"
            class="codigo h-14 min-w-0 flex-1 rounded-xl border-0 bg-white px-4 text-lg text-noche-900 outline-none placeholder:font-sans placeholder:text-base placeholder:font-normal placeholder:tracking-normal focus:ring-4 focus:ring-carmin-500/40"
            :aria-invalid="!!errorEntrada || undefined"
            aria-describedby="rastreo-error"
          />
          <BaseButton type="submit" size="lg" class="h-14" aria-label="Buscar guía" :loading="rastreo.isFetching.value">
            <Search class="size-5" aria-hidden="true" /><span class="hidden sm:inline">Rastrear</span>
          </BaseButton>
        </form>
        <p v-if="errorEntrada" id="rastreo-error" class="text-sm font-semibold text-carmin-200" role="alert">{{ errorEntrada }}</p>
      </div>
    </section>

    <div class="contenedor py-8">
      <div v-if="!guiaRuta" class="flex flex-col items-center gap-3 py-10 text-center text-muted">
        <Package class="size-10" aria-hidden="true" />
        <p>La guía de 8 dígitos aparece en el comprobante que te dieron al enviar.</p>
      </div>
      <div v-else-if="rastreo.isLoading.value" class="grid gap-5 lg:grid-cols-2">
        <SkeletonBlock class="h-56 rounded-2xl" /><SkeletonBlock class="h-56 rounded-2xl" />
      </div>
      <ErrorState v-else-if="rastreo.isError.value" :error="rastreo.error.value" title="No encontramos esa guía" @retry="rastreo.refetch()" />

      <div v-else-if="rastreo.data.value" class="grid items-start gap-6 lg:grid-cols-[1.1fr_1fr]">
        <div class="flex flex-col gap-5">
          <section class="flex flex-col gap-5 rounded-2xl border border-line bg-surface p-5 sm:p-6">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <StatusBadge :tono="estado.tono" :label="rastreo.data.value.estado_legible" />
              <span class="text-sm text-muted">
                Guía <span class="codigo text-fg">{{ rastreo.data.value.numero_guia }}</span> ·
                {{ TIPO_ENVIO[rastreo.data.value.tipo_envio] }} · {{ rastreo.data.value.cantidad_bultos }}
                {{ rastreo.data.value.cantidad_bultos === 1 ? 'bulto' : 'bultos' }}
              </span>
            </div>
            <h2 class="flex flex-wrap items-center gap-3 text-2xl font-bold text-noche-900">
              {{ rastreo.data.value.ciudad_origen }} <ArrowRight class="size-6 text-carmin-600" aria-hidden="true" /> {{ rastreo.data.value.ciudad_destino }}
            </h2>
            <div :aria-label="`Progreso: paso ${paso} de 5`" role="img">
              <div class="flex gap-1.5">
                <span v-for="n in 5" :key="n" class="h-1.5 flex-1 rounded-full" :class="n <= paso ? 'bg-turquesa-600' : 'bg-surface-2'" />
              </div>
              <div class="mt-2 hidden justify-between text-xs text-muted sm:flex">
                <span v-for="(p, i) in pasos" :key="p" :class="i + 1 === paso ? 'font-bold text-turquesa-800' : ''">{{ p }}</span>
              </div>
            </div>
            <p class="text-[15px] leading-relaxed">{{ rastreo.data.value.mensaje }}</p>
            <p v-if="rastreo.data.value.fecha_estimada_entrega && rastreo.data.value.estado !== 'entregada'" class="flex items-center gap-2 text-sm text-muted">
              <Clock3 class="size-4" aria-hidden="true" />Llegada estimada: {{ fechaLarga(rastreo.data.value.fecha_estimada_entrega) }},
              {{ hora(rastreo.data.value.fecha_estimada_entrega) }}
            </p>
          </section>

          <section v-if="rastreo.data.value.oficina_retiro" class="flex flex-col gap-3 rounded-2xl bg-noche-900 p-5 text-white sm:p-6">
            <span class="text-xs font-bold tracking-[0.12em] text-carmin-200">{{ rastreo.data.value.lista_para_retiro ? 'RECÓGELA EN' : 'SE ENTREGARÁ EN' }}</span>
            <strong class="font-display text-xl">{{ rastreo.data.value.oficina_retiro }}</strong>
            <span class="flex items-start gap-2 text-sm text-noche-200"><MapPin class="mt-0.5 size-4 shrink-0" aria-hidden="true" />{{ rastreo.data.value.direccion_retiro }}</span>
            <span v-if="rastreo.data.value.horario_oficina" class="flex items-center gap-2 text-sm text-noche-200">
              <Clock3 class="size-4" aria-hidden="true" />{{ rastreo.data.value.horario_oficina }}
            </span>
            <a
              v-if="rastreo.data.value.telefono_oficina"
              :href="`tel:+${rastreo.data.value.telefono_oficina}`"
              class="mt-2 inline-flex h-11 w-fit items-center gap-2 rounded-xl border border-noche-600 px-4 text-sm font-semibold hover:bg-white/5"
            >
              <Phone class="size-4" aria-hidden="true" />Llamar {{ telefono(rastreo.data.value.telefono_oficina) }}
            </a>
          </section>

          <div class="grid gap-3 sm:grid-cols-2">
            <div class="flex gap-3 rounded-2xl border border-line bg-surface p-4 text-sm">
              <IdCard class="size-5 shrink-0 text-noche-700" aria-hidden="true" />
              <span>Para recoger presenta tu <strong>documento</strong> y el <strong>código de retiro de 4 dígitos</strong> que recibió el remitente.</span>
            </div>
            <div v-if="rastreo.data.value.pago_pendiente_en_destino" class="flex gap-3 rounded-2xl bg-aviso-50 p-4 text-sm text-aviso-800">
              <Wallet class="size-5 shrink-0" aria-hidden="true" />
              <span>Este envío tiene <strong>pago en destino</strong>: se cancela al recogerlo.</span>
            </div>
          </div>
        </div>

        <section class="rounded-2xl border border-line bg-surface p-5 sm:p-6">
          <h2 class="mb-4 text-lg font-bold">Historial</h2>
          <TrackingTimeline :eventos="rastreo.data.value.eventos" />
          <p class="text-xs text-muted">Por tu privacidad no mostramos nombres, teléfonos ni montos.</p>
        </section>
      </div>
    </div>
  </div>
</template>
