<script setup lang="ts">
import {
  BarChart3,
  BookOpen,
  Bus,
  ClipboardList,
  House,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Package,
  PackagePlus,
  RotateCcw,
  ScanLine,
  Search,
  ShieldCheck,
  Sun,
  Ticket,
  UserRound,
  Users,
  X,
} from '@lucide/vue'
import { onKeyStroke } from '@vueuse/core'
import { DialogContent, DialogOverlay, DialogPortal, DialogRoot, DialogTitle } from 'reka-ui'
import { computed, onBeforeUnmount, ref, watch, watchEffect, type Component } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import LogoMark from '@/components/brand/LogoMark.vue'
import { iniciales } from '@/lib/format'
import { ROL } from '@/lib/labels'
import { ACCESO } from '@/lib/roles'
import { useAuthStore, type Rol } from '@/stores/auth'
import { useTemaStore } from '@/stores/tema'

const auth = useAuthStore()
const tema = useTemaStore()
const route = useRoute()
const router = useRouter()
const menuMovil = ref(false)
watch(() => route.fullPath, () => (menuMovil.value = false))

// El modo oscuro también debe cubrir los diálogos (se montan en <body>).
watchEffect(() => document.documentElement.classList.toggle('dark', tema.oscuro))
onBeforeUnmount(() => document.documentElement.classList.remove('dark'))

interface Item {
  to: string
  label: string
  icono: Component
  roles: Rol[]
}
const secciones: { titulo: string; items: Item[] }[] = [
  {
    titulo: 'Operación',
    items: [
      { to: '/admin', label: 'Tablero', icono: LayoutDashboard, roles: ACCESO.tablero },
      { to: '/admin/salidas', label: 'Salidas', icono: Bus, roles: ACCESO.salidas },
      { to: '/admin/boleteria', label: 'Boletería', icono: Ticket, roles: ACCESO.boleteria },
      { to: '/admin/abordaje', label: 'Abordaje', icono: ScanLine, roles: ACCESO.abordaje },
      { to: '/admin/ventas', label: 'Ventas', icono: ClipboardList, roles: ACCESO.ventas },
      { to: '/admin/reembolsos', label: 'Reembolsos', icono: RotateCcw, roles: ACCESO.reembolsos },
    ],
  },
  {
    titulo: 'Carga',
    items: [
      { to: '/admin/encomiendas', label: 'Encomiendas', icono: Package, roles: ACCESO.encomiendas },
      { to: '/admin/encomiendas/nueva', label: 'Nueva encomienda', icono: PackagePlus, roles: ACCESO.encomiendasRegistrar },
      { to: '/admin/puerta-a-puerta', label: 'Puerta a puerta', icono: House, roles: ACCESO.puerta },
    ],
  },
  {
    titulo: 'Administración',
    items: [
      { to: '/admin/catalogos', label: 'Catálogos', icono: BookOpen, roles: ACCESO.catalogos },
      { to: '/admin/personal', label: 'Personal', icono: Users, roles: ACCESO.personal },
      { to: '/admin/clientes', label: 'Clientes', icono: UserRound, roles: ACCESO.clientes },
      { to: '/admin/reportes', label: 'Reportes', icono: BarChart3, roles: ACCESO.reportes },
      { to: '/admin/auditoria', label: 'Auditoría', icono: ShieldCheck, roles: ACCESO.auditoria },
    ],
  },
]
const visibles = computed(() =>
  secciones.map((s) => ({ ...s, items: s.items.filter((i) => auth.puede(i.roles)) })).filter((s) => s.items.length),
)
function activo(to: string): boolean {
  if (to === '/admin') return route.path === '/admin'
  if (to === '/admin/encomiendas') return route.path.startsWith('/admin/encomiendas') && route.path !== '/admin/encomiendas/nueva'
  return route.path.startsWith(to)
}

