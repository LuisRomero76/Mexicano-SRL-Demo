import { defineStore } from 'pinia'
import { ref } from 'vue'

export type TipoAviso = 'exito' | 'error' | 'info'

export interface Aviso {
  id: number
  tipo: TipoAviso
  titulo: string
  detalle?: string
}

export const useToastStore = defineStore('toast', () => {
  const avisos = ref<Aviso[]>([])
  let siguiente = 1

  function mostrar(tipo: TipoAviso, titulo: string, detalle?: string, duracion = 5000): void {
    const id = siguiente++
    avisos.value = [...avisos.value.slice(-3), { id, tipo, titulo, detalle }]
    window.setTimeout(() => cerrar(id), duracion)
  }

  function cerrar(id: number): void {
    avisos.value = avisos.value.filter((a) => a.id !== id)
  }

  return {
    avisos,
    cerrar,
    exito: (titulo: string, detalle?: string) => mostrar('exito', titulo, detalle),
    error: (titulo: string, detalle?: string) => mostrar('error', titulo, detalle, 7000),
    info: (titulo: string, detalle?: string) => mostrar('info', titulo, detalle),
  }
})
