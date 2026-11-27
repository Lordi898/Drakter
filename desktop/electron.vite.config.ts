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
    // dbus-next y zod (modo flotante) van dentro del bundle: electron-builder no empaqueta node_modules.
    // `usocket` y `x11` son requires opcionales de dbus-next que Drakter no usa (sockets abstractos, X11).
    plugins: [externalizeDepsPlugin({ exclude: ['dbus-next', 'zod'] })],
    build: {
      rollupOptions: { input: resolve(__dirname, 'electron/main/index.ts'), external: ['usocket', 'x11'] }
    }
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: {
      rollupOptions: {
        input: {
          index: resolve(__dirname, 'electron/preload/index.ts'),
          // Página flotante (CONTRACT §4.3): `window.drakterFloat`.
          floating: resolve(__dirname, 'electron/preload/floating.ts')
        }
      }
    }
  },
  renderer: {
    root: '.',
    // electron-vite deja el renderer sin minificar por defecto (1,66 MB en un solo chunk).
    // Las pantallas se parten con React.lazy en src/navigation/pages.ts.
    build: { minify: true, rollupOptions: { input: resolve(__dirname, 'index.html') } },
    resolve: { alias: { '@': resolve(__dirname, 'src') } },
    plugins: [contentSecurityPolicy(), react(), tailwindcss()]
  }
})
