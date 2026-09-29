import { expect, test } from '@playwright/test'
import { GUIA, RESERVA } from './datos'

test('la portada permite buscar pasajes', async ({ page }) => {
  await page.goto('/')
  const buscador = page.getByRole('form', { name: 'Buscar pasajes' })
  await expect(buscador).toBeVisible()
  await buscador.locator('button[type=submit]').click()
  await expect(page).toHaveURL(/\/pasajes\?/)
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
})

test('rastrea una encomienda por su guía', async ({ page }) => {
  await page.goto(`/rastreo/${GUIA}`)
  await expect(page.getByRole('heading', { name: 'Historial' })).toBeVisible()
  await expect(page.getByText('Lista para recoger').first()).toBeVisible()
})

test('una guía inexistente muestra un mensaje claro', async ({ page }) => {
  await page.goto('/rastreo/99999999')
  await expect(page.getByText(/no encontr/i).first()).toBeVisible()
})

test('consulta una reserva con código y documento', async ({ page }) => {
  await page.goto('/mi-reserva')
  await page.getByLabel('Código de reserva').fill(RESERVA.codigo)
  await page.getByLabel('Documento del comprador o de un pasajero').fill(RESERVA.documento)
  await page.getByRole('button', { name: 'Consultar' }).click()
  await expect(page.getByText(/asiento/i).first()).toBeVisible()
})

test('páginas informativas y página no encontrada', async ({ page }) => {
  for (const ruta of ['/rutas', '/buses', '/oficinas', '/ayuda', '/carga', '/terminos']) {
    await page.goto(ruta)
    await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible()
  }
  await page.goto('/no-existe')
  await expect(page.getByText(/no encontr|no existe/i).first()).toBeVisible()
})
