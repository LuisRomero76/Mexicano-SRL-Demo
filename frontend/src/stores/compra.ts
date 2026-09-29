import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import type { Schemas } from '@/api/client'

export interface AsientoElegido {
  numero: number
  tipo_asiento: string
  clase: string
  precio_bs: number
}

export interface PasajeroForm {
  numero_asiento: number
  tipo_pasajero: 'adulto' | 'embarazada'
  tipo_documento: Schemas['TipoDocumento']
  numero_documento: string
  complemento: string
  nombres: string
  apellidos: string
  semanas_gestacion: number | null
  viaja_con_perro_guia: boolean
}

export interface CompradorForm {
  tipo_documento: Schemas['TipoDocumento']
  numero_documento: string
  nombres: string
  apellidos: string
  telefono: string
  email: string
  nit_facturacion: string
  razon_social_facturacion: string
}

interface Estado {
  salida: Schemas['SalidaResumen'] | null
  asientos: AsientoElegido[]
  pasajeros: PasajeroForm[]
  comprador: CompradorForm
  reserva: { codigo: string; documento: string } | null
}

const CLAVE = 'em.compra.v1'

function vacio(): Estado {
  return {
    salida: null,
    asientos: [],
    pasajeros: [],
    comprador: {
      tipo_documento: 'ci',
      numero_documento: '',
      nombres: '',
      apellidos: '',
      telefono: '',
      email: '',
      nit_facturacion: '',
      razon_social_facturacion: '',
    },
    reserva: null,
  }
}

function leer(): Estado {
  try {
    const crudo = sessionStorage.getItem(CLAVE)
    return crudo ? { ...vacio(), ...(JSON.parse(crudo) as Partial<Estado>) } : vacio()
  } catch {
    return vacio()
  }
}

/**
 * Compra en curso. Se guarda en sessionStorage (se borra al cerrar la pestaña) para que
 * recargar la página no haga perder los datos. No se guardan datos de tarjeta.
 */
export const useCompraStore = defineStore('compra', () => {
  const estado = ref<Estado>(leer())

  watch(
    estado,
    (valor) => {
      try {
        sessionStorage.setItem(CLAVE, JSON.stringify(valor))
      } catch {
        /* almacenamiento no disponible: la compra sigue en memoria */
      }
    },
    { deep: true },
  )

  const total = computed(() => estado.value.asientos.reduce((t, a) => t + a.precio_bs, 0))

  function iniciar(salida: Schemas['SalidaResumen']): void {
    if (estado.value.salida?.id !== salida.id) {
      estado.value = { ...vacio(), comprador: estado.value.comprador, salida }
    } else {
      estado.value.salida = salida
    }
  }

  function fijarAsientos(asientos: AsientoElegido[]): void {
    estado.value.asientos = [...asientos].sort((a, b) => a.numero - b.numero)
    const previos = new Map(estado.value.pasajeros.map((p) => [p.numero_asiento, p]))
    estado.value.pasajeros = estado.value.asientos.map(
      (a) =>
        previos.get(a.numero) ?? {
          numero_asiento: a.numero,
          tipo_pasajero: 'adulto',
          tipo_documento: 'ci',
          numero_documento: '',
          complemento: '',
          nombres: '',
          apellidos: '',
          semanas_gestacion: null,
          viaja_con_perro_guia: false,
        },
    )
  }

  function fijarReserva(codigo: string, documento: string): void {
    estado.value.reserva = { codigo, documento }
  }

  function reiniciar(): void {
    const comprador = estado.value.comprador
    estado.value = { ...vacio(), comprador }
  }

  return { estado, total, iniciar, fijarAsientos, fijarReserva, reiniciar }
})
