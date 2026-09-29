import { computed, useAttrs } from 'vue'

/**
 * En los campos de formulario, `class` y `style` van al contenedor (maquetación)
 * y el resto de atributos (placeholder, maxlength, inputmode…) al control.
 */
export function useAtributosDeCampo() {
  const attrs = useAttrs()
  const raiz = computed(() => ({ class: attrs.class, style: attrs.style }))
  const control = computed(() => {
    const { class: _c, style: _s, ...resto } = attrs
    return resto
  })
  return { raiz, control }
}
