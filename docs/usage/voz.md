# Usar la voz

Hablas a Drakter y te contesta en voz alta. El reconocimiento de voz y la activación son locales; la voz de Drakter la genera Fish Audio (con red) o Kokoro (local). Instalación previa: [Instalar la voz](../installation/voz.md). Voces y perfiles: [Perfiles de voz](voces.md).

## Cómo funciona en una línea

Drakter tiene dos modos. En **reposo** solo escucha la palabra de activación y no transcribe nada. En **conversación** te transcribe y contesta. Cuando acabas, vuelve solo a reposo.

## Activar

- **Super+J.** Es un atajo de GNOME que ejecuta `scripts/drakter activate`. Se instala una vez con `scripts/install-shortcut.sh install` (ver la guía de instalación). También puedes ejecutar `scripts/drakter activate` a mano.
- **«Hey Jarvis».** Di «Hey Jarvis» y, si quieres, la orden en la misma frase: «Hey Jarvis, ¿qué tengo hoy?». Se puede apagar en Ajustes → Voz («Activar con la palabra Jarvis»).
- **Bandeja del sistema.** Menú del icono de Drakter → «Activar voz».

La ventana puede estar oculta en la bandeja: la escucha sigue. Con la app cerrada no hay escucha.

## Conversación y vuelta a reposo

Dentro de la conversación no hace falta repetir «Jarvis». Vuelve a reposo cuando:

- pasa un rato sin que hables tras la respuesta (Drakter te pregunta antes si sigues ahí);
- dices **«descansa»**, «deja de escuchar», «eso es todo» o similares;
- te despides: «adiós», «hasta luego», «buenas noches»…

## Interrumpir

- **«Para»**, «calla», «basta», «silencio»: corta solo la voz. Drakter sigue en la conversación.
- **Hablar encima** (barge-in): al detectar voz mientras habla, Drakter baja el volumen y, si lo que dices son varias palabras que no son eco, se calla y te escucha. Con una sola palabra suelta no te corta.
- Los **asentimientos** («aja», «mm», «vale», «claro») se ignoran: no interrumpen ni cuentan como respuesta.
- **Reanudar:** di «siga» o «como le decía». Drakter sabe lo último que llegaste a oír y lo que quedó sin decir, y retoma desde ahí.

## Altavoz y micrófono

- **Icono de altavoz** (junto al cuadro del chat): silencia la voz de Drakter. El chat sigue funcionando por escrito y el micrófono no se cierra.
- **Punto junto al altavoz:** estado del micrófono. `off` (apagado), `standby` (esperando la palabra de activación) o `live` (escuchando).
- **Bandeja → «Silenciar micrófono» / «Activar micrófono»:** cierra o reabre la captura de verdad, sin reiniciar nada. Con el micrófono cerrado ni el atajo ni «Hey Jarvis» funcionan hasta que lo actives.
- Con la ventana oculta, el micrófono sigue escuchando la palabra de activación.

## Elegir micrófono y salida

En **Ajustes → Voz**:

- **Micrófono:** la entrada que usa Drakter. «Predeterminado del sistema» sigue al de GNOME.
- **Salida de audio:** por dónde habla Drakter, aunque el sistema tenga otra salida predeterminada. **Probar** reproduce un tono por ella.
- Si eliges micrófono y salida de dispositivos distintos, Ajustes te avisa: puede que te hable por unos auriculares y te escuche por otro micrófono.

Se guardan en las preferencias del escritorio y no cambian nada del sistema.

## Auriculares o altavoces

- **Auriculares o headset (recomendado):** no hay eco, así que hablar encima funciona siempre y Drakter no se corta solo. Elige el headset tanto en Micrófono como en Salida.
- **Altavoces:** funciona, con cancelación de eco, pero a volumen alto Drakter puede oírse a sí mismo y cortarse. Baja el volumen o aleja el micrófono.

## Voces

La voz la elige el perfil activo de `~/.config/drakter/voces.toml` (por defecto `natural`). Puedes pedírselo en el chat o por voz: «cambia tu voz a la neutral». Cómo crear perfiles y poner los IDs de Fish: [Perfiles de voz](voces.md).

## Confirmaciones: nunca por voz

Las acciones destructivas o masivas se confirman **solo en pantalla**. Decir «sí» no vale. Drakter te avisa («Necesito su confirmación en pantalla») y trae la ventana al frente.

## Trabajos en segundo plano

