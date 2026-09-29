<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, reactive, ref, watch } from 'vue'
import { ApiError, api, unwrap, type Schemas } from '@/api/client'
import AppDialog from '@/components/ui/AppDialog.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import { DIAS } from '@/lib/labels'
import { useToastStore } from '@/stores/toast'

type Servicio = Schemas['ServicioOficina']
interface Dia {
  abierto: boolean
  apertura: string
  cierre: string
}

const props = defineProps<{ oficina: { id: number; codigo: string; nombre: string } | null }>()
const emit = defineEmits<{ cerrar: [] }>()
const avisos = useToastStore()
const cliente = useQueryClient()

const detalle = useQuery({
  queryKey: computed(() => ['oficina', props.oficina?.codigo]),
  queryFn: () => unwrap(api.GET('/api/v1/oficinas/{codigo}', { params: { path: { codigo: props.oficina!.codigo } } })),
  enabled: computed(() => !!props.oficina),
})

const SERVICIOS: { value: Servicio; label: string }[] = [
  { value: 'general', label: 'General' },
  { value: 'boleteria', label: 'Boletería' },
  { value: 'carga', label: 'Carga' },
]
const servicio = ref<Servicio>('general')
const semana = reactive<Record<Servicio, Dia[]>>({ general: [], boleteria: [], carga: [] })

function vacia(): Dia[] {
  return DIAS.map(() => ({ abierto: false, apertura: '08:00', cierre: '18:00' }))
}
watch(
  () => detalle.data.value,
  (d) => {
    if (!d) return
    for (const s of SERVICIOS) {
      semana[s.value] = vacia()
      for (const h of d.horarios.filter((x) => x.servicio === s.value)) {
        semana[s.value][h.dia_semana - 1] = { abierto: true, apertura: h.hora_apertura.slice(0, 5), cierre: h.hora_cierre.slice(0, 5) }
      }
    }
    servicio.value = d.horarios.some((h) => h.servicio === 'general') || !d.horarios.length ? 'general' : (d.horarios[0].servicio as Servicio)
  },
  { immediate: true },
)
function copiarLunes(): void {
  const l = semana[servicio.value][0]
  semana[servicio.value] = semana[servicio.value].map((d, i) => (i < 5 ? { ...l } : d))
}

const invalido = computed(() =>
  SERVICIOS.some((s) => semana[s.value].some((d) => d.abierto && d.cierre <= d.apertura)),
)
const guardar = useMutation({
  mutationFn: () =>
    unwrap(
      api.PUT('/api/v1/admin/oficinas/{oficina_id}/horarios', {
        params: { path: { oficina_id: props.oficina!.id } },
        body: SERVICIOS.flatMap((s) =>
          semana[s.value].flatMap((d, i) => (d.abierto ? [{ servicio: s.value, dia_semana: i + 1, hora_apertura: d.apertura, hora_cierre: d.cierre }] : [])),
        ),
      }),
    ),
  onSuccess: () => {
    avisos.exito('Horario actualizado')
    void cliente.invalidateQueries({ queryKey: ['oficina'] })
    void cliente.invalidateQueries({ queryKey: ['oficinas'] })
    emit('cerrar')
  },
  onError: (e) => avisos.error('No se pudo guardar', e instanceof ApiError ? e.message : undefined),
})
</script>

<template>
  <AppDialog :open="!!oficina" :title="`Horario · ${oficina?.nombre ?? ''}`" description="Marca los días de atención y sus horas." size="lg" @update:open="(v) => !v && emit('cerrar')">
    <SkeletonBlock v-if="detalle.isLoading.value" class="h-72" />
    <div v-else class="flex flex-col gap-4">
      <SegmentedControl v-model="servicio" label="Servicio" variant="switch" :options="SERVICIOS" />
      <ul class="flex flex-col divide-y divide-line rounded-xl border border-line">
        <li v-for="(d, i) in semana[servicio]" :key="i" class="flex flex-wrap items-center gap-3 px-4 py-2.5">
          <label class="flex w-32 items-center gap-2.5 text-sm font-semibold">
            <input v-model="d.abierto" type="checkbox" class="size-4.5 accent-carmin-600" />{{ DIAS[i] }}
          </label>
          <template v-if="d.abierto">
            <input v-model="d.apertura" type="time" class="h-10 rounded-lg border border-line-strong bg-surface px-2 text-sm tabular" :aria-label="`Apertura ${DIAS[i]}`" />
            <span class="text-muted">a</span>
            <input v-model="d.cierre" type="time" class="h-10 rounded-lg border border-line-strong bg-surface px-2 text-sm tabular" :aria-label="`Cierre ${DIAS[i]}`" />
            <span v-if="d.cierre <= d.apertura" class="text-xs text-peligro-600">El cierre debe ser posterior</span>
          </template>
          <span v-else class="text-sm text-muted">Cerrado</span>
        </li>
      </ul>
      <button type="button" class="self-start text-sm font-semibold text-carmin-600 hover:underline dark:text-carmin-200" @click="copiarLunes">Copiar el lunes a toda la semana laboral</button>
    </div>
    <template #footer>
      <BaseButton variant="subtle" @click="emit('cerrar')">Cancelar</BaseButton>
      <BaseButton :disabled="invalido" :loading="guardar.isPending.value" @click="guardar.mutate()">Guardar horario</BaseButton>
    </template>
  </AppDialog>
</template>
