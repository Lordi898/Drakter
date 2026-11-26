# Holo-Hilo (avatar 3D)

Es Holo-Contorno con una trama de filamentos encima (prototipo de la sesión drakter-91). No duplica nada: reutiliza
el rig de `../holo-contorno/` (escultura, cara, pelo, barba, cerebro, capa y envoltorio) mediante una `HoloVariant`.

- `threads.ts`: la trama. Son miles de hebras sobre la escultura que siguen líneas de flujo anatómicas. En la cara
  usan la misma deformación que la piel. Sus uniformes van por instancia (`threadUniforms()`).
- `variant.ts`: los modismos del hilo, que mueven la trama según el estado: ovillo al pensar, lanzadera al
  ejecutar, atar cabos en el éxito, perder el hilo en el error y deshilachado sin conexión. Las curvas de nivel
  quedan como un eco tenue (`lineK`).
- `entry.ts`: `create`/`createLayer` de Holo-Contorno con `variant: holoHilo`.
