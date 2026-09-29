/** Datos de demostración sembrados por el backend (ver backend/README). */
export const PASSWORD = process.env.E2E_PASSWORD ?? 'ElMexicano2026!'
export const USUARIOS = {
  admin: 'admin@elmexicanosrl.com',
  supervisor: 'supervisor@elmexicanosrl.com',
  boletero: 'boleteria.sucre@elmexicanosrl.com',
  bodega: 'bodega.sucre@elmexicanosrl.com',
}
export const GUIA = '26000101'
export const RESERVA = { codigo: 'MX7K2P', documento: '6123456' }

/** Fecha ISO (hora de Bolivia) dentro de `dias` días. */
export function fechaEn(dias: number): string {
  const hoy = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/La_Paz' }).format(new Date())
  const [a, m, d] = hoy.split('-').map(Number)
  return new Date(Date.UTC(a, m - 1, d + dias)).toISOString().slice(0, 10)
}
