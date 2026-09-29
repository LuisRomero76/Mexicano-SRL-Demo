<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { api, unwrap } from '@/api/client'
import ErrorState from '@/components/ui/ErrorState.vue'
import MarkdownView from '@/components/ui/MarkdownView.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'

const props = defineProps<{ slug: string }>()
const pagina = useQuery({
  queryKey: computed(() => ['pagina', props.slug]),
  queryFn: () => unwrap(api.GET('/api/v1/paginas/{slug}', { params: { path: { slug: props.slug } } })),
})
</script>

<template>
  <div class="contenedor max-w-3xl py-12">
    <SkeletonBlock v-if="pagina.isLoading.value" class="h-80 rounded-2xl" />
    <ErrorState v-else-if="pagina.isError.value" :error="pagina.error.value" @retry="pagina.refetch()" />
    <article v-else-if="pagina.data.value" class="rounded-2xl border border-line bg-surface p-6 sm:p-10">
      <MarkdownView :source="pagina.data.value.contenido_md" />
    </article>
  </div>
</template>
