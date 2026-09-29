import { z } from 'zod'

export const documento = z
  .string()
  .trim()
  .min(4, 'Ingresa al menos 4 caracteres')
  .max(20, 'Máximo 20 caracteres')
  .regex(/^[A-Za-z0-9-]+$/, 'Solo letras, números y guiones')

export const nombre = z
  .string()
  .trim()
  .min(2, 'Escribe al menos 2 letras')
  .max(80, 'Máximo 80 caracteres')
  .regex(/^[\p{L}' .-]+$/u, 'Solo letras')

/** Celular boliviano (8 dígitos que empiezan con 6 o 7) o número internacional con +. */
export const celular = z
  .string()
  .trim()
  .refine((v) => {
    const d = v.replace(/[\s()-]/g, '')
    return /^(\+?591)?[67]\d{7}$/.test(d) || /^\+\d{10,15}$/.test(d)
  }, 'Ingresa un celular válido, p. ej. 71234567')

export const correoOpcional = z
  .string()
  .trim()
  .max(150)
  .refine((v) => v === '' || z.email().safeParse(v).success, 'Correo no válido')

export const guia = z
  .string()
  .transform((v) => v.replace(/\D/g, ''))
  .refine((v) => v.length === 8, 'La guía tiene 8 dígitos')

/** Convierte los errores de Zod en { "ruta.del.campo": "mensaje" } (primer error por campo). */
export function erroresDe(resultado: z.ZodSafeParseResult<unknown>): Record<string, string> {
  if (resultado.success) return {}
  const errores: Record<string, string> = {}
  for (const issue of resultado.error.issues) {
    const clave = issue.path.join('.')
    errores[clave] ??= issue.message
  }
  return errores
}
