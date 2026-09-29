<script setup lang="ts">
import { BusFront, CircleHelp, Menu, MessageCircle, Package, Ticket, X } from '@lucide/vue'
import { DialogContent, DialogOverlay, DialogPortal, DialogRoot, DialogTitle } from 'reka-ui'
import { ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useEmpresa } from '@/api/queries'
import LogoMark from '@/components/brand/LogoMark.vue'
import { telefono, whatsappUrl } from '@/lib/format'

const route = useRoute()
const { data: empresa } = useEmpresa()
const menuAbierto = ref(false)
watch(() => route.fullPath, () => (menuAbierto.value = false))

const enlaces = [
  { to: { name: 'inicio' }, label: 'Pasajes', nombre: 'inicio' },
  { to: { name: 'rutas' }, label: 'Rutas', nombre: 'rutas' },
  { to: { name: 'buses' }, label: 'Nuestros buses', nombre: 'buses' },
  { to: { name: 'carga' }, label: 'Carga', nombre: 'carga' },
  { to: { name: 'oficinas' }, label: 'Oficinas', nombre: 'oficinas' },
  { to: { name: 'ayuda' }, label: 'Ayuda', nombre: 'ayuda' },
]
const inferior = [
  { to: { name: 'inicio' }, label: 'Pasajes', icono: BusFront, nombres: ['inicio', 'resultados', 'asientos', 'pasajeros', 'pago'] },
  { to: { name: 'rastreo' }, label: 'Envíos', icono: Package, nombres: ['rastreo', 'carga', 'puerta-a-puerta'] },
  { to: { name: 'mi-reserva' }, label: 'Mi reserva', icono: Ticket, nombres: ['mi-reserva', 'confirmacion'] },
  { to: { name: 'ayuda' }, label: 'Ayuda', icono: CircleHelp, nombres: ['ayuda', 'oficinas'] },
]
const activo = (nombres: string[]) => nombres.includes(String(route.name))
</script>

