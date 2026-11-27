# desktop/floating: la página de la ventana flotante (copia de Roamies)

Es la página que carga la ventana flotante de Electron (`app://floating/index.html?look=jarvis`). Sale de
[KenKaiii/Roamies](https://github.com/KenKaiii/Roamies), commit `8f0adaa` (`showcase/`), bajo **AGPL-3.0**. Drakter es
AGPL-3.0-only por esto. El contrato con Electron main está en `docs/floating/CONTRACT.md` §4.3 y §11.

## Qué hay

| Ruta | Origen | Estado |
|---|---|---|
| `roamies/*.js` (18) | `showcase/roamies/` de `8f0adaa` | Copia byte a byte. Solo llevan los parches `// Drakter:` de la tabla de abajo |
| `fonts/*.woff2`, `fonts/OFL-*.txt` | `showcase/onboarding/fonts/` | Idénticos (SIL OFL 1.1, cada fuente con su titular) |
| `index.html` | `showcase/desktop.html` | Adaptado (ver abajo) |
| `boot.js`, `boot-fonts.js` | Los dos `<script>` en línea de `desktop.html` (líneas 49 y 56) | El mismo código pasado a archivo, porque la CSP no admite scripts en línea |
| `bridge.js` | Nuevo (Drakter) | `window.drakterFloat` → globales `ROAMIE_*`, `__TAURI__.core.invoke` y `__roamie*` (§11.2). Atiende además `drakter_dodge{rect}` de main: con el diálogo nativo de confirmación abierto, aparca el avatar en la esquina más lejana con `avatar_pin` de Roamies y al cerrarse lo devuelve a su sitio con `place` (o al pin del usuario) |
| `drakter-voice-out.js` | Nuevo (Drakter) | Sustituye a `Roamie.voiceOut` con la misma API, alimentado por `float:voice` (§11.5) |
| `dev/` | Nuevo (Drakter), **solo desarrollo** | `fake-host.html` + `fake-preload.js` + `fake-panel.js`, y `diff-upstream.sh`. No se empaqueta |

Se omiten `people.js`, `minis.js`, `agent-home.js`, `sidebar.js` y `pen.js`: todos sus usos van con `?.`.

## Cambios respecto a Roamies `8f0adaa` (exigido por la AGPL)

Cada línea cambiada en `roamies/` acaba en un comentario `// Drakter: …`. `dev/diff-upstream.sh <checkout de Roamies>`
lo comprueba (falla si hay una línea cambiada sin marca o una fuente distinta).

Sin cambios: `10-dither.js`, `12-sidekick.js`, `ask-bar.js`, `core.js`, `glass.js`, `ink3d.js`, `jarvis.js`, `sfx.js`,
`voice-out.js` y `world.js`.

| Archivo | Líneas | Cambio |
|---|---|---|
| `host.js` | 96 | `NAMES.jarvis`: `'JARVIS'` → `'Drakter'` (aria-label «Mensaje para Drakter») |
| `host.js` | 97, 554 | «Message for …» → «Mensaje para …» |
| `host.js` | 148, 162 | Aria «Pulsa S para permitir o N para rechazar.» y la tecla **S** en vez de Y |
| `host.js` | 185 | Regex `LISTY`: `…\n\s*(?:sources?\|fuentes?)\s*:/i` |
| `host.js` | 193, 208, 320, 329, 330, 343, 384, 420, 477 | «Leyendo …», «Buscando en la web», «Trabajando», «Redactándolo», «Te lo enseño», «Desde la web» / «Respuesta», «Escuchando… pulsa otra vez para enviar» / «Escuchando…» |
| `markdown.js` | 78 | Regex de fuentes: `/^\**(?:sources?\|fuentes?)\**\s*:\s*(.*)$/i` |
| `agent.js` | 1019 | Placeholder «Escuchando…» |
| `agent-cards.js` | 42, 76 | «tu petición»; contador de pasos de la tarjeta de manos «N de M» |
| `agent-tools.js` | 12, 22, 43, 74, 99 | Etiquetas por defecto de los chips: «mirando tu pantalla», «captura», «leyendo», «escribiendo», «ejecutando» (`web` queda igual) |
| `agent-panel.js` | 105, 135, 140, 222, 237, 243 | «Fuentes: », «Respuesta desde la web», «Cerrar», «Buscando en la web», «Desde la web», «No he podido terminar» |
| `notch.js` | 223, 808 | Nombre por defecto `'Drakter'` |
| `notch.js` | 781, 784, 788, 825, 833, 836, 843, 846, 872, 873, 877, 895, 905 | «Bien» / «Mal», «Ha estado bien» / «Ha estado mal», «¡Gracias!», «Escuchando», «Respondiendo», «Te lo enseño», «Pensando», «Trabajando», «Algo ha salido mal.», «No he podido terminar», «Hola», «Necesito tu permiso», «S o N» |
| `ink.js` | 548, 553, 554, 555 | «escrito: …», «Copiado al portapapeles», «Abriendo …», «Entregado» |
| `ink.js` | 716 | «FUENTES» |
| `ink.js` | 749, 764, 833, 848, 884, 918, 922, 989, 1027, 1065, 1079, 1227, 1287, 1313, 1437, 1581, 1669, 1759, 1830, 1870 | Títulos por defecto de las tarjetas: respuesta, tema, mapa mental, lista, recorte, fuentes, foto, gráfica, cronología, modelo, molécula, tabla, barras, flujo, matemáticas, figura, mapa, test, tu objetivo |
| `ink.js` | 880, 882 | «+ Añadir» |
| `ink.js` | 980, 1074, 1738 | «no he encontrado imagen», «el 3D no está disponible aquí», «los mapas no están disponibles aquí» |
| `ink.js` | 1291 | `fmtValue`: `toLocaleString('es-ES')` y sufijos `mil M` (≥ 10⁹) y `M` (≥ 10⁶) |
| `ink.js` | 1794, 1795, 1803, 1804, 1825, 1827, 1852 | Test: «N de M», «correctas», «Inténtalo de nuevo», «Correcto.» / «No exactamente: es la X.», «Siguiente» / «Ver puntuación», «Pruébalo» |
| `ink.js` | 1921 | «Borrar todo · n» |
| `ink.js` | 2144 | Recordatorios ocultos: «+N más» |
| `ink.js` | 2124, 2135, 2136, 2137, 2164 | Recordatorios: «hecho», «con retraso …», «Hoy», «Nada para hoy» / «Tu lista aún está vacía», «Más tarde», «recordatorios» |

`index.html` frente a `desktop.html`: `lang="es"`; título `drakter-floating` (regla de casado de la extensión, §4.1); la
CSP de §11.6; las fuentes en `fonts/` y no en `onboarding/fonts/`; aria-label del lienzo «Drakter en el escritorio»;
`bridge.js` delante de todo y `drakter-voice-out.js` detrás de `voice-out.js`; los dos scripts en línea pasan a `boot.js`
y `boot-fonts.js`; y sin `minis`, `agent-home`, `people`, `sidebar` ni `pen`. Están marcados con `<!-- Drakter: -->`.

Sin traducir a propósito: el aria-label de la galería en `core.js:723` y `:727` (solo existe en el modo galería, no en
`bootDesktop`), el nombre de archivo `'card'` de `ink.js:2287` (va a `card_image`, que se ignora en v1) y las letras
`ABCD` del test.

## Probarla sin Electron main

Abre `dev/fake-host.html` en un Chromium o un Electron normal. Lleva un `drakterFloat` falso: contesta a `ui_ready` como
main (§4.2 paso 5), manda el ratón real como `ptr` (o uno simulado con «Puntero»), `__roamieSafe` con una barra de 32 px,
y un clic como `float:click` mientras la página pide `ink_wait`. El panel inyecta los mensajes de §11.4: turno completo,
voz, herramientas, error, avisos, barra de pregunta, Esc, tamaños, un dibujo (anillo, subrayado, flecha y tarjeta) y una
guía con `wait:'click'`. La casilla «Beats con voz» añade `speech_id` y `float:voice` para probar el shim, y «Mostrar
regiones» dibuja lo que la página manda en `set_hit_rects`. La tecla P esconde el panel. Desde fuera:
`__fake.run('dibujo')`, `__fake.panel(false)`.

## Licencia

El código de Roamies y lo que Drakter le añade aquí es AGPL-3.0 (Drakter: AGPL-3.0-only). Las fuentes conservan la SIL
OFL 1.1 (`fonts/OFL-*.txt`). Ver `THIRD_PARTY_NOTICES.md`.
