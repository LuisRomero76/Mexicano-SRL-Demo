<script setup lang="ts">
import { computed } from 'vue'
import type { Schemas } from '@/api/client'

type Asiento = Schemas['AsientoMapa']

const props = withDefaults(
  defineProps<{
    asientos: Asiento[]
    maximo: number
    titulo: string
    precio?: string
    /** En boletería la selección es libre; en web se limita a `maximo`. */
    compacto?: boolean
    horizontal?: boolean
  }>(),
  { horizontal: true },
)
const seleccion = defineModel<number[]>({ required: true })

const filas = computed(() => Math.max(1, ...props.asientos.map((a) => a.fila)))

function alternar(a: Asiento): void {
  if (a.estado !== 'libre') return
  const actual = seleccion.value
  if (actual.includes(a.numero)) {
    seleccion.value = actual.filter((n) => n !== a.numero)
  } else if (actual.length >= props.maximo) {
    // Al llegar al máximo, el asiento nuevo reemplaza al primero elegido.
    seleccion.value = [...actual.slice(1), a.numero]
  } else {
    seleccion.value = [...actual, a.numero]
  }
}

function clases(a: Asiento): string {
  if (seleccion.value.includes(a.numero)) return 'bg-carmin-600 text-white shadow-[0_4px_12px_-4px_rgb(179_18_46/0.6)]'
  if (a.estado === 'libre')
    return 'bg-surface text-fg border-[1.5px] border-[#9AA3B2] hover:border-carmin-600 hover:text-carmin-600 dark:border-noche-400'
  return 'bg-[#D9DDE4] text-[#8A93A3] cursor-not-allowed dark:bg-white/10 dark:text-noche-400'
}

function descripcion(a: Asiento): string {
  const estado = seleccion.value.includes(a.numero) ? 'elegido' : a.estado === 'libre' ? 'libre' : 'ocupado'
  const lado = a.posicion === 'ventana' ? 'ventana' : 'pasillo'
  return `Asiento ${a.numero}, ${lado}, ${estado}`
}

/** Columna visual: 1 y 2 a un lado del pasillo, la 3 (individual) al otro. */
const pista = (columna: number) => (columna === 3 ? 4 : columna)
</script>

<template>
  <section :aria-label="titulo" class="flex flex-col gap-3">
    <div class="flex items-baseline justify-between gap-3">
      <h3 class="font-sans text-[15px] font-bold">{{ titulo }}</h3>
      <span v-if="precio" class="text-sm text-muted">{{ precio }}</span>
    </div>
    <div class="flex gap-3" :class="horizontal ? 'flex-col md:flex-row' : 'flex-col'">
      <div
        class="flex items-center justify-center rounded-xl border-[1.5px] border-dashed border-line-strong text-[11px] font-bold tracking-[0.2em] text-muted"
        :class="horizontal ? 'h-8 md:h-auto md:w-10 md:[writing-mode:vertical-rl] md:rotate-180' : 'h-8'"
        aria-hidden="true"
      >
        FRENTE
      </div>
      <div
        class="seat-grid grid gap-2 justify-center"
        :class="horizontal ? 'seat-grid--h' : ''"
        :style="{ '--filas': filas }"
      >
        <button
          v-for="a in asientos"
          :key="a.numero"
          type="button"
          class="flex items-center justify-center rounded-lg text-[13px] font-bold transition-[background,box-shadow,transform] active:scale-95"
          :class="[clases(a), compacto ? 'h-9 w-11' : 'h-11 w-12 md:w-auto']"
          :style="{ '--fila': a.fila, '--col': pista(a.columna) }"
          :disabled="a.estado !== 'libre'"
          :aria-pressed="seleccion.includes(a.numero)"
          :aria-label="descripcion(a)"
          @click="alternar(a)"
        >
          {{ a.numero }}
        </button>
        <span class="pasillo text-[10px] font-bold tracking-[0.25em] text-muted/70" aria-hidden="true">PASILLO</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* Vertical (celular): filas hacia abajo, 2 + pasillo + 1 */
.seat-grid {
  grid-template-columns: repeat(2, auto) 28px auto;
  grid-template-rows: repeat(var(--filas), auto);
}
.seat-grid > button {
  grid-row: var(--fila);
  grid-column: var(--col);
}
.pasillo {
  display: none;
}
@media (width >= 48rem) {
  /* Horizontal (escritorio): el frente a la izquierda, cada fila es una columna */
  .seat-grid--h {
    grid-template-columns: repeat(var(--filas), minmax(40px, 56px));
    grid-template-rows: repeat(2, auto) 22px auto;
    justify-content: start;
  }
  .seat-grid--h > button {
    grid-row: var(--col);
    grid-column: var(--fila);
  }
  .seat-grid--h .pasillo {
    display: flex;
    align-items: center;
    grid-row: 3;
    grid-column: 1 / -1;
  }
}
</style>
