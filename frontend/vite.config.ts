/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig, loadEnv, type Plugin } from 'vite'

/**
 * Inyecta una Content-Security-Policy estricta solo en el build de producción
 * (en desarrollo Vite necesita scripts en línea para el HMR).
 * `frame-ancestors` no se puede fijar por <meta>: el servidor web debe enviarla como cabecera.
 */
function politicaDeSeguridad(apiBase: string): Plugin {
  const conectar = ["'self'", apiBase ? new URL(apiBase).origin : ''].filter(Boolean).join(' ')
  const csp = [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src ${conectar}`,
    "media-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; ')
  return {
    name: 'politica-de-seguridad',
    apply: 'build',
    transformIndexHtml(html) {
      return html.replace('<head>', `<head>\n    <meta http-equiv="Content-Security-Policy" content="${csp}">`)
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget = env.VITE_API_PROXY || 'http://localhost:8000'
  return {
    plugins: [vue(), tailwindcss(), politicaDeSeguridad(env.VITE_API_BASE_URL || '')],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': { target: proxyTarget, changeOrigin: true },
        '/health': { target: proxyTarget, changeOrigin: true },
      },
    },
    preview: {
      port: 4173,
      proxy: {
        '/api': { target: proxyTarget, changeOrigin: true },
      },
    },
    build: {
      sourcemap: false,
      chunkSizeWarningLimit: 900,
      rollupOptions: {
        output: {
          manualChunks(id: string) {
            if (id.includes('node_modules/echarts') || id.includes('node_modules/zrender')) return 'charts'
            if (id.includes('node_modules/marked') || id.includes('node_modules/dompurify')) return 'markdown'
          },
        },
      },
    },
    test: {
      environment: 'jsdom',
      include: ['src/**/*.spec.ts'],
    },
  }
})
