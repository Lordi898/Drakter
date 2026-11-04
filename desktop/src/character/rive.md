# Enchufar el .riv

1. Crear `character/RiveCharacter.tsx` que exporte un componente con las mismas props (`CharacterRendererProps`: `state`, `size`) y use el runtime de Rive (dependencia a añadir en `package.json` por quien lo gestione).
2. En `character/plug.ts`, cambiar la única línea: `characterRenderer = RiveCharacter` (en lugar de `SvgCharacter`). `CharacterSlot` y el resto de la app no cambian; `EmptyFrame` sigue de respaldo si vale `null`.
3. Máquina de estados del `.riv`:
   - Entrada `state` (numérica, 0..8) en el orden de `CHARACTER_STATES` en `types.ts`: idle, listening, thinking, speaking, executing, success, error, interrupted, offline.
   - Una entrada numérica por cada clave de `PARAMS` en `rig.ts` (mismo nombre y rango): eyeOpen, lidBend, pupil, gazeX, gazeY, browAngleL/R, browRaiseL/R, mouthOpen, mouthCurve, mouthWidth, mouthX, fang, headTilt, headY, headScale, finL/R, ember, emberHue, crackle, sparks, smoke, flame, sat, value, breath, breathRate, blink, talk, scan.
   - Cada bloque de `STATES` pasa a un estado de la máquina; `rate` a la duración de la transición; `settle` a una animación de entrada.
4. Voz: `mouthOpen` debe venir de la intensidad del audio vía `CharacterSink.setMouth(level 0..1)` (ver `receiver.ts`); expresiones vía `setExpression` (lista cerrada `KNOWN_EXPRESSIONS`).
5. Borrar `rig.ts` y `SvgCharacter.tsx` cuando el `.riv` esté validado.
