<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ExternalLink } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { ApiError, api, unwrap } from '@/api/client'
import BaseButton from '@/components/ui/BaseButton.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import MarkdownView from '@/components/ui/MarkdownView.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import TabsBar from '@/components/ui/TabsBar.vue'
import TextArea from '@/components/ui/TextArea.vue'
import TextInput from '@/components/ui/TextInput.vue'
import { useToastStore } from '@/stores/toast'

const avisos = useToastStore()
const cliente = useQueryClient()
const paginas = useQuery({ queryKey: ['paginas'], queryFn: () => unwrap(api.GET('/api/v1/paginas')) })

const slug = ref<string | null>(null)
watch(
  () => paginas.data.value,
  (l) => {
    if (l?.length && !slug.value) slug.value = l[0].slug
  },
  { immediate: true },
)
const actual = computed(() => paginas.data.value?.find((p) => p.slug === slug.value))
const form = reactive({ titulo: '', meta: '', contenido: '' })
watch(
  actual,
  (p) => {
    if (!p) return
    Object.assign(form, { titulo: p.titulo, meta: p.meta_descripcion ?? '', contenido: p.contenido_md })
  },
  { immediate: true },
)
const cambiado = computed(
  () => !!actual.value && (form.titulo !== actual.value.titulo || form.meta !== (actual.value.meta_descripcion ?? '') || form.contenido !== actual.value.contenido_md),
)
const vista = ref('editar')

const guardar = useMutation({
  mutationFn: () =>
    unwrap(
      api.PUT('/api/v1/admin/paginas/{slug}', {
        params: { path: { slug: slug.value! } },
        body: { titulo: form.titulo.trim(), meta_descripcion: form.meta.trim() || null, contenido_md: form.contenido },
      }),
    ),
  onSuccess: () => {
    avisos.exito('Página publicada')
    void cliente.invalidateQueries({ queryKey: ['paginas'] })
    void cliente.invalidateQueries({ queryKey: ['pagina'] })
  },
  onError: (e) => avisos.error('No se pudo guardar', e instanceof ApiError ? e.message : undefined),
})
</script>

<template>
  <section class="flex flex-col gap-4">
    <div>
      <h2 class="text-lg font-bold">Páginas del sitio</h2>
      <p class="mt-0.5 text-sm text-muted">Términos, privacidad y demás textos públicos. Se escriben en Markdown.</p>
    </div>
    <SkeletonBlock v-if="paginas.isLoading.value" class="h-96" />
    <ErrorState v-else-if="paginas.isError.value" :error="paginas.error.value" @retry="paginas.refetch()" />
    <div v-else class="grid items-start gap-4 lg:grid-cols-[220px_1fr]">
      <nav aria-label="Páginas" class="flex gap-1 overflow-x-auto lg:flex-col">
        <button
          v-for="p in paginas.data.value"
          :key="p.slug"
          type="button"
          class="rounded-lg px-3 py-2 text-left text-sm font-medium whitespace-nowrap"
          :class="p.slug === slug ? 'bg-noche-900 text-white dark:bg-noche-700' : 'hover:bg-surface-2'"
          @click="slug = p.slug"
        >
          {{ p.titulo }}
        </button>
      </nav>
      <div v-if="actual" class="flex min-w-0 flex-col gap-4 rounded-2xl border border-line bg-surface p-5">
        <div class="grid gap-3 md:grid-cols-2">
          <TextInput v-model="form.titulo" label="Título" required />
          <TextInput v-model="form.meta" label="Descripción para buscadores" maxlength="300" />
        </div>
        <TabsBar v-model="vista" label="Modo" :tabs="[{ key: 'editar', label: 'Editar' }, { key: 'vista', label: 'Vista previa' }]" />
        <TextArea v-if="vista === 'editar'" v-model="form.contenido" label="Contenido (Markdown)" :rows="18" class="font-mono text-sm" />
        <div v-else class="max-h-[560px] overflow-y-auto rounded-xl border border-line p-5">
          <MarkdownView :source="form.contenido" />
        </div>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <RouterLink :to="{ name: 'pagina', params: { slug: actual.slug } }" target="_blank" class="inline-flex items-center gap-1.5 text-sm font-semibold text-carmin-600 hover:underline dark:text-carmin-200">
            Ver en el sitio <ExternalLink class="size-3.5" aria-hidden="true" />
          </RouterLink>
          <div class="flex gap-2">
            <BaseButton variant="subtle" :disabled="!cambiado" @click="Object.assign(form, { titulo: actual.titulo, meta: actual.meta_descripcion ?? '', contenido: actual.contenido_md })">Descartar</BaseButton>
            <BaseButton :disabled="!cambiado || !form.titulo.trim()" :loading="guardar.isPending.value" @click="guardar.mutate()">Publicar cambios</BaseButton>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