Si le pides algo largo, Drakter puede hacerlo en segundo plano («Lo hago en segundo plano, señor»). Los trabajos salen en el panel de contexto con su estado, y puedes preguntar por ellos o cancelarlos. Solo hay un trabajo a la vez: si está ocupado, te lo dice. Al terminar recibes una notificación y un aviso hablado («he terminado el trabajo»); el resumen se lo cuenta al siguiente turno. Si el trabajo necesita confirmar algo, la confirmación aparece en pantalla.

## Frases fijas: genera tu caché

Los avisos cortos («Entendido», «Un momento», «Sigo con ello»…) suenan desde una caché de audio para responder al instante. La caché inicial se generó sin tu perfil de voz. Regenérala **con tu perfil, antes del 30-11-2026**, desde la raíz del repositorio:

```bash
~/.local/share/drakter/venvs/voice/bin/python -m voice phrases
```

Opciones: `--profile <nombre>`, `--only fish|kokoro`, `--force` (regenera aunque exista). Necesita `FISH_API_KEY` y red para la parte de Fish; la de Kokoro es local. Pasada la fecha, Fish ya no se usa y solo se necesita la de Kokoro.

## Reconocimiento de voz: nube o local

- Con `DEEPGRAM_API_KEY` en `~/.config/drakter/.env`, Drakter usa Deepgram Nova-3 (región UE, sin programa de mejora del modelo); si no, con `GROQ_API_KEY`, Groq Whisper large-v3-turbo; si no, Moonshine local. Las dos nubes conocen «Drakter», «Jarvis», «Imanol» y «Magaña» (`stt_keyterms` en `voice.toml` para cambiarlos). Fuerza uno con `DRAKTER_VOICE_STT=deepgram|groq|moonshine`.
- Si la nube falla (sin red, clave mala o cuota), pasa a Moonshine con un único aviso y sigue así hasta reiniciar la voz.
- Si te entiende mal, activa el volcado con `DRAKTER_VOICE_DUMP_AUDIO=1` (en `~/.config/drakter/.env`) y reinicia: guarda el audio de cada turno tal como lo oye el reconocedor en `~/.local/share/drakter/voice/dumps/`, con sus niveles al lado, y lo borra solo a las 24 h.

## Sin red y después del 30-11-2026

- **Sin red:** el WebRTC va por `127.0.0.1`, así que la conexión entre la app y el proceso de voz sigue funcionando. Lo que cae es Fish: Drakter avisa **una sola vez** («paso a mi voz local») y sigue con Kokoro. Con STT en la nube, el reconocimiento pasa a Moonshine local; «Hey Jarvis» no necesita red. El agente (Claude) sí la necesita para responder.
- **Después del 30-11-2026:** el modelo gratuito `s2.1-pro-free` de Fish deja de usarse, salvo que pongas `allow_paid = true` en el `voces.toml` (con cobro). Desde esa fecha todo habla con Kokoro, sin aviso de cambio.

## Privacidad

El audio y las transcripciones **no se guardan** en ningún sitio, salvo que actives el volcado de diagnóstico (`DRAKTER_VOICE_DUMP_AUDIO=1`, se borra a las 24 h). Con STT en la nube, el audio de cada turno se envía a Deepgram o a Groq para transcribirlo. Solo se guarda `~/.local/share/drakter/voice/metrics.jsonl`, con tiempos y contadores, sin texto. Lo que dices llega al agente como un mensaje del chat y queda en el historial del chat igual que si lo hubieras escrito. Lo que se envía a Fish para sintetizar es el texto de la respuesta, no tu voz.

## Qué tienes que probar tú

1. Super+J y «Hey Jarvis, ¿qué hora es?» con altavoces (no auriculares): comprueba que no se interrumpe con su propio eco.
2. «Para» a mitad de respuesta y «siga» después.
3. Cortar la red y comprobar el aviso único y el paso a Kokoro.
4. Latencia percibida de la primera palabra: primer audio (normalmente un acuse) 2,36-2,88 s tras callar; primer audio de la respuesta en sí, depende de Haiku (primer delta típico 1,8-4,2 s); TTFA de Fish 0,71-0,96 s y de Kokoro 0,72 s (medido en la máquina de desarrollo).

## Problemas frecuentes

Tabla completa (micrófono silenciado, sin red, eco…): [Solución de problemas](problemas.md#la-voz-no-funciona).

- **No pasa nada con Super+J:** ejecuta `scripts/drakter activate` a mano; si funciona, repite `scripts/install-shortcut.sh install`.
- **No conecta sin red:** la app debe arrancarse con `scripts/drakter` o `scripts/drakter-local.sh`, que añaden el switch de WebRTC por loopback.
- **Mensaje de error de voz o punto de micrófono en `off`:** abre la bandeja y activa el micrófono; si persiste, ejecuta `python -m voice check` ([instalación](../installation/voz.md)).
