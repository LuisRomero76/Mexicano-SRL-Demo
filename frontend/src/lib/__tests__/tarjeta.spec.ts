import { describe, expect, it } from 'vitest'
import { formatearNumero, luhnValido, marca, vencimientoValido } from '../tarjeta'

describe('tarjeta', () => {
  it('valida con Luhn', () => {
    expect(luhnValido('4111 1111 1111 1111')).toBe(true)
    expect(luhnValido('4111 1111 1111 1112')).toBe(false)
    expect(luhnValido('4111')).toBe(false)
  })

  it('reconoce la marca', () => {
    expect(marca('4111')).toBe('Visa')
    expect(marca('5500 0000')).toBe('Mastercard')
    expect(marca('2221 0000')).toBe('Mastercard')
    expect(marca('3782')).toBeNull()
  })

  it('agrupa el número de 4 en 4', () => {
    expect(formatearNumero('4111111111111111')).toBe('4111 1111 1111 1111')
    expect(formatearNumero('4111-11ab11')).toBe('4111 1111')
  })

  it('rechaza tarjetas vencidas o meses inválidos', () => {
    const hoy = new Date(2026, 8, 29)
    expect(vencimientoValido('09/26', hoy)).toBe(true)
    expect(vencimientoValido('08/26', hoy)).toBe(false)
    expect(vencimientoValido('13/27', hoy)).toBe(false)
    expect(vencimientoValido('1227', hoy)).toBe(true)
    expect(vencimientoValido('abc', hoy)).toBe(false)
  })
})
