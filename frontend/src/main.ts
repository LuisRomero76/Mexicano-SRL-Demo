import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { ApiError } from '@/api/client'
import App from './App.vue'
import { router } from './router'
import './styles/main.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // Solo reintenta errores de red o del servidor, nunca 4xx.
      retry: (intentos, error) =>
        intentos < 2 && !(error instanceof ApiError && error.status >= 400 && error.status < 500),
    },
  },
})

createApp(App).use(createPinia()).use(router).use(VueQueryPlugin, { queryClient }).mount('#app')
