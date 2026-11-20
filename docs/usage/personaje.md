# Personaje: boca sincronizada y archivo Rive

Drakter dibuja su personaje con un SVG provisional. Si existe tu archivo `.riv`, lo usa en su lugar sin tocar nada más.

## Boca sincronizada

Mientras Drakter habla (estado `speaking`), la boca sigue el volumen real del audio que suena: se mide en la pista de voz que recibe la aplicación, unas 30 veces por segundo, con un umbral de silencio y un suavizado. Si no suena nada, la boca no se mueve. Cuando no está hablando no se mide nada.

Con **Reducir movimiento** activado en Ajustes (o en el sistema operativo), la boca no sigue el audio y queda en la pose fija de siempre.

## Dónde poner tu `.riv`

- Ruta por defecto: `~/.local/share/drakter/character/drakter.riv` (respeta `XDG_DATA_HOME`).
- Otra ruta: variable de entorno `DRAKTER_CHARACTER_RIV` con la ruta del archivo, antes de abrir la aplicación.
- Se lee al abrir la aplicación; para cambiar de archivo, reinicia Drakter.
- Si el archivo no existe, no es un `.riv` válido o no tiene la state machine descrita abajo, se usa el SVG sin mostrar errores.
- En modo desarrollo (`npm run dev`) el archivo no se sirve y se ve siempre el SVG; pruébalo con la aplicación compilada (`npm run start`).

## Cómo diseñarlo en el editor de Rive

1. **Artboard cuadrado de 360 × 360**. Se dibuja escalado dentro de un cuadrado (120 px compacto, hasta 360 px expandido), con fondo transparente.
2. **Una state machine llamada exactamente `Drakter`.**
3. Con estos inputs (los nombres distinguen mayúsculas; los que falten se ignoran):

| Input | Tipo | Valores |
|---|---|---|
| `state` | Number | 0 `idle`, 1 `listening`, 2 `thinking`, 3 `speaking`, 4 `executing`, 5 `success`, 6 `error`, 7 `interrupted`, 8 `offline` |
| `mouthOpen` | Number | 0 (cerrada) a 1 (abierta del todo). Solo se mueve en `speaking`, con el nivel real del audio; en el resto de estados vale 0 |

4. Transiciones entre los 9 estados según el valor de `state` (por ejemplo, condiciones `state == 3`). Las expresiones (`happy`, `curious`…) de momento no se envían al `.riv`.
5. Para la boca, usa `mouthOpen` como entrada de un blend o de una animación 1D de la boca. Suaviza dentro de Rive si quieres más inercia; la aplicación ya filtra el nivel.
6. Exporta como `.riv` (runtime `@rive-app/canvas` 2.53.0) y copia el archivo a la ruta de arriba.

Rive marca los inputs de state machine como en desuso a favor de los view models (data binding); se usan inputs porque son lo más sencillo de diseñar y siguen funcionando. Migrar sería un cambio pequeño en `RiveCharacter.tsx`.

## Para quien toca el código

- `desktop/src/voice/outputLevel.ts`: mide el nivel con un `AnalyserNode` sobre la pista remota de WebRTC (solo mientras hay suscriptores).
- `desktop/src/character/useMouthLevel.ts`: suscripción compartida por ambos renderers.
- `desktop/src/character/RiveCharacter.tsx` y `AdaptiveCharacter.tsx`: carga del `.riv` y respaldo al SVG.
- `desktop/electron/main/rendererProtocol.ts`: sirve el `.riv` del usuario por `app://drakter/__character/drakter.riv` (solo ese archivo y solo con extensión `.riv`).
