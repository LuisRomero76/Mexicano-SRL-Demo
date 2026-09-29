import { describe, expect, it } from 'vitest'
import { z } from 'zod'
import { celular, correoOpcional, documento, erroresDe, guia, nombre } from '../validacion'

describe('validacion', () => {
  it('acepta celulares bolivianos e internacionales', () => {
    for (const v of ['71234567', '+591 71234567', '591-6123-4567', '+5491123456789']) expect(celular.safeParse(v).success).toBe(true)
    for (const v of ['1234567', '81234567', 'abc']) expect(celular.safeParse(v).success).toBe(false)
  })

  it('valida documento, nombre y correo', () => {
    expect(documento.safeParse('6123456').success).toBe(true)
    expect(documento.safeParse('12').success).toBe(false)
    expect(documento.safeParse('12 34<').success).toBe(false)
    expect(nombre.safeParse("María José O'Brien").success).toBe(true)
    expect(nombre.safeParse('R2D2').success).toBe(false)
    expect(correoOpcional.safeParse('').success).toBe(true)
    expect(correoOpcional.safeParse('no-es-correo').success).toBe(false)
  })

  it('normaliza la guía', () => {
    expect(guia.parse('2600-0101')).toBe('26000101')
    expect(guia.safeParse('123').success).toBe(false)
  })

  it('devuelve el primer error por campo', () => {
    const r = z.object({ a: z.object({ b: documento }), c: nombre }).safeParse({ a: { b: '1' }, c: '' })
    const e = erroresDe(r)
    expect(Object.keys(e).sort()).toEqual(['a.b', 'c'])
    expect(e['a.b']).toBe('Ingresa al menos 4 caracteres')
  })
})
