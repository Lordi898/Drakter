# Chat y personaje

> **Estado:** integrado en `drakter/integracion` (`2e05ba6`): chat, personaje SVG, diálogo nativo de aprobación, API `chat` y runtime de Hermes (`backend/app/integrations/hermes/`). Sin clave de API solo se ha probado con el LLM de pruebas, y en la pasada de cierre la sesión de chat respondía `agent_unavailable`. Las notas «Pendiente» del cuerpo se escribieron sobre `drakter/build` (`2da8bef`) y alguna puede estar ya resuelta. NO COMPROBADO en la app real (ver «Estado de la integración» en [README](README.md)).

Hablas con Drakter por escrito en la barra de chat de la ventana y ves su estado en el personaje de la pantalla de inicio. Esta guía explica cómo conversar, cómo detenerlo y qué significa cada estado.

## Conversar

1. Abre la aplicación. La barra de chat está en la parte inferior de la ventana (`ChatDock`).
2. Escribe en la caja "Escribe un mensaje".
3. Pulsa Enter para enviar. Shift+Enter hace un salto de línea.
4. La respuesta aparece en la conversación mientras se genera, con un cursor parpadeante.
5. Si Drakter usa una herramienta, verás una línea con su nombre y el resultado: "en curso", "hecho" o "ha fallado".

Límites del código:

- Máximo 8000 caracteres por mensaje; si te pasas, sale un aviso y no se envía.
- Solo puede haber una respuesta en curso. Mientras tanto no puedes enviar otro mensaje.
- Sin conexión con el backend la caja se desactiva y se muestra "Conectando con Drakter…", "Reconectando con Drakter…" o "Drakter no está conectado ahora…".

## Interrumpir

Mientras Drakter responde, el botón "Enviar" pasa a ser "Detener". Púlsalo y la respuesta se corta. Lo que ya se había escrito se queda en pantalla con el aviso "Esta respuesta se ha cortado y puede estar incompleta."

Si la respuesta falla, aparece el motivo y un botón "Reintentar" (salvo que el backend indique que reintentar no tiene sentido). Reintentar un mensaje tuyo no lo duplica si el servidor ya lo había recibido.

## Estados del personaje

El personaje está en la pantalla de inicio (`HomePage`). Los nueve estados salen de `desktop/src/character/types.ts`. El texto que dice Drakter junto al personaje sale de `HomePage.tsx`.

| Estado | Qué significa | Texto en pantalla |
|---|---|---|
| `idle` | En reposo, sin nada en curso | "Estoy aquí. Dime qué necesitas." |
| `listening` | Te escucha | "Te estoy escuchando." |
| `thinking` | Está pensando la respuesta | "Estoy pensando." |
| `speaking` | Está respondiendo | "Te estoy respondiendo." |
| `executing` | Ejecuta una herramienta | "Estoy trabajando en ello." |
| `success` | Terminó una acción bien | "Ya lo he hecho." |
| `error` | No pudo terminar | "No he podido terminarlo." |
| `interrupted` | Se detuvo antes de acabar | "Me he detenido." |
| `offline` | Sin enlace con el backend | "Todavía no estoy conectado." |

`offline` lo decide la propia interfaz cuando el enlace con el backend no está abierto. El resto los envía el backend con el evento `agent.status_changed`; en el código solo lo emite el runtime de `drakter/agente-hermes` (`backend/app/integrations/hermes/runtime.py`), no `drakter/build`. La interfaz no inventa estados: al abrir el enlace lee el estado real con `GET /api/v1/agent/status`.

## El personaje es provisional

Es un dibujo SVG (`SvgCharacter.tsx`) con los nueve estados. No es el personaje animado final: el archivo `.riv` de Rive se diseña aparte y todavía no existe. Cuando exista se enchufa cambiando una línea de `desktop/src/character/plug.ts`, sin tocar el resto (pasos en `desktop/src/character/rive.md`). Hasta entonces el aspecto cambiará.

El personaje también acepta expresiones (`neutral`, `happy`, `curious`, `concerned`, `surprised`, `focused`); cualquier otra se ignora.

## Confirmaciones del agente

Si Drakter va a hacer algo destructivo o masivo, no lo ejecuta sin tu permiso. En la conversación aparece un aviso "Drakter necesita tu confirmación" con:

- el resumen de la acción,
- cuántos elementos afecta, si se sabe,
- un contador con el tiempo restante,
- un botón "Revisar".

"Revisar" abre un diálogo nativo del sistema (`approvals.ts`, título «Confirmar acción») con el resumen, «Elementos afectados» y, si se conoce, el «Riesgo», y dos botones: «Cancelar» (por defecto) y «Aprobar». Ahí decides. En el chat no hay botones para aprobar ni rechazar, ni para aprobar en bloque ni para recordar decisiones: es a propósito. Si el tiempo se agota, el aviso desaparece y no se ejecuta nada. Mensajes posibles tras revisar: "Los elementos han cambiado; la acción no se ha ejecutado." o "No se ha podido completar la decisión. Comprueba el estado antes de repetir."

Escribir "sí, confirmo" en el chat no sustituye a la confirmación.

## Problemas frecuentes

- "Drakter sigue respondiendo. Espera a que termine o cancela el turno.": hay una respuesta en curso. Pulsa "Detener".
- "El agente no está disponible en este momento.": el agente no responde; revisa el estado y vuelve a probar.
- "El proveedor del modelo rechazó las credenciales.": problema de clave API; ver [clave-api](../installation/clave-api.md).
- "El servicio local de Drakter no está disponible.": el backend no está arrancado.

## Pendiente

- **Pendiente:** el micrófono de la pantalla de inicio está desactivado; la voz va en [voz](voz.md).
- **Pendiente:** en `drakter/build` (2da8bef) no hay backend de chat ni de agente: sin las rutas de `drakter/agente-hermes` (integra sin fusionar), el chat no tiene a quién hablar y el personaje queda en `offline`. `almacen-relaciones`, `chat-personaje` y `agente-hermes` siguen sin ser ancestros de 2da8bef por merge-base, aunque la interfaz de chat sí llegó por otra vía.
- NO COMPROBADO: ningún paso se ha ejecutado en la app real.
