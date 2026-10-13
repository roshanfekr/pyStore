import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// The build is emitted into the storefront app's static directory so Django's
// static files machinery serves it without extra configuration. `base` must
// match STATIC_URL + the output folder name.
export default defineConfig({
  plugins: [vue()],
  base: '/static/storefront-spa/',
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    outDir: '../apps/storefront/static/storefront-spa',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/static': 'http://127.0.0.1:8000',
      '/admin': 'http://127.0.0.1:8000',
    },
  },
})
