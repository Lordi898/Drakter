# Avatares 3D de Drakter

El usuario elige el avatar (Ajustes → Avatar, el selector de Jarvis o la voz) y la elección se guarda
en la preferencia `avatarId`. `registry.ts` resuelve ese id: un avatar portado, o `null` para el personaje
clásico (`none`, un id desconocido o uno aún no portado; nunca rompe). El predeterminado es `holo-contorno`.

Cada avatar es un módulo de Three.js **0.180.0** (la misma versión exacta que la app, una sola copia) con
**una sola implementación** y dos formas de montarla:

| Ruta | Quién la usa | Firma (`types.ts`) |
|---|---|---|
| **Capa** de un renderer ajeno | Stage de Jarvis (un único lienzo WebGL) | `CreateAvatarLayer = (renderer, options) => AvatarLayer` |
| **Lienzo propio** | Modo Drakter (`ThreeCharacter`) y la vista previa de Ajustes | `CreateAvatar = (canvas, options) => Avatar3D` |

La capa es el núcleo; `createAvatar` es un envoltorio que pone alrededor un `WebGLRenderer`, un bucle
`requestAnimationFrame` y la entrada de ratón. Ascuario (`ascuario/layer.ts` + `ascuario/index.ts`) es el
ejemplo de referencia.

## Lo que debe cumplir cada port (lista de comprobación)

- [ ] **Todo en `avatars/<id>/`** y una línea en `registry.ts` (más su `import`). Nada específico de un
      avatar fuera de su carpeta. `<id>` en minúsculas con guiones, igual que en el plan (`holo-orbe`).
- [ ] **Sin assets de terceros**: todo procedural o generado por nosotros. Si hay malla horneada, va como
      asset de Vite (`?url`) y se puede regenerar desde el código del propio avatar.
- [ ] **Three externo**: `import * as THREE from 'three'` (el paquete de la app, 0.180.0). Nunca un
      `.mjs` con Three empaquetado dentro ni otra versión. TypeScript estricto (compila con `tsconfig.web.json`).
- [ ] `register.ts` exporta `avatar: AvatarEntry` **sin importar Three** (el registro va en el chunk principal):
  ```ts
  import type { AvatarEntry } from '../registry'
  import thumbnail from './thumbnail.webp?url'
  export const avatar: AvatarEntry = {
    meta: { id: 'holo-orbe', name: 'Holo-Orbe', description: 'Una línea para Ajustes.', thumbnail,
            voiceAliases: ['orbe'] },
    load: () => import('./entry').then((m) => m.create),
    loadLayer: () => import('./entry').then((m) => m.createLayer),
    transparent: true
  }
  ```
- [ ] **Miniatura** `thumbnail.webp`: cuadrada, 192 px, menos de 20 KB, en estado `idle` y sobre el fondo con el
      que mejor se lee (oscuro para los hologramas).
- [ ] `entry.ts` exporta **las dos** funciones, `create: CreateAvatar` y `createLayer: CreateAvatarLayer`.
- [ ] **`transparent`**: si el avatar sabe dibujarse sin fondo propio, `transparent: true` en el registro y lo
      respeta en `AvatarOptions.transparent` (alfa premultiplicado, `clearAlpha` 0).
- [ ] **`theme`**: respeta `AvatarOptions.theme` al crear y, si su aspecto depende del fondo (un holograma
      aditivo no se ve sobre claro), implementa `setTheme('dark' | 'light')` en vivo. Si se ve igual, puede omitirlo.
- [ ] **`dispose()`** libera geometrías, materiales, texturas, listeners y el bucle; en la capa, nunca el renderer.
- [ ] `ready` se resuelve con los shaders compilados y se **rechaza** si la carga falla (el anfitrión cae al SVG).
      Nada de bloqueos de más de 100 ms en el hilo principal: si hay que tejer o esculpir, por tandas entre fotogramas.
- [ ] El bucle de `createAvatar` va a 30 fps como mucho y se para con `document.hidden`.
- [ ] **Rendimiento** medido en la UHD 620 dentro de `flock ~/.local/share/drakter/research/avatar3d/.medicion.lock`:
      CPU del renderer en reposo ≲ 12 %.

## Reglas de la capa (`AvatarLayer`)

- **No es dueña del renderer ni del bucle.** Nunca llama a `setSize`, `setPixelRatio`, `setAnimationLoop`
  ni a `dispose()` del renderer, ni registra `requestAnimationFrame`.
- `render(dt, viewport)`: dibuja dentro de `viewport` (px CSS, origen **arriba** a la izquierda). La capa
  fija su `setViewport` y su `setScissor` (Three cuenta la `y` desde abajo: `y = altoDelLienzo − vp.y − vp.height`),
  puede limpiar **solo la profundidad** dentro de su recuadro (`clearDepth()` con el scissor activo) y nunca el
  color. Al terminar **restaura todo lo que cambie**, también si el fotograma falla (`try/finally`): viewport,
  scissor y scissor test, `toneMapping`, `toneMappingExposure`, `clearColor`/`clearAlpha` y el render target.
- Si compila con un tone mapping propio, lo fija solo alrededor de la llamada síncrona a `compileAsync` (la clave
  del programa lo incluye; si no, recompila al aparecer) y lo restaura enseguida.
- `resize(width, height, pixelRatio)`: solo su cámara y sus uniformes (tamaño del recuadro y densidad del lienzo compartido).
- Sin listeners globales (`pointermove`, `focus`, `blur`, `visibilitychange`): en la capa todo llega del anfitrión.
  - Mirada: `lookAt(x, y)` en −1..1 respecto al centro del avatar, con la `y` positiva hacia abajo.
  - Contexto: `notify('focus' | 'blur' | 'userTyping')`.
  - Estado, voz, movimiento reducido y tema: `setState`, `setAudioLevel` (0..1, ~30-60 Hz), `setReducedMotion`
    y `setTheme`.
- `transparent: true`: sin fondo propio y con alfa premultiplicado. Lo que se salga del recuadro se recorta.

En `createAvatar` (lienzo propio), el envoltorio sí es dueño del renderer: crea el bucle, lo para con
`document.hidden`, limpia el lienzo en cada fotograma y llama a la capa con el lienzo completo. Escucha el ratón
para la mirada y los clics (salvo que se haya llamado a `lookAt`) y no escucha `focus`/`blur`, que avisa el anfitrión.

## Anfitriones

- **Drakter**: `AdaptiveCharacter.tsx` → `ThreeCharacter.tsx` (lienzo propio, tema de la app y SVG de respaldo);
  cambiar de avatar monta uno nuevo y libera el anterior.
- **Ajustes**: `settings/AvatarSection.tsx` (miniaturas y vista previa en vivo).
- **Jarvis**: `jarvis/stage/layers/avatar.ts`. `createAvatarStageLayer({ load: entry.loadLayer, viewport, theme? })`
  es un `StageLayer` que pasa el puntero del Stage a `lookAt` y sincroniza `reducedMotion`, y expone `controls`,
  que se conectan con `useAvatarWiring(controls, state)` (`wiring.ts`): estado, voz real, foco y blur, y escritura.
- **Voz y herramienta**: `avatarIds()` para validar y `findAvatarByAlias(texto)` para resolver lo que se dice.
