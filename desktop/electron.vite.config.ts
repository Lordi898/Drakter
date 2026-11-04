import { resolve } from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import type { Plugin } from 'vite'
import { RENDERER_CSP, RENDERER_DEV_CSP } from './electron/shared/csp'

function contentSecurityPolicy(): Plugin {
  return {
    name: 'drakter-csp',
    transformIndexHtml(html, context) {
      const policy = context.server ? RENDERER_DEV_CSP : RENDERER_CSP
      return html.replace('%DRAKTER_CSP%', policy)
    }
  }
}

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: { rollupOptions: { input: resolve(__dirname, 'electron/main/index.ts') } }
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: { rollupOptions: { input: resolve(__dirname, 'electron/preload/index.ts') } }
  },
  renderer: {
    root: '.',
    build: { rollupOptions: { input: resolve(__dirname, 'index.html') } },
    resolve: { alias: { '@': resolve(__dirname, 'src') } },
    plugins: [contentSecurityPolicy(), react(), tailwindcss()]
  }
})
