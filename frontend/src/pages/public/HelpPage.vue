<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { refDebounced } from '@vueuse/core'
import { ChevronDown, MessageCircle, Phone, Search } from '@lucide/vue'
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, unwrap } from '@/api/client'
import { useEmpresa } from '@/api/queries'
import ErrorState from '@/components/ui/ErrorState.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import { telefono, whatsappUrl } from '@/lib/format'

const route = useRoute()
const { data: empresa } = useEmpresa()
const faqs = useQuery({ queryKey: ['faqs'], queryFn: () => unwrap(api.GET('/api/v1/faqs')) })
const texto = ref('')
const q = refDebounced(texto, 350)
const busqueda = useQuery({
  queryKey: computed(() => ['faq-buscar', q.value]),
  queryFn: () => unwrap(api.GET('/api/v1/faqs/buscar', { params: { query: { q: q.value } } })),
  enabled: computed(() => q.value.trim().length >= 3),
})
const abiertas = ref<Set<string>>(new Set())

function alternar(slug: string, abierto: boolean): void {
  const s = new Set(abiertas.value)
  if (abierto) s.add(slug)
  else s.delete(slug)
  abiertas.value = s
}

onMounted(async () => {
  const slug = route.hash.slice(1)
  if (!slug) return
  abiertas.value = new Set([slug])
  await nextTick()
  document.getElementById(slug)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
})
</script>

<template>
  <div>
    <section class="bg-noche-900 text-white">
      <div class="contenedor flex flex-col gap-5 py-10 sm:py-14">
        <h1 class="text-[34px] font-bold sm:text-[44px]">¿En qué te ayudamos?</h1>
        <div class="relative max-w-2xl">
          <label for="faq-buscar" class="sr-only">Buscar en las preguntas frecuentes</label>
          <Search class="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-muted" aria-hidden="true" />
          <input
            id="faq-buscar"
            v-model="texto"
            type="search"
            placeholder="Por ejemplo: ¿puedo viajar con mi perro?"
            class="h-14 w-full rounded-xl bg-white pr-4 pl-12 text-base text-noche-900 outline-none focus:ring-4 focus:ring-carmin-500/40"
          />
        </div>
        <div v-if="q.trim().length >= 3" class="max-w-2xl rounded-2xl bg-white p-5 text-noche-900" aria-live="polite">
          <SkeletonBlock v-if="busqueda.isLoading.value" class="h-16" />
          <template v-else-if="busqueda.data.value">
            <p class="text-[15px] leading-relaxed">{{ busqueda.data.value.mensaje }}</p>
            <ul v-if="busqueda.data.value.resultados.length" class="mt-3 flex flex-wrap gap-2">
              <li v-for="r in busqueda.data.value.resultados" :key="r.slug">
                <a :href="`#${r.slug}`" class="inline-flex rounded-full bg-carmin-50 px-3 py-1.5 text-sm font-semibold text-carmin-700" @click="alternar(r.slug, true)">{{ r.pregunta }}</a>
              </li>
            </ul>
          </template>
        </div>
      </div>
    </section>

    <div class="contenedor grid items-start gap-8 py-10 lg:grid-cols-[1fr_320px]">
      <div class="flex flex-col gap-8">
        <ErrorState v-if="faqs.isError.value" :error="faqs.error.value" @retry="faqs.refetch()" />
        <SkeletonBlock v-else-if="faqs.isLoading.value" class="h-96 rounded-2xl" />
        <section v-for="c in faqs.data.value ?? []" v-else :key="c.codigo" :aria-labelledby="`cat-${c.codigo}`" class="flex flex-col gap-3">
          <h2 :id="`cat-${c.codigo}`" class="text-xl font-bold text-noche-900">{{ c.nombre }}</h2>
          <div class="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
            <details
              v-for="f in c.preguntas"
              :id="f.slug"
              :key="f.slug"
              class="group scroll-mt-28"
              :open="abiertas.has(f.slug)"
              @toggle="alternar(f.slug, ($event.target as HTMLDetailsElement).open)"
            >
              <summary class="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 px-5 py-3.5 font-semibold hover:bg-surface-2 [&::-webkit-details-marker]:hidden">
                {{ f.pregunta }}
                <ChevronDown class="size-5 shrink-0 text-muted transition-transform group-open:rotate-180" aria-hidden="true" />
              </summary>
              <div class="px-5 pb-5 text-[15px] leading-relaxed whitespace-pre-line text-fg/85">{{ f.respuesta }}</div>
            </details>
          </div>
        </section>
      </div>
      <aside class="flex flex-col gap-4 lg:sticky lg:top-24">
        <div class="flex flex-col gap-3 rounded-2xl bg-noche-900 p-6 text-white">
          <h2 class="font-sans text-lg font-bold">¿No encontraste tu respuesta?</h2>
          <a
            v-if="empresa?.whatsapp_central_e164"
            :href="whatsappUrl(empresa.whatsapp_central_e164, 'Hola, tengo una consulta.')"
            target="_blank"
            rel="noopener noreferrer"
            class="flex h-12 items-center justify-center gap-2 rounded-xl bg-exito-600 font-semibold hover:bg-exito-800"
          >
            <MessageCircle class="size-5" aria-hidden="true" />WhatsApp {{ telefono(empresa.whatsapp_central_e164) }}
          </a>
          <a
            v-if="empresa?.telefono_atencion_cliente_e164"
            :href="`tel:+${empresa.telefono_atencion_cliente_e164}`"
            class="flex h-12 items-center justify-center gap-2 rounded-xl border border-noche-600 font-semibold hover:bg-white/5"
          >
            <Phone class="size-5" aria-hidden="true" />Atención al cliente
          </a>
        </div>
      </aside>
    </div>
  </div>
</template>
