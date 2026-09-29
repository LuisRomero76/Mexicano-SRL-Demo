<script setup lang="ts">
import { useMutation } from '@tanstack/vue-query'
import { Camera, CameraOff, CircleCheck, CircleX, Luggage, ScanLine } from '@lucide/vue'
import { onBeforeUnmount, reactive, ref } from 'vue'
import { ApiError, api, unwrap, type Schemas } from '@/api/client'
import BaseButton from '@/components/ui/BaseButton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SurfaceCard from '@/components/ui/SurfaceCard.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { bsExacto, hora } from '@/lib/format'
import { TIPO_PASAJERO } from '@/lib/labels'

interface Lectura {
  id: number
  ok: boolean
  titulo: string
  detalle: string
  boleto?: Schemas['BoletoOut']
  momento: string
}

const codigo = ref('')
const lecturas = ref<Lectura[]>([])
const ultimo = ref<Schemas['BoletoOut'] | null>(null)
let siguiente = 1

const abordar = useMutation({
  mutationFn: (valor: string) => unwrap(api.POST('/api/v1/admin/boletos/abordar', { body: { codigo: valor } })),
  onSuccess: (b) => {
    ultimo.value = b
    registrar({ ok: true, titulo: `Asiento ${b.numero_asiento} · ${b.pasajero}`, detalle: `${b.clase} · ${TIPO_PASAJERO[b.tipo_pasajero]} · ${b.numero_boleto}`, boleto: b })
    equipaje.peso = ''
  },
  onError: (e) => registrar({ ok: false, titulo: 'Boleto no válido', detalle: e instanceof ApiError ? e.message : 'Error al validar' }),
})

function registrar(l: Omit<Lectura, 'id' | 'momento'>): void {
  lecturas.value = [{ ...l, id: siguiente++, momento: hora(new Date()) }, ...lecturas.value].slice(0, 12)
  try {
    navigator.vibrate?.(l.ok ? 60 : [80, 60, 80])
  } catch {
    /* sin vibración */
  }
}

function validarManual(): void {
  const v = codigo.value.trim()
  if (!v) return
  abordar.mutate(v)
  codigo.value = ''
}

// --- Cámara con BarcodeDetector (Chrome/Edge/Android). Sin soporte: ingreso manual. ---
interface Detector {
  detect(fuente: HTMLVideoElement): Promise<{ rawValue: string }[]>
}
const soportaCamara = 'BarcodeDetector' in window && !!navigator.mediaDevices?.getUserMedia
const video = ref<HTMLVideoElement | null>(null)
const camaraActiva = ref(false)
const errorCamara = ref<string | null>(null)
let flujo: MediaStream | null = null
let temporizador: number | undefined
let ultimoLeido = ''
let ultimoMomento = 0

async function iniciarCamara(): Promise<void> {
  errorCamara.value = null
  try {
    flujo = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
    camaraActiva.value = true
    await new Promise((r) => requestAnimationFrame(r))
    if (!video.value) return
    video.value.srcObject = flujo
    await video.value.play()
    const Clase = (window as unknown as { BarcodeDetector: new (o: { formats: string[] }) => Detector }).BarcodeDetector
    const detector = new Clase({ formats: ['qr_code'] })
    temporizador = window.setInterval(async () => {
      if (!video.value || abordar.isPending.value) return
      const [hallado] = await detector.detect(video.value).catch(() => [])
      if (!hallado) return
      const ahora = Date.now()
      if (hallado.rawValue === ultimoLeido && ahora - ultimoMomento < 4000) return
      ultimoLeido = hallado.rawValue
      ultimoMomento = ahora
      abordar.mutate(hallado.rawValue)
    }, 350)
  } catch {
    errorCamara.value = 'No se pudo abrir la cámara. Revisa el permiso del navegador o usa el ingreso manual.'
    detenerCamara()
  }
}
function detenerCamara(): void {
  window.clearInterval(temporizador)
  flujo?.getTracks().forEach((t) => t.stop())
  flujo = null
  camaraActiva.value = false
}
onBeforeUnmount(detenerCamara)

