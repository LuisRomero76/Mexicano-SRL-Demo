<script setup lang="ts">
import { useMutation } from '@tanstack/vue-query'
import { Info, ShieldCheck } from '@lucide/vue'
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { z } from 'zod'
import { ApiError, api, unwrap } from '@/api/client'
import BookingSteps from '@/components/booking/BookingSteps.vue'
import TripSummary from '@/components/booking/TripSummary.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import CheckboxInput from '@/components/ui/CheckboxInput.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SelectInput from '@/components/ui/SelectInput.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { bs } from '@/lib/format'
import { celular, correoOpcional, documento, erroresDe, nombre } from '@/lib/validacion'
import { useCompraStore } from '@/stores/compra'
import { useToastStore } from '@/stores/toast'

const router = useRouter()
const compra = useCompraStore()
const avisos = useToastStore()
const estado = compra.estado

onMounted(() => {
  if (!estado.salida || estado.asientos.length === 0) {
    avisos.info('Primero elige tu viaje', 'Busca una salida y selecciona tus asientos.')
    void router.replace({ name: 'inicio' })
  }
})

const compradorEsPasajero = ref(true)
const conFactura = ref(!!estado.comprador.nit_facturacion)
const errores = ref<Record<string, string>>({})

const tiposDocumento = [
  { value: 'ci', label: 'Cédula de identidad' },
  { value: 'pasaporte', label: 'Pasaporte' },
  { value: 'carnet_extranjero', label: 'Carnet de extranjero' },
]

watch(
  () => [compradorEsPasajero.value, estado.pasajeros[0]] as const,
  ([mismo, primero]) => {
    if (!mismo || !primero) return
    estado.comprador.tipo_documento = primero.tipo_documento
    estado.comprador.numero_documento = primero.numero_documento
    estado.comprador.nombres = primero.nombres
    estado.comprador.apellidos = primero.apellidos
  },
  { deep: true, immediate: true },
)

const esquema = z.object({
  pasajeros: z.array(
    z
      .object({
        numero_documento: documento,
        nombres: nombre,
        apellidos: nombre,
        tipo_pasajero: z.enum(['adulto', 'embarazada']),
        semanas_gestacion: z.number().int().min(1).max(30, 'Se puede viajar hasta las 30 semanas').nullable(),
      })
      .refine((p) => p.tipo_pasajero !== 'embarazada' || p.semanas_gestacion !== null, {
        message: 'Indica las semanas de gestación',
        path: ['semanas_gestacion'],
      }),
  ),
  comprador: z.object({
    numero_documento: documento,
    nombres: nombre,
    apellidos: nombre,
    telefono: celular,
    email: correoOpcional,
  }),
})

const reservar = useMutation({
  mutationFn: () =>
    unwrap(
      api.POST('/api/v1/reservas', {
        body: {
          salida_id: estado.salida!.id,
          comprador: {
            tipo_documento: estado.comprador.tipo_documento,
            numero_documento: estado.comprador.numero_documento.trim(),
            nombres: estado.comprador.nombres.trim(),
            apellidos: estado.comprador.apellidos.trim(),
            telefono: estado.comprador.telefono.trim(),
            email: estado.comprador.email.trim() || null,
            nit_facturacion: conFactura.value ? estado.comprador.nit_facturacion.trim() || null : null,
            razon_social_facturacion: conFactura.value ? estado.comprador.razon_social_facturacion.trim() || null : null,
          },
          pasajeros: estado.pasajeros.map((p) => ({
            numero_asiento: p.numero_asiento,
            tipo_pasajero: p.tipo_pasajero,
            tipo_documento: p.tipo_documento,
            numero_documento: p.numero_documento.trim(),
            complemento: p.complemento.trim() || null,
            nombres: p.nombres.trim(),
            apellidos: p.apellidos.trim(),
            semanas_gestacion: p.tipo_pasajero === 'embarazada' ? p.semanas_gestacion : null,
            viaja_con_perro_guia: p.viaja_con_perro_guia,
          })),
        },
      }),
    ),
  onSuccess: (reserva) => {
    compra.fijarReserva(reserva.codigo_reserva, estado.comprador.numero_documento.trim())
    void router.push({ name: 'pago', params: { codigo: reserva.codigo_reserva } })
  },
  onError: (e) => {
    if (e instanceof ApiError && e.code === 'asiento_ocupado') {
      avisos.error('Uno de tus asientos se ocupó', e.message)
      void router.push({ name: 'asientos', params: { salidaId: estado.salida!.id }, query: { pasajeros: String(estado.asientos.length) } })
      return
    }
    if (e instanceof ApiError && e.code === 'datos_invalidos') errores.value = e.camposInvalidos
    avisos.error('No pudimos reservar', e instanceof ApiError ? e.message : undefined)
  },
})

function enviar(): void {
  errores.value = erroresDe(esquema.safeParse({ pasajeros: estado.pasajeros, comprador: estado.comprador }))
  if (Object.keys(errores.value).length) {
    avisos.error('Revisa los datos marcados')
    requestAnimationFrame(() => document.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus())
    return
  }
  reservar.mutate()
}

const err = (clave: string) => errores.value[clave] ?? null
const total = computed(() => compra.total)
</script>

