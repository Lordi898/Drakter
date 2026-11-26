# Avatares 3D de Drakter

Cada avatar es un módulo de Three.js **0.180.0** (la misma versión exacta que la app, una sola copia) con
**una sola implementación** y dos formas de montarla:

| Ruta | Quién la usa | Firma (`types.ts`) |
|---|---|---|
| **Capa** de un renderer ajeno | Stage de Jarvis (un único lienzo WebGL) | `CreateAvatarLayer = (renderer, options) => AvatarLayer` |
| **Lienzo propio** | Modo Drakter (`ThreeCharacter`), y Jarvis si el avatar no trae capa | `CreateAvatar = (canvas, options) => Avatar3D` |

La capa es el núcleo; `createAvatar` es un envoltorio que pone alrededor un `WebGLRenderer`, un bucle
`requestAnimationFrame` y la entrada de ratón. Ascuario (`ascuario/layer.ts` + `ascuario/index.ts`) es el
ejemplo de referencia.

## Cómo enchufar un avatar nuevo

1. Carpeta `avatars/<nombre>/` con todo su código (procedural, sin assets de terceros). Nada específico de
   un avatar fuera de su carpeta.
2. `avatars/<nombre>/entry.ts` exporta las dos funciones:
   ```ts
   export const create: CreateAvatar = (canvas, options) => …
   export const createLayer: CreateAvatarLayer = (renderer, options) => …
   ```
   Los assets (p. ej. una malla horneada) se importan con `?url` y se pasan aquí.
3. Una entrada en `registry.ts`:
   ```ts
   holo: {
     load: () => import('./holo/entry').then((m) => m.create),
     loadLayer: () => import('./holo/entry').then((m) => m.createLayer),
     transparent: true // sabe dibujarse sin fondo propio
   }
   ```
4. Activarlo: `ACTIVE_AVATAR = 'holo'`. Con `null` no hay avatar 3D y Three no se descarga.

Si falta `loadLayer`, Jarvis monta `create` en un segundo lienzo (dos contextos WebGL, sin composición en profundidad).

## Reglas de la capa (`AvatarLayer`)

- **No es dueña del renderer ni del bucle.** Nunca llama a `setSize`, `setPixelRatio`, `setAnimationLoop`
  ni a `dispose()` del renderer, ni registra `requestAnimationFrame`.
- `render(dt, viewport)`: dibuja dentro de `viewport` (px CSS, origen **arriba** a la izquierda). La capa
  fija su `setViewport` y su `setScissor` (Three cuenta la `y` desde abajo: `y = altoDelLienzo − vp.y − vp.height`),
  puede limpiar **solo la profundidad** dentro de su recuadro (`clearDepth()` con el scissor activo) y nunca el
  color. Al terminar **restaura todo lo que cambie**: viewport, scissor y scissor test, `toneMapping`,
  `toneMappingExposure`, `clearColor`/`clearAlpha` y el render target.
- `resize(width, height, pixelRatio)`: solo su cámara y sus uniformes (tamaño del recuadro y densidad del lienzo compartido).
- `ready`: se resuelve con la geometría lista y los shaders compilados (`renderer.compileAsync`); se rechaza si
  la carga falla. Nada de bloqueos de más de 100 ms en el hilo principal.
- Sin listeners globales (`pointermove`, `focus`, `blur`, `visibilitychange`): en la capa todo llega del anfitrión.
  - Mirada: `lookAt(x, y)` en −1..1 respecto al centro del avatar, con la `y` positiva hacia abajo.
  - Contexto: `notify('focus' | 'blur' | 'userTyping')`.
  - Estado, voz y movimiento reducido: `setState`, `setAudioLevel` (0..1, ~30-60 Hz) y `setReducedMotion`.
- `dispose()`: libera geometrías, materiales y texturas propios; nunca el renderer.
- `transparent: true`: sin fondo propio y con alfa premultiplicado. Lo que se salga del recuadro se recorta.

En `createAvatar` (lienzo propio), el envoltorio sí es dueño del renderer. Crea el bucle (30 fps) y lo para con
`document.hidden`. Limpia el lienzo en cada fotograma y llama a la capa con el lienzo completo. Escucha el ratón
para la mirada y los clics, salvo que se haya llamado a `lookAt`, y no escucha `focus`/`blur`, que avisa el anfitrión.

## Anfitriones

- **Drakter**: `ThreeCharacter.tsx` (lienzo propio y respaldo SVG).
- **Jarvis**: `jarvis/stage/layers/avatar.ts`. `createAvatarStageLayer({ load: entry.loadLayer, viewport })` es un
  `StageLayer`. Pasa el puntero del Stage a `lookAt` y sincroniza `reducedMotion`, y expone `controls`, que se
  conectan con `useAvatarWiring(controls, state)` (`wiring.ts`): estado, voz real, foco y blur, y escritura.