<template>
  <div class="flex min-h-dvh flex-col bg-canvas">
    <header class="no-print sticky top-0 z-40 bg-noche-900/95 backdrop-blur supports-[backdrop-filter]:bg-noche-900/90">
      <div class="contenedor flex h-16 items-center justify-between gap-4 md:h-[72px]">
        <RouterLink :to="{ name: 'inicio' }" aria-label="El Mexicano, ir al inicio"><LogoMark :size="34" /></RouterLink>
        <nav aria-label="Principal" class="hidden items-center gap-1 lg:flex">
          <RouterLink
            v-for="e in enlaces"
            :key="e.nombre"
            :to="e.to"
            class="rounded-lg px-3 py-2 text-[15px] font-medium text-noche-200 transition-colors hover:bg-white/5 hover:text-white"
            exact-active-class="!font-semibold !text-white"
          >
            {{ e.label }}
          </RouterLink>
        </nav>
        <div class="flex items-center gap-2">
          <RouterLink
            :to="{ name: 'mi-reserva' }"
            class="hidden h-10 items-center rounded-control border border-noche-600 px-4 text-sm font-semibold text-white hover:bg-white/5 sm:inline-flex"
          >
            Mi reserva
          </RouterLink>
          <a
            v-if="empresa?.whatsapp_central_e164"
            :href="whatsappUrl(empresa.whatsapp_central_e164, 'Hola, quiero hacer una consulta.')"
            target="_blank"
            rel="noopener noreferrer"
            class="hidden h-10 items-center gap-2 rounded-control bg-white px-4 text-sm font-semibold text-noche-900 hover:bg-noche-100 md:inline-flex"
          >
            <MessageCircle class="size-4" aria-hidden="true" />{{ telefono(empresa.whatsapp_central_e164).replace('+591 ', '') }}
          </a>
          <button
            class="flex size-11 items-center justify-center rounded-lg text-white hover:bg-white/10 lg:hidden"
            aria-label="Abrir menú"
            @click="menuAbierto = true"
          >
            <Menu class="size-6" />
          </button>
        </div>
      </div>
    </header>

    <DialogRoot v-model:open="menuAbierto">
      <DialogPortal>
        <DialogOverlay class="fixed inset-0 z-50 bg-noche-950/60 lg:hidden" />
        <DialogContent class="fixed inset-y-0 right-0 z-50 flex w-[86vw] max-w-sm flex-col bg-noche-900 p-5 text-white data-[state=open]:animate-aparecer lg:hidden">
          <div class="flex items-center justify-between">
            <DialogTitle class="sr-only">Menú</DialogTitle>
            <LogoMark :size="30" />
            <button class="flex size-11 items-center justify-center rounded-lg hover:bg-white/10" aria-label="Cerrar menú" @click="menuAbierto = false">
              <X class="size-6" />
            </button>
          </div>
          <nav aria-label="Menú móvil" class="mt-8 flex flex-col gap-1">
            <RouterLink
              v-for="e in enlaces"
              :key="e.nombre"
              :to="e.to"
              class="rounded-xl px-4 py-3.5 text-lg font-semibold text-noche-100 hover:bg-white/5"
            >
              {{ e.label }}
            </RouterLink>
            <RouterLink :to="{ name: 'rastreo' }" class="rounded-xl px-4 py-3.5 text-lg font-semibold text-noche-100 hover:bg-white/5">Rastrear envío</RouterLink>
            <RouterLink :to="{ name: 'mi-reserva' }" class="rounded-xl px-4 py-3.5 text-lg font-semibold text-noche-100 hover:bg-white/5">Mi reserva</RouterLink>
          </nav>
          <a
            v-if="empresa?.whatsapp_central_e164"
            :href="whatsappUrl(empresa.whatsapp_central_e164, 'Hola, quiero hacer una consulta.')"
            target="_blank"
            rel="noopener noreferrer"
            class="mt-auto flex h-13 items-center justify-center gap-2 rounded-xl bg-exito-600 font-bold"
          >
            <MessageCircle class="size-5" aria-hidden="true" />Escríbenos por WhatsApp
          </a>
        </DialogContent>
      </DialogPortal>
    </DialogRoot>

    <main id="contenido" class="flex-1 pb-20 lg:pb-0" tabindex="-1">
      <RouterView v-slot="{ Component }">
        <Transition name="pagina" mode="out-in">
          <component :is="Component" :key="route.path" />
        </Transition>
      </RouterView>
    </main>

    <footer class="no-print bg-noche-900 text-noche-200">
      <div class="contenedor grid gap-10 py-12 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div class="flex flex-col gap-4">
          <LogoMark :size="34" subtitle="Pasajes · Carga · Encomiendas" />
          <p class="max-w-sm text-sm leading-relaxed">
            Empresa regulada y fiscalizada por la Autoridad de Telecomunicaciones y Transportes (ATT) del Estado
            Plurinacional de Bolivia.
          </p>
        </div>
        <div class="flex flex-col gap-2 text-sm">
          <p class="font-semibold text-white">Viaja</p>
          <RouterLink :to="{ name: 'inicio' }" class="hover:text-white">Comprar pasajes</RouterLink>
          <RouterLink :to="{ name: 'rutas' }" class="hover:text-white">Rutas e itinerarios</RouterLink>
          <RouterLink :to="{ name: 'buses' }" class="hover:text-white">Nuestros buses</RouterLink>
          <RouterLink :to="{ name: 'mi-reserva' }" class="hover:text-white">Mi reserva</RouterLink>
        </div>
        <div class="flex flex-col gap-2 text-sm">
          <p class="font-semibold text-white">Envía</p>
          <RouterLink :to="{ name: 'carga' }" class="hover:text-white">Carga y encomiendas</RouterLink>
          <RouterLink :to="{ name: 'rastreo' }" class="hover:text-white">Rastrear envío</RouterLink>
          <RouterLink :to="{ name: 'puerta-a-puerta' }" class="hover:text-white">Puerta a puerta</RouterLink>
          <RouterLink :to="{ name: 'oficinas' }" class="hover:text-white">Boleterías y bodegas</RouterLink>
        </div>
        <div class="flex flex-col gap-2 text-sm">
          <p class="font-semibold text-white">Contacto</p>
          <span>WhatsApp {{ telefono(empresa?.whatsapp_central_e164) }}</span>
          <span>Atención al cliente {{ telefono(empresa?.telefono_atencion_cliente_e164) }}</span>
          <RouterLink :to="{ name: 'ayuda' }" class="hover:text-white">Centro de ayuda</RouterLink>
          <RouterLink :to="{ name: 'terminos' }" class="hover:text-white">Términos y condiciones</RouterLink>
        </div>
      </div>
      <div class="border-t border-noche-800">
        <div class="contenedor flex flex-col gap-2 py-5 text-xs text-noche-300 sm:flex-row sm:justify-between">
          <span>© {{ new Date().getFullYear() }} Transportes El Mexicano S.R.L.</span>
          <RouterLink :to="{ name: 'admin-login' }" class="hover:text-white">Acceso del personal</RouterLink>
        </div>
      </div>
    </footer>

    <nav aria-label="Accesos rápidos" class="no-print fixed inset-x-0 bottom-0 z-30 flex h-16 border-t border-line bg-surface/95 backdrop-blur pb-[env(safe-area-inset-bottom)] lg:hidden">
      <RouterLink
        v-for="i in inferior"
        :key="i.label"
        :to="i.to"
        class="flex flex-1 flex-col items-center justify-center gap-1 text-xs font-semibold"
        :class="activo(i.nombres) ? 'text-carmin-600' : 'text-muted'"
        :aria-current="activo(i.nombres) ? 'page' : undefined"
      >
        <component :is="i.icono" class="size-[22px]" aria-hidden="true" />{{ i.label }}
      </RouterLink>
    </nav>
  </div>
</template>

<style>
.pagina-enter-active,
.pagina-leave-active {
  transition: opacity 0.15s ease;
}
.pagina-enter-from,
.pagina-leave-to {
  opacity: 0;
}
</style>
