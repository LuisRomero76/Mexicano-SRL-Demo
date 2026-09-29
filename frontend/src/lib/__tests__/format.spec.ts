import { describe, expect, it } from 'vitest'
import { bs, bsExacto, diaSemanaISO, duracion, esDiaSiguiente, fechaHora, hora, iniciales, sumarDias, telefono, whatsappUrl } from '../format'

describe('format', () => {
  it('formatea bolivianos', () => {
    expect(bs(180)).toBe('Bs 180')
    expect(bs(1234.5)).toBe('Bs 1.234,50')
    expect(bs('99.9', true)).toBe('Bs 100')
    expect(bsExacto(25)).toBe('Bs 25,00')
    expect(bs(null)).toBe('—')
  })

  it('usa la hora de Bolivia (UTC-4)', () => {
    expect(hora('2026-09-28T22:30:00Z')).toBe('18:30')
    expect(fechaHora('2026-09-29T03:15:00Z')).toBe('28/09/2026 23:15')
  })

  it('opera con fechas ISO sin desfase', () => {
    expect(sumarDias('2026-12-31', 1)).toBe('2027-01-01')
    expect(sumarDias('2026-03-01', -1)).toBe('2026-02-28')
    expect(diaSemanaISO('2026-09-28')).toBe(1)
    expect(diaSemanaISO('2026-10-04')).toBe(7)
  })

  it('detecta llegada al día siguiente', () => {
    expect(esDiaSiguiente('2026-09-28T22:30:00Z', '2026-09-29T12:30:00Z')).toBe(true)
    expect(esDiaSiguiente('2026-09-28T12:00:00Z', '2026-09-28T20:00:00Z')).toBe(false)
  })

  it('formatea duración, teléfonos e iniciales', () => {
    expect(duracion(840)).toBe('14 h')
    expect(duracion(90)).toBe('1 h 30 min')
    expect(telefono('59171420823')).toBe('+591 71420823')
    expect(whatsappUrl('+59171420823', 'Hola mundo')).toBe('https://wa.me/59171420823?text=Hola%20mundo')
    expect(whatsappUrl(null)).toBeUndefined()
    expect(iniciales('carlos  mendoza rojas')).toBe('CM')
  })
})
