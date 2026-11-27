# Modo flotante

> **Estado:** en construcción (2026-11-27). La interfaz de la ventana principal (botones, atajo, ayuda y ajustes) está hecha; la ventana flotante, la extensión de GNOME y las herramientas de dibujo y de manos llegan con la integración del modo. Esta guía describe el comportamiento previsto en `docs/floating/CONTRACT.md`.

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
| La extensión ha rechazado la conexión | Sal de Drakter desde la bandeja y vuelve a abrirlo; si sigue, reinstala la extensión |
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

- **Sigue al cursor** por toda la pantalla sin robarte el foco: escribes y pulsas en tus apps como siempre. Solo es clicable donde dibuja algo.
- **Te escucha y te habla:** la esfera se mueve con su voz y la píldora de escucha con tu micrófono.
- **Mira la pantalla** cuando se lo pides («¿cómo exporto esto a PDF?»), señala dónde pulsar y espera a que lo hagas antes de pasar al siguiente paso.
- **Dibuja tarjetas y esquemas** en una zona libre («hazme un esquema de la fotosíntesis»). `Esc` los borra.
- **Barra de pregunta:** `Super+Alt+A` la abre para escribirle sin cambiar de app.
- Cuando necesita permiso para algo, aparece el **cuadro de confirmación de siempre**. Desde el avatar no se aprueba nada.

## Ajustes

En Configuración → **Modo flotante**:

| Ajuste | Qué hace | Por defecto |
|---|---|---|
| Tamaño del avatar | Normal, pequeño o junto al cursor. Se aplica la próxima vez que actives el modo | Normal |
| Sonidos del avatar | Pequeños sonidos al aparecer, señalar y terminar. No afecta a la voz | Activado |
| Dejar que Drakter use mis apps | Permite que Drakter pulse y escriba en otras ventanas cuando se lo pidas | **Desactivado** |

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

## Problemas

- **El botón abre la ayuda aunque instalé la extensión:** falta cerrar la sesión y volver a entrar, o la extensión está desactivada (`gnome-extensions list --enabled`).
- **`Super+Alt+D` no hace nada:** comprueba que Drakter está abierto (aunque sea en la bandeja) y que el indicador de la extensión aparece en el panel.
- **JARVIS no se mueve con la voz:** revisa que la voz funciona en la ventana principal ([Voz](voz.md)).
