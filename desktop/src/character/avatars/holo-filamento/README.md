# Holo-Filamento (avatar 3D)

Busto tejido con miles de hebras de luz azul sobre un busto sólido oscuro, en Three.js 0.180 (concurso de avatares 3D, sesión drakter-91). Tres draw calls más el fondo; toda la animación va en el vertex shader.

- `layer.ts`: `createHoloFilamentoLayer(renderer, opts)`, el núcleo, como capa de un renderer ajeno (`AvatarLayer`). El tejido (`bust.ts`, `createWeaver`) sigue por tandas de 12 ms dentro de `render()`; los shaders se compilan antes con `compileAsync`.
- `index.ts`: `createAvatar(canvas, opts)`, envoltorio con renderer propio, bucle de 30 fps con limitador por calendario, ratón (mirada, tacto, arrastre para girar, clic).
- `brain.ts`, `bust.ts`, `render.ts`: comportamiento, geometría/tejido y shaders.

## Respecto al prototipo
- `surface` / `setSurface` pasan a `theme` / `setTheme` (`'dark' | 'light'`). Con `transparent` y tema claro, lo que flota fuera del busto se dibuja como tinta cobalto (`uInk`); el busto es opaco y oscuro y se lee igual.
- El renderer ya no se crea dentro de `render.ts`: lo pone el anfitrión. El fondo (`BG_FRAG`) resta el origen del recuadro (`uOrg`) a `gl_FragCoord`, para que el halo quede en su sitio dentro de un viewport del Stage.
- `dispose()` ya no llama a `forceContextLoss()` ni a `gl.dispose()`: el contexto es del anfitrión (el envoltorio hace `gl.dispose()` solo en su lienzo propio).
