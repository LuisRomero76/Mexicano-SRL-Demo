<script setup lang="ts">
import { useMutation } from '@tanstack/vue-query'
import { CalendarCheck, CircleCheck, Clock3, MessageCircle } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { z } from 'zod'
import { ApiError, api, unwrap, type Schemas } from '@/api/client'
import { useCiudades, useFeriados } from '@/api/queries'
import BaseButton from '@/components/ui/BaseButton.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SelectInput from '@/components/ui/SelectInput.vue'
import TextArea from '@/components/ui/TextArea.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { diaSemanaISO, fechaLarga, hoyISO, sumarDias, telefono, whatsappUrl } from '@/lib/format'
import { celular, documento, erroresDe, nombre } from '@/lib/validacion'
import { useToastStore } from '@/stores/toast'

const avisos = useToastStore()
const { data: ciudades } = useCiudades()
const { data: feriados } = useFeriados()

const conServicio = computed(() => (ciudades.value ?? []).filter((c) => c.tiene_puerta_a_puerta))
const form = reactive({
  tipo: 'recojo' as 'recojo' | 'entrega',
  ciudad: 'Sucre',
  documento: '',
  nombres: '',
  apellidos: '',
  telefono: '',
  direccion: '',
  referencia: '',
  fecha: '',
  peso: '',
  descripcion: '',
  guia: '',
})
const errores = ref<Record<string, string>>({})
const resultado = ref<Schemas['SolicitudPuertaOut'] | null>(null)

const departamento = computed(() => conServicio.value.find((c) => c.nombre === form.ciudad)?.departamento)
/** Próximos 10 días hábiles de la ciudad (sin fines de semana ni feriados). */
const dias = computed(() => {
  const bloqueados = new Set(
    (feriados.value ?? []).filter((f) => !f.departamento || f.departamento === departamento.value).map((f) => f.fecha),
  )
  const horaActual = Number(new Date().toLocaleTimeString('en-GB', { timeZone: 'America/La_Paz', hour: '2-digit' }))
  const limite = form.tipo === 'entrega' ? 11 : 16
  const lista: { value: string; label: string }[] = []
  let d = horaActual >= limite ? sumarDias(hoyISO(), 1) : hoyISO()
  while (lista.length < 10) {
    if (diaSemanaISO(d) <= 5 && !bloqueados.has(d)) lista.push({ value: d, label: fechaLarga(d) })
    d = sumarDias(d, 1)
  }
  return lista
})
watch(dias, (l) => {
  if (!l.some((d) => d.value === form.fecha)) form.fecha = l[0]?.value ?? ''
}, { immediate: true })

const franja = computed(() => (form.tipo === 'entrega' ? 'de 08:00 a 12:00' : 'de 14:00 a 17:00'))

const esquema = z.object({
  documento,
  nombres: nombre,
  apellidos: nombre,
  telefono: celular,
  direccion: z.string().trim().min(5, 'Escribe la dirección completa'),
  peso: z.string().refine((v) => v === '' || Number(v.replace(',', '.')) >= 1, 'El servicio es desde 1 kg'),
  guia: z.string().refine((v) => v === '' || v.replace(/\D/g, '').length === 8, 'La guía tiene 8 dígitos'),
})

const solicitar = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/puerta-a-puerta', {
        body: {
          tipo: form.tipo,
          ciudad: form.ciudad,
          cliente: { numero_documento: form.documento.trim(), nombres: form.nombres.trim(), apellidos: form.apellidos.trim() },
          telefono: form.telefono.trim(),
          direccion: form.direccion.trim(),
          referencia: form.referencia.trim() || null,
          fecha_programada: form.fecha,
          peso_estimado_kg: form.peso ? Number(form.peso.replace(',', '.')) : null,
          descripcion: form.descripcion.trim() || null,
          numero_guia: form.guia.replace(/\D/g, '') || null,
        },
      }),
    ),
  onSuccess: (r) => {
    resultado.value = r
    window.scrollTo({ top: 0, behavior: 'smooth' })
  },
  onError: (e) => {
    if (e instanceof ApiError && e.code === 'datos_invalidos') errores.value = e.camposInvalidos
    avisos.error('No pudimos registrar la solicitud', e instanceof ApiError ? e.message : undefined)
  },
})

function enviar(): void {
  errores.value = erroresDe(esquema.safeParse(form))
  if (Object.keys(errores.value).length) return
  solicitar.mutate()
}
</script>

