<script setup lang="ts">
import { Eye, EyeOff, LockKeyhole } from '@lucide/vue'
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ApiError } from '@/api/client'
import LogoMark from '@/components/brand/LogoMark.vue'
import RouteMapArt from '@/components/brand/RouteMapArt.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const ver = ref(false)
const cargando = ref(false)
const error = ref<string | null>(null)

/** Solo se permite volver a rutas internas del panel (evita redirecciones abiertas). */
function destinoSeguro(): string {
  const s = route.query.siguiente
  return typeof s === 'string' && s.startsWith('/admin') && !s.startsWith('//') && !s.includes('\\') ? s : '/admin'
}

async function entrar(): Promise<void> {
  error.value = null
  if (!email.value.includes('@') || password.value.length < 1) {
    error.value = 'Ingresa tu correo y contraseña.'
    return
  }
  cargando.value = true
  try {
    await auth.iniciarSesion(email.value, password.value)
    password.value = ''
    await router.replace(destinoSeguro())
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'No pudimos iniciar sesión.'
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div class="grid min-h-dvh bg-canvas lg:grid-cols-[1.1fr_1fr]">
    <section class="relative hidden flex-col justify-between overflow-hidden bg-noche-900 p-12 text-white lg:flex">
      <LogoMark :size="40" subtitle="Panel de operación" />
      <div class="mx-auto w-full max-w-lg opacity-90"><RouteMapArt /></div>
      <div>
        <p class="font-display text-3xl leading-tight font-bold">Salidas, boletería y carga<br />en un solo lugar.</p>
        <p class="mt-3 text-noche-200">Acceso exclusivo para el personal de Transportes El Mexicano.</p>
      </div>
    </section>
    <section class="flex items-center justify-center px-4 py-12 sm:px-8">
      <form class="flex w-full max-w-sm flex-col gap-5" novalidate @submit.prevent="entrar">
        <div class="lg:hidden"><LogoMark :size="36" tone="dark" /></div>
        <div>
          <h1 class="text-[28px] font-bold">Iniciar sesión</h1>
          <p class="mt-1 text-muted">Usa tu correo institucional.</p>
        </div>
        <TextInput id="login-email" v-model="email" label="Correo" type="email" autocomplete="username" required autofocus />
        <TextInput id="login-password" v-model="password" label="Contraseña" :type="ver ? 'text' : 'password'" autocomplete="current-password" required>
          <template #sufijo>
            <button type="button" class="-mr-1 flex size-9 items-center justify-center rounded-md text-muted hover:text-fg" :aria-label="ver ? 'Ocultar contraseña' : 'Mostrar contraseña'" @click="ver = !ver">
              <EyeOff v-if="ver" class="size-[18px]" /><Eye v-else class="size-[18px]" />
            </button>
          </template>
        </TextInput>
        <p v-if="error" class="rounded-xl bg-peligro-50 px-4 py-3 text-sm font-medium text-peligro-800" role="alert">{{ error }}</p>
        <BaseButton type="submit" size="lg" block :loading="cargando"><LockKeyhole class="size-4" aria-hidden="true" />Entrar</BaseButton>
        <RouterLink :to="{ name: 'inicio' }" class="text-center text-sm font-semibold text-muted hover:text-fg">← Volver al sitio</RouterLink>
      </form>
    </section>
  </div>
</template>