// --- Equipaje del último pasajero ---
const equipaje = reactive({ tipo: 'bodega' as 'bodega' | 'mano', peso: '', piezas: '1' })
const registroEquipaje = ref<Schemas['EquipajeOut'] | null>(null)
const guardarEquipaje = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/admin/boletos/{numero_boleto}/equipajes', {
        params: { path: { numero_boleto: ultimo.value!.numero_boleto } },
        body: { tipo: equipaje.tipo, peso_kg: Number(equipaje.peso.replace(',', '.')), piezas: Number(equipaje.piezas) || 1 },
      }),
    ),
  onSuccess: (r) => {
    registroEquipaje.value = r
    equipaje.peso = ''
  },
  onError: (e) => registrar({ ok: false, titulo: 'Equipaje no registrado', detalle: e instanceof ApiError ? e.message : '' }),
})
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader title="Abordaje" subtitle="Valida los boletos con el QR del e-ticket o con el número de boleto." />

    <div class="grid items-start gap-6 lg:grid-cols-[1fr_380px]">
      <div class="flex flex-col gap-6">
        <SurfaceCard title="Escanear">
          <div class="flex flex-col gap-4">
            <div v-if="camaraActiva" class="relative overflow-hidden rounded-2xl bg-black">
              <video ref="video" class="aspect-video w-full object-cover" muted playsinline aria-label="Vista de la cámara" />
              <div class="pointer-events-none absolute inset-0 m-auto size-48 rounded-2xl border-4 border-white/80" aria-hidden="true" />
            </div>
            <p v-if="errorCamara" class="rounded-xl bg-peligro-50 px-4 py-3 text-sm text-peligro-800" role="alert">{{ errorCamara }}</p>
            <div class="flex flex-wrap gap-2">
              <BaseButton v-if="soportaCamara && !camaraActiva" variant="secondary" @click="iniciarCamara"><Camera class="size-4" aria-hidden="true" />Usar cámara</BaseButton>
              <BaseButton v-if="camaraActiva" variant="subtle" @click="detenerCamara"><CameraOff class="size-4" aria-hidden="true" />Detener cámara</BaseButton>
              <p v-if="!soportaCamara" class="text-sm text-muted">Este navegador no lee QR con la cámara; usa un lector USB o el ingreso manual.</p>
            </div>
            <form class="flex flex-col gap-3 sm:flex-row sm:items-end" @submit.prevent="validarManual">
              <TextInput v-model="codigo" label="Número de boleto o contenido del QR" placeholder="B26001004" mono class="flex-1" autocomplete="off" autofocus />
              <BaseButton type="submit" class="h-11" :loading="abordar.isPending.value"><ScanLine class="size-4" aria-hidden="true" />Validar</BaseButton>
            </form>
          </div>
        </SurfaceCard>

        <SurfaceCard v-if="ultimo" :title="`Equipaje · asiento ${ultimo.numero_asiento}`" :subtitle="ultimo.pasajero">
          <form class="flex flex-col gap-4" @submit.prevent="guardarEquipaje.mutate()">
            <SegmentedControl
              v-model="equipaje.tipo"
              label="Tipo"
              variant="switch"
              :options="[
                { value: 'bodega', label: 'Bodega (20 kg)' },
                { value: 'mano', label: 'De mano (5 kg)' },
              ]"
            />
            <div class="grid gap-3 sm:grid-cols-[1fr_120px_auto] sm:items-end">
              <TextInput v-model="equipaje.peso" label="Peso (kg)" inputmode="decimal" required />
              <TextInput v-model="equipaje.piezas" label="Piezas" type="number" min="1" max="10" />
              <BaseButton type="submit" variant="subtle" class="h-11" :disabled="!equipaje.peso" :loading="guardarEquipaje.isPending.value">
                <Luggage class="size-4" aria-hidden="true" />Registrar
              </BaseButton>
            </div>
            <p v-if="registroEquipaje" class="rounded-xl px-4 py-3 text-sm" :class="registroEquipaje.exceso_kg > 0 ? 'bg-aviso-50 text-aviso-800' : 'bg-exito-50 text-exito-800'" role="status">
              Etiqueta <span class="codigo">{{ registroEquipaje.etiqueta }}</span> ·
              <template v-if="registroEquipaje.exceso_kg > 0">exceso de {{ registroEquipaje.exceso_kg }} kg: cobrar {{ bsExacto(registroEquipaje.cargo_exceso_bs) }}</template>
              <template v-else>dentro de la franquicia</template>
            </p>
          </form>
        </SurfaceCard>
      </div>

      <SurfaceCard title="Últimas lecturas">
        <p v-if="!lecturas.length" class="text-sm text-muted">Aún no se validaron boletos.</p>
        <ul class="flex flex-col gap-2" aria-live="polite">
          <li
            v-for="l in lecturas"
            :key="l.id"
            class="flex gap-3 rounded-xl p-3"
            :class="l.ok ? 'bg-exito-50 text-exito-800 dark:bg-exito-600/15 dark:text-emerald-200' : 'bg-peligro-50 text-peligro-800 dark:bg-peligro-600/15 dark:text-red-200'"
          >
            <component :is="l.ok ? CircleCheck : CircleX" class="mt-0.5 size-5 shrink-0" aria-hidden="true" />
            <div class="min-w-0 flex-1">
              <p class="font-semibold">{{ l.titulo }}</p>
              <p class="text-[13px] opacity-90">{{ l.detalle }}</p>
            </div>
            <span class="text-xs opacity-70">{{ l.momento }}</span>
          </li>
        </ul>
      </SurfaceCard>
    </div>
  </div>
</template>
