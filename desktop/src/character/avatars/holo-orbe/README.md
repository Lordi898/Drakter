# Holo-Orbe (avatar 3D holográfico)

Busto holográfico de filamentos que nace de un orbe, pasa a rostro y vuelve al orbe al pensar. Hecho en
Three.js 0.180 por la ronda de avatares holográficos (sesión drakter-96, versión v2). Todo es procedural: la escultura
es un campo de distancias (`bust.ts`) que se teje en filamentos por tandas al arrancar. Sin modelos, texturas
ni fuentes de terceros (las fuentes del panel de pruebas original no se portan).

- `layer.ts`: `createHoloOrbeLayer(renderer, opts)`, el núcleo, como capa de un renderer ajeno (`AvatarLayer`).
  Teje 8 ms por fotograma dentro de `render` hasta terminar.
- `index.ts`: `createAvatar(canvas, opts)`, envoltorio con renderer, bucle (30 fps), pausa con `document.hidden`
  y la entrada de ratón del original (mirada, tacto de los filamentos, viento, arrastre para girar y clics por zona).
- `render.ts`: escena y shaders (`createScene(renderer)`); `brain.ts`: estados, expresiones y gestos; `bust.ts`: escultura y tejido.
- Tema: en claro dibuja en tinta de cobalto (mezcla normal); en oscuro, luz aditiva (`setTheme`).

Cambios respecto al prototipo: la escena recibe el renderer en vez de crearlo (sin `setSize`, `setPixelRatio`,
`dispose` ni `forceContextLoss` del renderer, y sin dibujar dentro de `resize`), y el fondo propio usa
`uOrigin` para funcionar en un recuadro de un lienzo compartido. `brain.ts` y `bust.ts` van sin cambios.
