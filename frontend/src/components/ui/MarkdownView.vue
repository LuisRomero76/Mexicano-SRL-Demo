<script setup lang="ts">
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed } from 'vue'

const props = defineProps<{ source: string }>()

// El contenido viene de la base de datos (editable por el personal): siempre se sanea.
const html = computed(() => {
  const crudo = marked.parse(props.source, { async: false, gfm: true, breaks: false }) as string
  return DOMPurify.sanitize(crudo, {
    ALLOWED_TAGS: ['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'li', 'strong', 'em', 'a', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'code', 'br', 'hr', 'blockquote'],
    ALLOWED_ATTR: ['href', 'title'],
    ALLOWED_URI_REGEXP: /^(?:https?:|mailto:|tel:|\/)/i,
  })
})
</script>

<template>
  <div class="markdown" v-html="html" />
</template>

<style scoped>
.markdown :deep(h1) {
  font-family: var(--font-display);
  font-size: 1.875rem;
  font-weight: 700;
  margin: 0 0 1rem;
}
.markdown :deep(h2) {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 600;
  margin: 1.75rem 0 0.5rem;
}
.markdown :deep(p),
.markdown :deep(li) {
  line-height: 1.7;
  color: var(--color-fg);
}
.markdown :deep(p) {
  margin: 0 0 0.9rem;
}
.markdown :deep(ul) {
  list-style: disc;
  padding-left: 1.25rem;
  margin: 0 0 1rem;
}
.markdown :deep(a) {
  color: var(--color-carmin-600);
  font-weight: 600;
  text-decoration: underline;
}
.markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  font-size: 0.9rem;
}
.markdown :deep(th),
.markdown :deep(td) {
  border-bottom: 1px solid var(--color-line);
  padding: 0.6rem 0.5rem;
  text-align: left;
}
.markdown :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.85em;
  background: var(--color-surface-2);
  padding: 0.1em 0.35em;
  border-radius: 4px;
}
</style>