async function salir(): Promise<void> {
  await auth.cerrarSesion()
  void router.push({ name: 'admin-login' })
}

// Buscador global: guía (8 dígitos), reserva (6 caracteres) o cliente (documento/nombre).
const busqueda = ref('')
const campo = ref<HTMLInputElement | null>(null)
onKeyStroke('/', (e) => {
  const t = e.target as HTMLElement | null
  if (t && ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName)) return
  e.preventDefault()
  campo.value?.focus()
})
function buscar(): void {
  const q = busqueda.value.trim()
  if (!q) return
  const digitos = q.replace(/\D/g, '')
  if (/^\d{8}$/.test(q) && auth.puede(ACCESO.encomiendas)) void router.push({ name: 'admin-encomienda', params: { guia: q } })
  else if (/^[A-Za-z0-9]{6}$/.test(q) && /[A-Za-z]/.test(q) && auth.puede(ACCESO.ventas))
    void router.push({ name: 'admin-ventas', query: { codigo: q.toUpperCase() } })
  else if (auth.puede(ACCESO.clientes)) void router.push({ name: 'admin-clientes', query: { q } })
  else if (digitos) void router.push({ name: 'admin-encomiendas', query: { q } })
  busqueda.value = ''
}
const titulo = computed(() => route.meta.title ?? 'Panel')
</script>

