import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { nextTick } from 'vue'
import type { Schemas } from '@/api/client'
import { useCompraStore } from '../compra'

const salida = (id: string) => ({ id }) as unknown as Schemas['SalidaResumen']
const asiento = (numero: number, precio_bs = 180) => ({ numero, tipo_asiento: 'suite', clase: 'Suite Cama', precio_bs })

describe('compra', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  it('ordena asientos, suma el total y crea un pasajero por asiento', () => {
    const c = useCompraStore()
    c.iniciar(salida('s1'))
    c.fijarAsientos([asiento(12, 200), asiento(3)])
    expect(c.estado.asientos.map((a) => a.numero)).toEqual([3, 12])
    expect(c.total).toBe(380)
    expect(c.estado.pasajeros.map((p) => p.numero_asiento)).toEqual([3, 12])
  })

  it('conserva los datos del pasajero si el asiento sigue elegido', () => {
    const c = useCompraStore()
    c.iniciar(salida('s1'))
    c.fijarAsientos([asiento(3), asiento(4)])
    c.estado.pasajeros[0].nombres = 'Ana'
    c.fijarAsientos([asiento(3), asiento(9)])
    expect(c.estado.pasajeros[0].nombres).toBe('Ana')
    expect(c.estado.pasajeros[1].nombres).toBe('')
  })

  it('cambiar de salida limpia asientos pero conserva al comprador', () => {
    const c = useCompraStore()
    c.iniciar(salida('s1'))
    c.estado.comprador.nombres = 'Luis'
    c.fijarAsientos([asiento(3)])
    c.iniciar(salida('s2'))
    expect(c.estado.asientos).toEqual([])
    expect(c.estado.comprador.nombres).toBe('Luis')
  })

  it('persiste en sessionStorage y se recupera', async () => {
    const c = useCompraStore()
    c.iniciar(salida('s1'))
    c.fijarReserva('MX7K2P', '6123456')
    await nextTick()
    setActivePinia(createPinia())
    expect(useCompraStore().estado.reserva).toEqual({ codigo: 'MX7K2P', documento: '6123456' })
  })
})
