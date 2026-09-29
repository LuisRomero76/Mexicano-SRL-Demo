import { computed, onBeforeUnmount, ref, watch, type Ref } from 'vue'

/** Cuenta regresiva hasta una fecha ISO: "mm:ss" y si ya venció. */
export function useCuentaRegresiva(hasta: Ref<string | null | undefined>) {
  const ahora = ref(Date.now())
  let reloj: number | undefined

  const restanteMs = computed(() => (hasta.value ? new Date(hasta.value).getTime() - ahora.value : null))
  const vencido = computed(() => restanteMs.value !== null && restanteMs.value <= 0)
  const texto = computed(() => {
    if (restanteMs.value === null) return ''
    const s = Math.max(0, Math.floor(restanteMs.value / 1000))
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    const seg = s % 60
    const mmss = `${String(m).padStart(2, '0')}:${String(seg).padStart(2, '0')}`
    return h ? `${h}:${mmss}` : mmss
  })
  const urgente = computed(() => restanteMs.value !== null && restanteMs.value < 3 * 60_000)

  watch(
    hasta,
    (valor) => {
      window.clearInterval(reloj)
      if (valor) reloj = window.setInterval(() => (ahora.value = Date.now()), 1000)
    },
    { immediate: true },
  )
  onBeforeUnmount(() => window.clearInterval(reloj))

  return { texto, vencido, urgente }
}
