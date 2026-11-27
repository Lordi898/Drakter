# Modo flotante

> **Estado:** integrado en `main` (PRs #76 y #77, 2026-11-28). Comprobado de punta a punta en un GNOME Shell 50 aislado, con la extensión, la ventana flotante, el dibujo, la guía, la visión, las manos y las confirmaciones. «Dejar que Drakter vea mi pantalla» y «Dejar que Drakter use mis apps» vienen **apagados** y solo se encienden en Ajustes. Pendiente: la prueba en una sesión real, después de instalar la extensión y volver a entrar.

En el modo flotante Drakter sale de su ventana: **JARVIS** se convierte en un avatar pequeño que flota encima de todas tus apps, sigue al cursor y te habla. Puede mirar la pantalla cuando se lo pides, señalarte dónde pulsar, guiarte paso a paso esperando tu clic y, si tú lo permites, usar otras apps por ti.

El cerebro, la voz, la memoria, los permisos y las confirmaciones son los de siempre. Lo único que cambia es dónde se ve Drakter.

## Requisitos

- **GNOME en Wayland** (GNOME Shell 50). En «GNOME sobre Xorg» u otros escritorios el modo no se activa.
- **La extensión de GNOME «Drakter Companion»** (`drakter-companion@drakter`). Es obligatoria: sin ella Drakter no puede ponerse encima de las demás ventanas ni seguir al cursor.

## Instalar la extensión

1. En una terminal, desde la carpeta de Drakter:

   ```bash
   ./scripts/install-gnome-extension.sh
   ```

2. **Cierra la sesión de GNOME y vuelve a entrar.** En Wayland una extensión nueva o actualizada solo se carga así. Hace falta una vez por versión de la extensión.
3. Si no queda activada sola, actívala en la app «Extensiones» o con:

   ```bash
   gnome-extensions enable drakter-companion@drakter
   ```

4. Al volver a entrar verás el indicador de Drakter en el panel superior. Abre Drakter y activa el modo.

Si pulsas el botón del modo flotante sin la extensión, Drakter abre esta misma ayuda y te dice qué falta:

| Mensaje | Qué hacer |
|---|---|
| Falta la extensión | Instálala (pasos de arriba) |
| La extensión es antigua | Vuelve a ejecutar el script y cierra la sesión |
| La extensión ha rechazado la conexión | Sal de Drakter desde la bandeja y vuelve a abrirlo (solo se admite un Drakter a la vez); si sigue, reinstala la extensión |
| Esta sesión no es GNOME con Wayland | En la pantalla de acceso elige «GNOME», no «GNOME sobre Xorg» |

## Activar y quitar

| Cómo | Activar | Quitar |
|---|---|---|
| Atajo global (en cualquier app) | `Super+Alt+D` | `Super+Alt+D` |
| Dentro de la ventana de Drakter | `Ctrl+Shift+F` (en modo Drakter y en modo Jarvis) | — |
| Botón en modo Drakter | Icono de imagen superpuesta en la cabecera, arriba a la derecha | El mismo botón |
| Botón en modo Jarvis | Icono junto a «Apariencia», arriba a la derecha (Núcleo, Holomesa y Visor) | El mismo botón |
| Ajustes | Configuración → Modo flotante → «Activar modo flotante» | «Quitar modo flotante» |
| Bandeja del sistema | Casilla «Modo flotante» | La misma casilla |
| Voz | «Modo flotante» | «Quita el modo flotante» |
| Chat | Pídeselo a Drakter | Pídeselo a Drakter |

Un punto ámbar sobre el botón indica que el modo no está disponible todavía; al pulsarlo se abre la ayuda.

Al activarlo, la ventana principal se esconde en la bandeja: el avatar ya hace su papel y no se repite en pantalla. La voz y el micrófono siguen funcionando igual. Puedes volver a abrir la ventana desde la bandeja sin salir del modo flotante. Al quitarlo, la ventana vuelve si estaba abierta.

## Qué hace JARVIS mientras flota

- **Aparece junto al cursor** cuando le hablas o te responde, como en Roamies, y se aparta a un borde cuando no hace nada. Nunca te roba el foco: escribes y pulsas en tus apps como siempre. Solo es clicable donde dibuja algo.
- **Te escucha y te habla:** la esfera se mueve con su voz y la píldora de escucha con tu micrófono.
- **Mira la pantalla** cuando se lo pides («¿cómo exporto esto a PDF?»), señala dónde pulsar y espera a que lo hagas antes de pasar al siguiente paso.
- **Dibuja tarjetas y esquemas** en una zona libre («hazme un esquema de la fotosíntesis»). `Esc` los borra.
- **Barra de pregunta:** `Super+Alt+A` la abre para escribirle sin cambiar de app.
- Cuando necesita permiso para algo, aparece el **cuadro de confirmación de siempre**. Desde el avatar no se aprueba nada. Mientras el cuadro está abierto, JARVIS y todo lo que haya dibujado desaparecen de la pantalla y dejan pasar los clics: nada puede tapar el texto del cuadro. Al cerrarlo vuelven.

## Ajustes

En Configuración → **Modo flotante**:

| Ajuste | Qué hace | Por defecto |
|---|---|---|
| Tamaño del avatar | Normal, pequeño o junto al cursor. Se aplica la próxima vez que actives el modo | Normal |
| Sonidos del avatar | Pequeños sonidos al aparecer, señalar y terminar. No afecta a la voz | Activado |
| Dejar que Drakter vea mi pantalla | Permite capturas de pantalla y leer el texto de tus ventanas, solo con el modo flotante activo y cuando la conversación lo pide | **Desactivado** |
| Dejar que Drakter use mis apps | Permite que Drakter pulse y escriba en otras ventanas cuando se lo pidas | **Desactivado** |

### Dejar que Drakter vea mi pantalla

Está apagado de entrada y solo se enciende desde este ajuste. Con él encendido, y **solo mientras el modo flotante está activo**, Drakter puede hacer una captura de tu pantalla o de una ventana, y leer el texto de tus ventanas, cuando la conversación lo pide («¿dónde pulso para exportar?», «mira esto»). Las capturas **se envían al modelo de IA** para que te responda; en tu equipo se borran nada más usarlas. Con el ajuste apagado tampoco ve los títulos de tus ventanas. Las terminales salen tapadas en las capturas, y no las lee nunca: pueden mostrar contraseñas o claves. Mientras Drakter tiene acceso, el icono de Drakter del panel superior se ve, y parpadea en cada captura.

### Dejar que Drakter use mis apps

Está apagado de entrada y solo se enciende desde este ajuste: Drakter no puede activárselo a sí mismo. Con él encendido:

- Antes de cualquier paso arriesgado (enviar, borrar, cerrar, pagar…) te pide confirmación. Si antes ha mirado la pantalla, pide confirmación para todo el plan.
- **Nunca** toca terminales, gestores de contraseñas, los ajustes del sistema ni las ventanas de Drakter, ni aunque se lo pidas.
- Nunca escribe en campos de contraseña.
- Si otra app se pone delante mientras trabaja, se para.

## Privacidad

- Las capturas de pantalla solo se hacen cuando Drakter las necesita para responderte, se procesan en tu equipo y se borran nada más leerlas.
- Lo que aparece en pantalla (textos de otras apps, títulos de ventana) se trata como dato no confiable: no puede darle órdenes a Drakter.
- La auditoría guarda qué se hizo, pero nunca lo que se tecleó ni el contenido de la pantalla.

## Seguridad de la extensión

La extensión «Drakter Companion» da acceso al puntero, a la lista de ventanas y a capturas sin diálogo. Para que no lo use cualquiera:

- Solo atiende a procesos de tu usuario que presentan el token secreto de `$XDG_RUNTIME_DIR/drakter-companion/token`.
- Además comprueba **qué proceso llama** (con el bus de sesión y `/proc`). Solo acepta:
  - el proceso principal de Drakter: el ejecutable `drakter` de la app instalada, con su `resources/app.asar` al lado, o el Electron de desarrollo de una copia de Drakter (`desktop/node_modules/electron/dist/electron`, con `desktop/package.json` llamado `drakter-desktop`);
  - el ayudante de las manos (`/usr/bin/python3 -I …/hands/helper/main.py`), y solo si desciende de ese proceso principal de Drakter.
  - Rechaza cualquier proceso con `LD_PRELOAD`, `LD_AUDIT` o `ELECTRON_RUN_AS_NODE` en su entorno.
- Solo admite **un** Drakter principal y **un** ayudante a la vez.
- La copia que instala `scripts/install-gnome-extension.sh` no lleva la interfaz de depuración (la que inyecta teclado y ratón en las pruebas). `--dev` la incluye, solo para el gnome-shell de pruebas.

**Riesgo que queda.** En el escritorio Linux tu propio usuario no es una frontera de seguridad completa. Un programa malicioso que ya se ejecute como tú podría, con esfuerzo deliberado, hacerse pasar por Drakter:

- en desarrollo, lanzando el Electron de tu copia de Drakter con su propio código (en la app instalada los fusibles de Electron lo impiden);
- modificando los archivos de la extensión en `~/.local/share/gnome-shell/extensions` (surte efecto al volver a iniciar sesión) o los de Drakter.

Lo que ya no basta es leer el token: un proceso cualquiera que lo lea recibe «acceso denegado». Si sospechas de software malicioso, desactiva la extensión (`gnome-extensions disable drakter-companion@drakter`): sin ella no hay capturas ni puntero global.

## Problemas

- **El botón abre la ayuda aunque instalé la extensión:** falta cerrar la sesión y volver a entrar, o la extensión está desactivada (`gnome-extensions list --enabled`).
- **`Super+Alt+D` no hace nada:** comprueba que Drakter está abierto (aunque sea en la bandeja) y que el indicador de la extensión aparece en el panel.
- **JARVIS no se mueve con la voz:** revisa que la voz funciona en la ventana principal ([Voz](voz.md)).
