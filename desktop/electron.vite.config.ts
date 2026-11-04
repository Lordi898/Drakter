import { resolve } from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import type { Plugin } from 'vite'

/**
 * CSP inyectada en index.html. En producción no hay `unsafe-eval` ni scripts
 * en línea; `connect-src` queda cerrado hasta que exista el contrato del backend.
 * `style-src 'unsafe-inline'` es necesario para los estilos que Radix y Sonner
 * aplican en tiempo de ejecución.
 */
const PRODUCTION_CSP = [
  "default-src 'none'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "font-src 'self'",
  "img-src 'self' data: blob:",
  "connect-src 'none'",
  "base-uri 'none'",
  "form-action 'none'",
  "object-src 'none'"
].join('; ')

/** El servidor de desarrollo necesita el preámbulo en línea de React Refresh y su WebSocket. */
const DEVELOPMENT_CSP = [
  "default-src 'none'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "font-src 'self'",
  "img-src 'self' data: blob:",
  "connect-src 'self' ws://localhost:* ws://127.0.0.1:*",
  "base-uri 'none'",
  "form-action 'none'",
  "object-src 'none'"
].join('; ')

function contentSecurityPolicy(): Plugin {
  return {
    name: 'drakter-csp',
    transformIndexHtml(html, context) {
      const policy = context.server ? DEVELOPMENT_CSP : PRODUCTION_CSP
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
