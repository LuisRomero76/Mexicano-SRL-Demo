import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ApiError, api, loginConFormulario, unwrap, type Schemas } from '@/api/client'

export type Usuario = Schemas['UsuarioOut']
export type Rol = Schemas['RolUsuario']

/**
 * La sesión vive en una cookie httpOnly que JavaScript no puede leer (mitiga robo por XSS).
 * Aquí solo guardamos el perfil que devuelve /auth/me.
 */
export const useAuthStore = defineStore('auth', () => {
  const usuario = ref<Usuario | null>(null)
  const estado = ref<'desconocido' | 'anonimo' | 'autenticado'>('desconocido')
  let consulta: Promise<void> | null = null

  const rol = computed(() => usuario.value?.rol ?? null)

  async function cargarSesion(forzar = false): Promise<void> {
    if (!forzar && estado.value !== 'desconocido') return
    if (consulta) return consulta
    consulta = (async () => {
      try {
        usuario.value = await unwrap(api.GET('/api/v1/auth/me'))
        estado.value = 'autenticado'
      } catch (e) {
        usuario.value = null
        estado.value = 'anonimo'
        if (!(e instanceof ApiError) || e.status !== 401) console.warn('No se pudo verificar la sesión', e)
      } finally {
        consulta = null
      }
    })()
    return consulta
  }

  async function iniciarSesion(email: string, password: string): Promise<void> {
    await loginConFormulario(email.trim(), password)
    await cargarSesion(true)
  }

  async function cerrarSesion(): Promise<void> {
    try {
      await api.POST('/api/v1/auth/logout')
    } finally {
      olvidar()
    }
  }

  function olvidar(): void {
    usuario.value = null
    estado.value = 'anonimo'
  }

  /** `admin` siempre puede; si no se indican roles, basta con estar autenticado. */
  function puede(roles?: readonly Rol[]): boolean {
    if (!usuario.value) return false
    if (!roles || roles.length === 0 || usuario.value.rol === 'admin') return true
    return roles.includes(usuario.value.rol)
  }

  return { usuario, estado, rol, cargarSesion, iniciarSesion, cerrarSesion, olvidar, puede }
})