<template>
  <div v-if="estado.salida">
    <BookingSteps :paso="3" />
    <form class="contenedor grid items-start gap-6 py-6 sm:py-8 lg:grid-cols-[1fr_360px]" novalidate @submit.prevent="enviar">
      <div class="flex min-w-0 flex-col gap-5">
        <div>
          <h1 class="text-2xl font-bold sm:text-[26px]">¿Quiénes viajan?</h1>
          <p class="mt-1 text-sm text-muted">Los datos deben coincidir con el documento que presentarás al abordar.</p>
        </div>

        <div class="flex gap-3 rounded-2xl border border-info-600/20 bg-info-50 p-4 text-sm text-info-800 dark:bg-info-600/10 dark:text-blue-200">
          <Info class="size-5 shrink-0" aria-hidden="true" />
          <p>
            Menores de 3 a 11 años (50 % de descuento), adultos mayores (20 %) y personas con discapacidad compran en
            <RouterLink :to="{ name: 'oficinas' }" class="font-semibold underline">boletería</RouterLink> presentando su documento.
          </p>
        </div>

        <fieldset
          v-for="(p, i) in estado.pasajeros"
          :key="p.numero_asiento"
          class="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-5"
        >
          <legend class="float-left mb-1 flex w-full items-center gap-3 text-base font-bold">
            <span class="flex size-9 items-center justify-center rounded-lg bg-carmin-600 text-sm text-white">{{ p.numero_asiento }}</span>
            Pasajero {{ i + 1 }}
            <span class="text-sm font-normal text-muted">· {{ estado.asientos[i]?.clase }}</span>
          </legend>
          <SegmentedControl
            v-model="p.tipo_pasajero"
            label="Tarifa"
            :options="[
              { value: 'adulto', label: 'Adulto', hint: 'Desde 12 años' },
              { value: 'embarazada', label: 'Embarazada', hint: 'Hasta 30 semanas' },
            ]"
          />
          <div class="grid gap-4 sm:grid-cols-[200px_1fr_110px]">
            <SelectInput v-model="p.tipo_documento" label="Documento" :options="tiposDocumento" />
            <TextInput
              v-model="p.numero_documento"
              label="Número"
              required
              autocomplete="off"
              inputmode="text"
              :error="err(`pasajeros.${i}.numero_documento`)"
            />
            <TextInput v-model="p.complemento" label="Compl." hint="Opcional" maxlength="5" autocomplete="off" />
          </div>
          <div class="grid gap-4 sm:grid-cols-2">
            <TextInput v-model="p.nombres" label="Nombres" required autocomplete="given-name" :error="err(`pasajeros.${i}.nombres`)" />
            <TextInput v-model="p.apellidos" label="Apellidos" required autocomplete="family-name" :error="err(`pasajeros.${i}.apellidos`)" />
          </div>
          <TextInput
            v-if="p.tipo_pasajero === 'embarazada'"
            v-model.number="p.semanas_gestacion"
            type="number"
            min="1"
            max="30"
            label="Semanas de gestación"
            class="sm:max-w-60"
            :error="err(`pasajeros.${i}.semanas_gestacion`)"
          />
          <CheckboxInput v-model="p.viaja_con_perro_guia" label="Viaja con perro guía" hint="No se permiten otras mascotas en cabina ni en bodega." />
        </fieldset>

        <fieldset class="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-5">
          <legend class="float-left mb-1 w-full text-base font-bold">Datos de contacto y factura</legend>
          <CheckboxInput v-model="compradorEsPasajero" label="Quien paga es el pasajero 1" />
          <div v-if="!compradorEsPasajero" class="grid gap-4 sm:grid-cols-3">
            <TextInput v-model="estado.comprador.numero_documento" label="Documento" required :error="err('comprador.numero_documento')" />
            <TextInput v-model="estado.comprador.nombres" label="Nombres" required :error="err('comprador.nombres')" />
            <TextInput v-model="estado.comprador.apellidos" label="Apellidos" required :error="err('comprador.apellidos')" />
          </div>
          <div class="grid gap-4 sm:grid-cols-2">
            <TextInput
              v-model="estado.comprador.telefono"
              label="Celular"
              type="tel"
              required
              autocomplete="tel"
              placeholder="71234567"
              hint="Te avisaremos si hay cambios en tu viaje."
              :error="err('comprador.telefono')"
            />
            <TextInput
              v-model="estado.comprador.email"
              label="Correo electrónico"
              type="email"
              autocomplete="email"
              hint="Para enviarte el e-ticket (recomendado)."
              :error="err('comprador.email')"
            />
          </div>
          <CheckboxInput v-model="conFactura" label="Quiero la factura con NIT o razón social" />
          <div v-if="conFactura" class="grid gap-4 sm:grid-cols-2">
            <TextInput v-model="estado.comprador.nit_facturacion" label="NIT o CI" maxlength="20" />
            <TextInput v-model="estado.comprador.razon_social_facturacion" label="Razón social" maxlength="150" />
          </div>
        </fieldset>
      </div>

      <aside class="overflow-hidden rounded-2xl border border-line bg-surface lg:sticky lg:top-24">
        <TripSummary :salida="estado.salida" />
        <div class="flex flex-col gap-3 p-5">
          <div v-for="a in estado.asientos" :key="a.numero" class="flex justify-between text-sm">
            <span>Asiento {{ a.numero }} · {{ a.clase }}</span><span class="tabular">{{ bs(a.precio_bs) }}</span>
          </div>
          <div class="flex items-baseline justify-between border-t border-line pt-3">
            <span class="font-semibold">Total</span>
            <span class="font-display text-[28px] font-bold tabular">{{ bs(total) }}</span>
          </div>
          <BaseButton type="submit" size="lg" block :loading="reservar.isPending.value">Reservar y continuar al pago</BaseButton>
          <p class="flex items-start gap-2 text-[13px] text-muted">
            <ShieldCheck class="mt-0.5 size-4 shrink-0" aria-hidden="true" />Al continuar reservamos tus asientos por 15 minutos.
          </p>
        </div>
      </aside>
    </form>
  </div>
</template>
