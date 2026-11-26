# Ascuario (avatar 3D)

Dragón procedural en Three.js 0.180, finalista del concurso de avatares 3D (ronda 2, sesión drakter-93).
Todo es código propio: la malla se esculpe con SDF en `sculpt.ts`; no hay modelos, texturas ni fuentes de terceros.

- `layer.ts`: `createAscuarioLayer(renderer, opts)`, el núcleo, como capa de un renderer ajeno (`AvatarLayer`, Stage de Jarvis).
- `index.ts`: `createAvatar(canvas, opts)`, envoltorio de la capa con renderer, bucle y ratón propios (API común, ver `../types.ts` y `../README.md`).
- `brain.ts`: estados, expresiones, gestos, mirada y boca. `scene.ts`, `mat.ts`, `fx.ts`: escena, shaders y partículas.
- `ascuario-geo.json`: la malla de `sculpt.ts` ya horneada (posiciones cuantizadas, base64) para no esculpir al
  arrancar. Se regenera con `tools/bake.mjs` del prototipo; si falta, `geos.ts` esculpe en caliente.

Copiado del prototipo sin cambios de lógica, salvo la separación capa/envoltorio. Se enchufa a través de `../registry.ts`.
