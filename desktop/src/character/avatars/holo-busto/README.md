# Holo-busto (avatar 3D)

Busto de caballero de 55-60 años como holograma de cristal de luz, en Three.js 0.180 (concurso de avatares 3D,
sesión drakter-93). Todo es código propio: la malla se esculpe con SDF en `sculpt.ts`; no hay modelos, texturas ni
fuentes de terceros.

- `register.ts`: ficha (`holo-busto`, alias de voz «busto») y cargadores para `../registry.ts`, sin importar Three.
  `thumbnail.webp`: miniatura de 192 px con el escenario propio en tema oscuro.
- `layer.ts`: `createHoloBustoLayer(renderer, opts)`, el núcleo, como capa de un renderer ajeno (`AvatarLayer`, Stage
  de Jarvis). No toca `setSize`/`setPixelRatio`/`setClearColor` ni el bucle; compila con `renderer.compileAsync`.
- `index.ts`: `createAvatar(canvas, opts)`, envoltorio con renderer, bucle (30 fps, temporizador antes del rAF) y ratón.
- Temas: `theme: 'dark'` (luz que se suma, `CustomBlending` ONE/ONE) o `'light'` (tinta de cobalto premultiplicada,
  ONE/ONE_MINUS_SRC_ALPHA), elegidos en `outc()` de `mat.ts`. `setTheme(theme, transparent?)` los cambia en caliente (el anfitrión pasa el tema real de la app).
  `transparent: true` oculta el escenario propio (halo y haz del proyector).
- `mat.ts`: uniformes y materiales **por instancia** (`makeKit()`), para que dos avatares a la vez no se pisen.
- `brain.ts`: estados, expresiones, visemas y gestos. `scene.ts`: rig y escena. `fx.ts`: motas. `geos.ts`: desempaqueta
  la malla horneada a trozos.
- `holo-busto-geo.json`: la malla de `sculpt.ts` horneada (posiciones cuantizadas, base64). Se regenera con
  `tools/bake.mjs` del prototipo (`~/.local/share/drakter/research/avatar3d/holo-busto`); sin él, `geos.ts` esculpe en
  caliente (15-25 s).

Copiado del prototipo sin cambios de lógica, salvo la separación capa/envoltorio y los materiales por instancia.
