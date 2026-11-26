# El Relojero v2 (avatar 3D)

Autómata de relojería procedural en Three.js 0.180 (concurso de avatares 3D, sesión drakter-92). Todo es código propio: sin modelos ni texturas.

- `layer.ts`: `createRelojeroLayer(renderer, opts)`, el núcleo, como capa de un renderer ajeno (`AvatarLayer`, Stage de Jarvis). Monta la escena por etapas (una tarea cada una), compila con `compileAsync` y precalienta la GPU con el scissor a cero (no pinta en el lienzo compartido).
- `index.ts`: `createAvatar(canvas, opts)`, envoltorio con renderer propio, bucle de 30 fps con limitador por calendario y ratón.
- `brain.ts`, `voice.ts`: estados, expresiones, mirada y visemas. `geo.ts`, `lux.ts`, `mats.ts`, `face.ts`: geometría, materiales «lux» con entorno analítico y deformación de la cara.

## Respecto al prototipo
- `transparent`: sin fondo propio (`backdrop` oculto) y con alfa premultiplicado. La luz aditiva (cristal, destellos) usa mezcla `One / OneMinusSrcAlpha` con alfa 0, que suma igual en lienzos opacos y transparentes.
- Tema (`theme` / `setTheme`): el cuerpo es opaco y se lee igual sobre claro y oscuro; en tema claro solo baja a la mitad la ganancia de los destellos aditivos (`uGain`).
- Capa: sin listeners globales; `lookAt`, `notify` y `setReducedMotion` llegan del anfitrión. `dispose()` libera lo suyo, nunca el renderer.
