import { defineStore } from 'pinia'
import { ref } from 'vue'

const CLAVE = 'em.panel.tema'

/** Modo oscuro del panel de operación (el portal público es siempre claro). */
export const useTemaStore = defineStore('tema', () => {
  const oscuro = ref(leer())

  function leer(): boolean {
    try {
      const guardado = localStorage.getItem(CLAVE)
      if (guardado) return guardado === 'oscuro'
      return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
    } catch {
      return false
    }
  }

  function alternar(): void {
    oscuro.value = !oscuro.value
    try {
      localStorage.setItem(CLAVE, oscuro.value ? 'oscuro' : 'claro')
    } catch {
      /* preferencia solo en memoria */
    }
  }

  return { oscuro, alternar }
})
