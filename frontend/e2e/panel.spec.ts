import { expect, test, type Page } from '@playwright/test'
import { GUIA, PASSWORD, USUARIOS } from './datos'

async function ingresar(page: Page, email: string): Promise<void> {
  await page.goto('/admin/login')
  await page.locator('#login-email').fill(email)
  await page.locator('#login-password').fill(PASSWORD)
  await page.locator('button[type=submit]').click()
  await expect(page).toHaveURL(/\/admin$/)
}

test('el panel exige iniciar sesión', async ({ page }) => {
  await page.goto('/admin/ventas')
  await expect(page).toHaveURL(/\/admin\/login/)
})

test('credenciales incorrectas muestran un error', async ({ page }) => {
  await page.goto('/admin/login')
  await page.locator('#login-email').fill(USUARIOS.supervisor)
  await page.locator('#login-password').fill('incorrecta-123')
  await page.locator('button[type=submit]').click()
  await expect(page.getByRole('alert').first()).toBeVisible()
})

test('la sesión vive en una cookie httpOnly y no en el almacenamiento del navegador', async ({ page, context }) => {
  await ingresar(page, USUARIOS.supervisor)
  const cookie = (await context.cookies()).find((c) => c.name === 'em_session')
  expect(cookie?.httpOnly).toBe(true)
  const guardado = await page.evaluate(() => JSON.stringify({ ...localStorage }) + JSON.stringify({ ...sessionStorage }))
  expect(guardado).not.toMatch(/eyJ/) // ningún JWT accesible desde JavaScript
})

test('supervisor recorre las secciones principales', async ({ page }) => {
  await ingresar(page, USUARIOS.supervisor)
  const secciones: [string, string][] = [
    ['/admin/salidas', 'Salidas'],
    ['/admin/ventas', 'Ventas'],
    ['/admin/encomiendas', 'Encomiendas'],
    ['/admin/puerta-a-puerta', 'Puerta a puerta'],
    ['/admin/catalogos/oficinas', 'Catálogos'],
    ['/admin/clientes', 'Clientes'],
    ['/admin/reportes', 'Reportes'],
    ['/admin/auditoria', 'Auditoría'],
  ]
  for (const [ruta, titulo] of secciones) {
    await page.goto(ruta)
    await expect(page.getByRole('heading', { level: 1, name: titulo })).toBeVisible()
  }
})

test('bodega ve el detalle de una guía', async ({ page }) => {
  await ingresar(page, USUARIOS.bodega)
  await page.goto(`/admin/encomiendas/${GUIA}`)
  await expect(page.getByRole('heading', { name: `Guía ${GUIA}` })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Historial de rastreo' })).toBeVisible()
})

test('un rol sin permiso no entra a secciones ajenas', async ({ page }) => {
  await ingresar(page, USUARIOS.bodega)
  await page.goto('/admin/reportes')
  await expect(page).toHaveURL(/sin-permiso/)
})

test('cerrar sesión invalida el acceso', async ({ page }) => {
  await ingresar(page, USUARIOS.boletero)
  await page.getByRole('button', { name: /cerrar sesión/i }).first().click()
  await expect(page).toHaveURL(/\/admin\/login/)
  await page.goto('/admin/ventas')
  await expect(page).toHaveURL(/\/admin\/login/)
})
