# Holo-Contorno (avatar 3D por defecto)

Drakter como holograma de contornos, en Three.js 0.180 y procedural: la cabeza y el busto son SDF analíticos
(`sculpt.ts`). No hay modelos, texturas ni fuentes de terceros. Viene del prototipo v2 (sesión drakter-92).

- `layer.ts`: `createHoloLayer(renderer, opts)`, el núcleo, como capa de un renderer ajeno (`AvatarLayer`, Stage de
  Jarvis). Monta la escultura en tareas troceadas y después llama a `compileAsync`, así que nunca hace `render()`
  antes. Acepta `theme: 'dark' | 'light'` y `setTheme()` en caliente (solo cambia los factores de mezcla y un
  uniforme, sin recompilar), y una `HoloVariant` para las variantes (ver `../holo-hilo/`).
- `index.ts`: `createHoloAvatar(canvas, opts)`, el envoltorio con lienzo propio, sin MSAA, con un limitador de
  30 fps por calendario y el ratón.
- `holo.ts`: los materiales. Incluye los contornos, la prepasada de profundidad, las cintas `LineBatch` en espacio
  de pantalla (`DoubleSide`), los brillos, el polvo animado en la GPU y el fondo. Los uniformes van **por
  instancia** (`holoUniforms()`).
- `features.ts`: los rasgos y la barba. `deform.ts`: la deformación de la piel en GLSL y su gemela en JS, que
  deben coincidir. `hair.ts`: el pelo. `brain.ts` y `voice.ts`: el comportamiento y los visemas.

Los shaders escriben valores de pantalla: la capa dibuja con `NoToneMapping` y `LinearSRGBColorSpace`, y
restaura el estado del renderer al acabar.
