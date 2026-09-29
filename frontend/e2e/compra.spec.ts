import { expect, test } from '@playwright/test'
import { fechaEn } from './datos'

test('compra completa de un pasaje con tarjeta', async ({ page }) => {
  await page.goto(`/pasajes?origen=Sucre&destino=Santa%20Cruz&fecha=${fechaEn(3)}&pasajeros=1`)
  await page.getByRole('button', { name: 'Elegir asientos' }).first().click()

  await expect(page).toHaveURL(/\/asientos/)
  await page.locator('button[aria-label*="libre"]').first().click()
  await page.getByRole('button', { name: /continuar/i }).first().click()

  await expect(page).toHaveURL(/\/compra\/pasajeros/)
  const documento = String(Date.now()).slice(-7)
  await page.getByLabel('Número').first().fill(documento)
  await page.getByLabel('Nombres').first().fill('Prueba')
  await page.getByLabel('Apellidos').first().fill('Automatizada')
  await page.getByLabel('Celular').fill('71234567')
  await page.getByRole('button', { name: 'Reservar y continuar al pago' }).click()

  await expect(page).toHaveURL(/\/compra\/pago\//)
  await page.getByRole('radiogroup', { name: 'Método de pago' }).getByText('Tarjeta', { exact: true }).click()
  await page.getByLabel('Número de tarjeta').fill('4111 1111 1111 1111')
  await page.getByLabel('Vencimiento').fill('12/30')
  await page.getByLabel('CVV').fill('123')
  await page.getByLabel('Nombre del titular').fill('PRUEBA AUTOMATIZADA')
  await page.locator('form button[type=submit]').last().click()

  await expect(page).toHaveURL(/\/compra\/confirmacion\//)
  await expect(page.getByRole('heading', { name: /Tu viaje está confirmado/ })).toBeVisible()
})
