import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { Schemas } from '@/api/client'
import SeatMap from '../SeatMap.vue'

const asiento = (numero: number, estado = 'libre') =>
  ({ numero, fila: numero, columna: 1, posicion: 'ventana', estado }) as unknown as Schemas['AsientoMapa']

function montar(seleccion: number[], maximo = 2) {
  const w = mount(SeatMap, {
    props: {
      asientos: [asiento(1), asiento(2), asiento(3, 'vendido'), asiento(4)],
      maximo,
      titulo: 'Planta alta',
      modelValue: seleccion,
      'onUpdate:modelValue': (v: number[]) => w.setProps({ modelValue: v }),
    },
  })
  return w
}
const boton = (w: ReturnType<typeof montar>, n: number) => w.findAll('button').find((b) => b.text() === String(n))!

describe('SeatMap', () => {
  it('elige y quita asientos libres', async () => {
    const w = montar([])
    await boton(w, 1).trigger('click')
    expect(w.props('modelValue')).toEqual([1])
    await boton(w, 1).trigger('click')
    expect(w.props('modelValue')).toEqual([])
  })

  it('no permite elegir asientos ocupados', async () => {
    const w = montar([])
    expect(boton(w, 3).attributes('disabled')).toBeDefined()
    await boton(w, 3).trigger('click')
    expect(w.props('modelValue')).toEqual([])
  })

  it('al llegar al máximo reemplaza el primero elegido', async () => {
    const w = montar([1, 2])
    await boton(w, 4).trigger('click')
    expect(w.props('modelValue')).toEqual([2, 4])
  })

  it('describe cada asiento para lectores de pantalla', () => {
    const w = montar([2])
    expect(boton(w, 2).attributes('aria-pressed')).toBe('true')
    expect(boton(w, 2).attributes('aria-label')).toContain('elegido')
  })
})
