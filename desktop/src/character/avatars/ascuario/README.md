# Ascuario (avatar 3D)

Dragón procedural en Three.js 0.180, finalista del concurso de avatares 3D (ronda 2, sesión drakter-93).
Todo es código propio: la malla se esculpe con SDF en `sculpt.ts`; no hay modelos, texturas ni fuentes de terceros.

- `index.ts`: `createAvatar(canvas, opts)` con la API común de los finalistas (ver `../types.ts`).
- `brain.ts`: estados, expresiones, gestos, mirada y boca. `scene.ts`, `mat.ts`, `fx.ts`: escena, shaders y partículas.
- `ascuario-geo.json`: la malla de `sculpt.ts` ya horneada (posiciones cuantizadas, base64) para no esculpir al
  arrancar. Se regenera con `tools/bake.mjs` del prototipo; si falta, `geos.ts` esculpe en caliente.

Copiado sin cambios de lógica desde el prototipo; solo se enchufa en la app a través de `../registry.ts`.