<template>
  <div class="contenedor grid items-start gap-8 py-10 lg:grid-cols-[1fr_380px]">
    <div class="flex flex-col gap-6">
      <div>
        <h1 class="text-[28px] font-bold sm:text-[34px]">Puerta a puerta</h1>
        <p class="mt-2 max-w-2xl text-muted">
          Recogemos tu encomienda o carga en la dirección que nos indiques y la entregamos en la puerta del destinatario. Desde
          1 kg, de lunes a viernes, en Sucre y Santa Cruz.
        </p>
      </div>

      <div v-if="resultado" class="flex flex-col gap-4 rounded-2xl border border-exito-600/30 bg-exito-50 p-6 text-exito-800" role="status">
        <div class="flex items-center gap-3">
          <CircleCheck class="size-7" aria-hidden="true" />
          <h2 class="font-sans text-xl font-bold">¡Solicitud registrada!</h2>
        </div>
        <p class="text-[15px]">{{ resultado.mensaje }}</p>
        <p class="text-sm">
          Código <span class="codigo">{{ resultado.codigo }}</span> · Te llamaremos al {{ telefono(resultado.contacto_telefono_e164) }} para confirmar.
        </p>
        <BaseButton variant="outline" class="self-start" @click="resultado = null">Hacer otra solicitud</BaseButton>
      </div>

      <form v-else class="flex flex-col gap-5 rounded-2xl border border-line bg-surface p-5 sm:p-6" novalidate @submit.prevent="enviar">
        <SegmentedControl
          v-model="form.tipo"
          label="¿Qué necesitas?"
          :options="[
            { value: 'recojo', label: 'Recojo', hint: 'Pasamos por tu envío · 14:00 a 17:00' },
            { value: 'entrega', label: 'Entrega', hint: 'Llevamos tu encomienda · 08:00 a 12:00' },
          ]"
        />
        <div class="grid gap-4 sm:grid-cols-2">
          <SelectInput v-model="form.ciudad" label="Ciudad" :options="conServicio.map((c) => ({ value: c.nombre, label: c.nombre }))" />
          <SelectInput v-model="form.fecha" label="Día" :options="dias" :hint="`Franja ${franja}`" />
        </div>
        <div class="grid gap-4 sm:grid-cols-3">
          <TextInput v-model="form.documento" label="CI" required :error="errores.documento" autocomplete="off" />
          <TextInput v-model="form.nombres" label="Nombres" required :error="errores.nombres" autocomplete="given-name" />
          <TextInput v-model="form.apellidos" label="Apellidos" required :error="errores.apellidos" autocomplete="family-name" />
        </div>
        <TextInput v-model="form.telefono" label="Celular de contacto" type="tel" required :error="errores.telefono" autocomplete="tel" placeholder="71234567" />
        <TextInput v-model="form.direccion" label="Dirección" required :error="errores.direccion" autocomplete="street-address" placeholder="Calle, número y zona" />
        <TextInput v-model="form.referencia" label="Referencia" hint="Opcional: color de la puerta, edificio, piso…" maxlength="250" />
        <div class="grid gap-4 sm:grid-cols-2">
          <TextInput v-model="form.peso" label="Peso aproximado (kg)" inputmode="decimal" :error="errores.peso" />
          <TextInput
            v-if="form.tipo === 'entrega'"
            v-model="form.guia"
            label="Número de guía"
            hint="La encomienda que debemos entregar"
            inputmode="numeric"
            mono
            :error="errores.guia"
          />
        </div>
        <TextArea v-model="form.descripcion" label="¿Qué enviarás?" :rows="2" maxlength="250" />
        <BaseButton type="submit" size="lg" :loading="solicitar.isPending.value" class="self-start">
          <CalendarCheck class="size-5" aria-hidden="true" />Solicitar {{ form.tipo }}
        </BaseButton>
      </form>
    </div>

    <aside class="flex flex-col gap-4">
      <div class="flex flex-col gap-3 rounded-2xl bg-noche-900 p-6 text-white">
        <h2 class="font-sans text-lg font-bold">Horarios</h2>
        <p class="flex items-center gap-2 text-sm text-noche-200"><Clock3 class="size-4" aria-hidden="true" />Entregas: 08:00 a 12:00, lunes a viernes</p>
        <p class="flex items-center gap-2 text-sm text-noche-200"><Clock3 class="size-4" aria-hidden="true" />Recojos: 14:00 a 17:00, lunes a viernes</p>
      </div>
      <div class="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-6">
        <h2 class="font-sans text-lg font-bold">También por WhatsApp</h2>
        <a
          v-for="c in conServicio"
          :key="c.id"
          :href="whatsappUrl(c.whatsapp_puerta_a_puerta_e164, 'Hola, quiero solicitar el servicio puerta a puerta.')"
          target="_blank"
          rel="noopener noreferrer"
          class="flex items-center justify-between rounded-xl border border-line px-4 py-3 hover:border-exito-600"
        >
          <span class="font-semibold">{{ c.nombre }}</span>
          <span class="flex items-center gap-2 text-sm text-exito-600"><MessageCircle class="size-4" aria-hidden="true" />{{ telefono(c.whatsapp_puerta_a_puerta_e164) }}</span>
        </a>
      </div>
    </aside>
  </div>
</template>