<template>
  <div class="min-h-dvh bg-canvas text-fg">
    <aside class="no-print fixed inset-y-0 left-0 z-30 hidden w-[248px] flex-col bg-noche-900 text-noche-200 lg:flex dark:bg-noche-950">
      <div class="px-5 pt-5 pb-4"><LogoMark :size="32" subtitle="Panel de operación" /></div>
      <nav aria-label="Panel" class="flex-1 overflow-y-auto px-3 pb-4">
        <div v-for="s in visibles" :key="s.titulo" class="mt-3">
          <p class="px-3 pb-1.5 text-[11px] font-bold tracking-[0.1em] text-noche-400 uppercase">{{ s.titulo }}</p>
          <RouterLink
            v-for="i in s.items"
            :key="i.to"
            :to="i.to"
            class="flex h-10 items-center gap-3 rounded-lg px-3 text-sm transition-colors"
            :class="activo(i.to) ? 'bg-noche-700 font-semibold text-white' : 'hover:bg-white/5 hover:text-white'"
            :aria-current="activo(i.to) ? 'page' : undefined"
          >
            <component :is="i.icono" class="size-[18px]" aria-hidden="true" />{{ i.label }}
          </RouterLink>
        </div>
      </nav>
      <div class="flex items-center gap-3 border-t border-noche-800 px-4 py-4">
        <span class="flex size-9 shrink-0 items-center justify-center rounded-full bg-noche-700 text-[13px] font-bold text-white">
          {{ iniciales(`${auth.usuario?.nombres ?? ''} ${auth.usuario?.apellidos ?? ''}`) }}
        </span>
        <div class="min-w-0 flex-1 text-[13px]">
          <p class="truncate font-semibold text-white">{{ auth.usuario?.nombres }} {{ auth.usuario?.apellidos?.split(' ')[0] }}</p>
          <p class="truncate">{{ ROL[auth.usuario?.rol ?? ''] }}</p>
        </div>
        <button class="flex size-9 items-center justify-center rounded-lg hover:bg-white/10 hover:text-white" aria-label="Cerrar sesión" title="Cerrar sesión" @click="salir">
          <LogOut class="size-[18px]" />
        </button>
      </div>
    </aside>

    <div class="flex min-h-dvh flex-col lg:pl-[248px]">
      <header class="no-print sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-line bg-surface/95 px-4 backdrop-blur sm:px-6">
        <button class="flex size-10 items-center justify-center rounded-lg hover:bg-surface-2 lg:hidden" aria-label="Abrir menú" @click="menuMovil = true">
          <Menu class="size-5" />
        </button>
        <span class="truncate font-display text-base font-semibold lg:hidden">{{ titulo }}</span>
        <form class="ml-auto hidden max-w-md flex-1 md:block lg:ml-0" role="search" @submit.prevent="buscar">
          <label for="buscador-global" class="sr-only">Buscar guía, reserva o cliente</label>
          <div class="flex h-10 items-center gap-2 rounded-control border-[1.5px] border-line-strong px-3 focus-within:border-noche-700">
            <Search class="size-4 text-muted" aria-hidden="true" />
            <input
              id="buscador-global"
              ref="campo"
              v-model="busqueda"
              class="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted"
              placeholder="Guía, código de reserva o CI"
              autocomplete="off"
            />
            <kbd class="rounded border border-line-strong px-1.5 font-mono text-[11px] text-muted">/</kbd>
          </div>
        </form>
        <div class="ml-auto flex items-center gap-2">
          <RouterLink :to="{ name: 'inicio' }" class="hidden text-sm font-semibold text-muted hover:text-fg xl:inline">Ver portal</RouterLink>
          <button
            class="flex size-10 items-center justify-center rounded-control border-[1.5px] border-line-strong hover:bg-surface-2"
            :aria-label="tema.oscuro ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
            :aria-pressed="tema.oscuro"
            @click="tema.alternar()"
          >
            <Sun v-if="tema.oscuro" class="size-[18px]" /><Moon v-else class="size-[18px]" />
          </button>
        </div>
      </header>
      <main id="contenido" class="flex-1 px-4 py-6 sm:px-6 lg:px-8" tabindex="-1">
        <RouterView />
      </main>
    </div>

    <DialogRoot v-model:open="menuMovil">
      <DialogPortal>
        <DialogOverlay class="fixed inset-0 z-50 bg-noche-950/60 lg:hidden" />
        <DialogContent class="fixed inset-y-0 left-0 z-50 flex w-[82vw] max-w-xs flex-col bg-noche-900 text-noche-200 data-[state=open]:animate-aparecer lg:hidden">
          <div class="flex items-center justify-between px-5 pt-5 pb-3">
            <DialogTitle class="sr-only">Menú del panel</DialogTitle>
            <LogoMark :size="30" />
            <button class="flex size-10 items-center justify-center rounded-lg hover:bg-white/10" aria-label="Cerrar menú" @click="menuMovil = false"><X class="size-5" /></button>
          </div>
          <form class="px-4 pb-2" role="search" @submit.prevent="buscar">
            <label for="buscador-movil" class="sr-only">Buscar</label>
            <input id="buscador-movil" v-model="busqueda" class="h-11 w-full rounded-lg bg-white/10 px-3 text-sm text-white outline-none placeholder:text-noche-300" placeholder="Guía, reserva o CI" />
          </form>
          <nav aria-label="Panel móvil" class="flex-1 overflow-y-auto px-3 pb-4">
            <div v-for="s in visibles" :key="s.titulo" class="mt-3">
              <p class="px-3 pb-1.5 text-[11px] font-bold tracking-[0.1em] text-noche-400 uppercase">{{ s.titulo }}</p>
              <RouterLink
                v-for="i in s.items"
                :key="i.to"
                :to="i.to"
                class="flex h-11 items-center gap-3 rounded-lg px-3 text-[15px]"
                :class="activo(i.to) ? 'bg-noche-700 font-semibold text-white' : 'hover:bg-white/5'"
              >
                <component :is="i.icono" class="size-5" aria-hidden="true" />{{ i.label }}
              </RouterLink>
            </div>
          </nav>
          <button class="m-4 flex h-11 items-center justify-center gap-2 rounded-lg border border-noche-700 font-semibold text-white" @click="salir">
            <LogOut class="size-4" aria-hidden="true" />Cerrar sesión
          </button>
        </DialogContent>
      </DialogPortal>
    </DialogRoot>
  </div>
</template>
