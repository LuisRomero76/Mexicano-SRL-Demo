/** Validación local de tarjetas (el backend solo recibe el número para simular; nunca se guarda completo). */

export function soloDigitos(v: string): string {
  return v.replace(/\D/g, '')
}

export function luhnValido(numero: string): boolean {
  const d = soloDigitos(numero)
  if (d.length < 13 || d.length > 19) return false
  let suma = 0
  let doble = false
  for (let i = d.length - 1; i >= 0; i--) {
    let n = Number(d[i])
    if (doble) {
      n *= 2
      if (n > 9) n -= 9
    }
    suma += n
    doble = !doble
  }
  return suma % 10 === 0
}

export function marca(numero: string): 'Visa' | 'Mastercard' | null {
  const d = soloDigitos(numero)
  if (/^4/.test(d)) return 'Visa'
  if (/^(5[1-5]|2[2-7])/.test(d)) return 'Mastercard'
  return null
}

/** "4111111111111111" → "4111 1111 1111 1111" */
export function formatearNumero(v: string): string {
  return soloDigitos(v)
    .slice(0, 19)
    .replace(/(\d{4})(?=\d)/g, '$1 ')
}

/** "0829" → "08/29"; valida mes y que no esté vencida. */
export function vencimientoValido(v: string, hoy = new Date()): boolean {
  const m = /^(\d{2})\/?(\d{2})$/.exec(v.trim())
  if (!m) return false
  const mes = Number(m[1])
  const anio = 2000 + Number(m[2])
  if (mes < 1 || mes > 12) return false
  const finDeMes = new Date(anio, mes, 0, 23, 59, 59)
  return finDeMes >= hoy
}
