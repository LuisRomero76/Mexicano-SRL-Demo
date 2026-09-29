<script setup lang="ts">
import { useId } from 'vue'
import { useAtributosDeCampo } from '@/composables/useAtributosDeCampo'
import FormField from './FormField.vue'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  label?: string
  hint?: string
  error?: string | null
  required?: boolean
  id?: string
  rows?: number
}>()
const modelo = defineModel<string | null>()
const idFinal = props.id ?? useId()
const { raiz, control } = useAtributosDeCampo()
</script>

<template>
  <FormField v-bind="raiz" :id="idFinal" :label="label" :hint="hint" :error="error" :required="required">
    <template #default="{ describedby, invalid }">
      <textarea
        :id="idFinal"
        v-model="modelo"
        v-bind="control"
        :rows="rows ?? 4"
        :required="required"
        :aria-invalid="invalid || undefined"
        :aria-describedby="describedby"
        class="w-full rounded-control border-[1.5px] bg-surface px-3.5 py-2.5 text-[15px] text-fg outline-none focus:border-noche-900 focus:ring-4 focus:ring-(--ring)"
        :class="invalid ? 'border-peligro-600' : 'border-line-strong'"
      />
    </template>
  </FormField>
</template>
