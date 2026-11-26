# Filamento v2, el dorado (avatar 3D)

Busto tejido con hebras de luz ámbar, en Three.js 0.180 (concurso de avatares 3D, sesión drakter-91). Tres draw calls (fondo, hebras, polvo); toda la animación va en el vertex shader.

- `layer.ts`: `createFilamentoLayer(renderer, opts)`, el núcleo, como capa de un renderer ajeno (`AvatarLayer`). El tejido sigue por tandas de 8 ms dentro de `render()`.
- `index.ts`: `createAvatar(canvas, opts)`, envoltorio con renderer propio, bucle de 30 fps con limitador por calendario y ratón.
- `brain.ts`, `bust.ts`, `render.ts`: comportamiento, tejido y shaders.

## Respecto al prototipo
- `transparent`: sin fondo y con alfa premultiplicado. Los fragmentos de luz escriben alfa 0 y la mezcla es `One / OneMinusSrcAlpha`, que suma igual que la aditiva anterior (`One / One`).
- Tema (`theme` / `setTheme`), **decisión de diseño**: es luz aditiva pura, sin malla sólida ni profundidad, así que sobre fondo claro desaparece. En tema claro (con `transparent`) pone su propio fondo oscuro como una **tarjeta de esquinas redondeadas** (`uCard`, borde suave de 1 px) y las hebras se suman encima. En tema oscuro flota sin fondo. Se descartó la tinta (como Holo-Hilo): cambia por completo el carácter ámbar del avatar.
- El fondo resta el origen del recuadro (`uOrg`) a `gl_FragCoord` (halo y tarjeta correctos en un viewport del Stage).
- `dispose()` ya no llama a `forceContextLoss()` ni a `gl.dispose()`: el contexto es del anfitrión.
