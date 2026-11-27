# Modo Jarvis

> **Estado:** en `main` desde el 2026-11-26. Comprobado en la app real (Electron, UHD 620): entrar y salir por todas las vías, cambiar de interfaz y de avatar, las tres interfaces con tema claro, oscuro y movimiento reducido, y una confirmación destructiva desde cada interfaz. La voz se ha probado con texto inyectado, sin micrófono real.

El modo Jarvis es una **segunda interfaz**, holográfica y en 3D, para el mismo Drakter. Muestra **los mismos datos** (tareas, hábitos, calendario, proyectos, almacén, relaciones, memoria, actividad) con más gráficos, animaciones y profundidad. No cambia nada de lo que hay guardado ni la forma de ser de Drakter: solo cambia cómo se ve.

**Drakter es siempre la interfaz de inicio.** Al abrir la app ves Drakter, salvo que elijas lo contrario en Ajustes (ver «Al arrancar»).

## Entrar y salir

| Cómo | Entrar | Salir |
|---|---|---|
| Botón | Icono de radar en la cabecera de Drakter (arriba a la derecha) | «Volver a Drakter», arriba a la derecha |
| Teclado | `Ctrl+Shift+J` | `Ctrl+Shift+J` |
| Búsqueda (`Ctrl+K`) | Escribe «jarvis» y elige «Abrir modo Jarvis» | — |
| Ajustes | Configuración → Modo Jarvis → «Abrir modo Jarvis» | — |
| Bandeja del sistema | «Alternar modo Jarvis» | «Alternar modo Jarvis» |
| Voz | «Modo Jarvis», «Activa el modo Jarvis», «Pon el modo Jarvis» | «Vuelve a Drakter», «Modo normal», «Sal del modo Jarvis» |
| Chat | «Pon el modo Jarvis», o como lo digas: el agente lo entiende | «Vuelve a Drakter» |

- **Voz:** las frases exactas se atienden al instante, sin pasar por el modelo, y Drakter confirma en voz alta («Modo Jarvis activado, señor»). Si lo dices de otra forma o lo mezclas con otra petición («activa el modo Jarvis y dime mis tareas»), lo resuelve el agente, que tarda un poco más.
- **En reposo:** «Activa el modo Jarvis» funciona también aunque Drakter esté en reposo: la palabra «Jarvis» del final lo despierta, hace el cambio y vuelve a reposo.
- **Lo que sigue funcionando:** al cambiar de modo, la voz, los avisos, las confirmaciones y los trabajos en segundo plano no se interrumpen.

## Las tres interfaces

| Interfaz | Cómo es |
|---|---|
| **Núcleo** (por defecto) | Un astrolabio de luz: el avatar en el centro y cada sección como un anillo a su alrededor |
| **Holomesa** | Una mesa de operaciones: cada sección es una maqueta de luz que se puede rodear |
| **Visor** | Un visor curvo a tu alrededor: giras la vista para pasar de una sección a otra |

Para cambiar de interfaz:

- **Selector «Apariencia»**, arriba a la derecha dentro de Jarvis, o `Ctrl+Shift+A`.
- **Ajustes:** Configuración → Modo Jarvis → Interfaz. Cambiarla aquí no abre Jarvis.
- **Búsqueda (`Ctrl+K`):** «interfaz visor», «holomesa», «núcleo»…
- **Voz:** «Cambia a la interfaz visor», «Interfaz núcleo», «Pon la interfaz holomesa». «Mesa» sola no basta: di «interfaz mesa».
- **Chat:** «Pon la interfaz visor».

Pedir una interfaz estando en Drakter también abre Jarvis.

## Avatares

El avatar es el mismo en los dos modos. Hay 8 avatares 3D y el personaje clásico:

| Avatar | Cómo pedirlo por voz |
|---|---|
| Holo-Contorno (por defecto) | «Pon el avatar contorno», «Usa el holograma» |
| Holo-Hilo | «Pon el avatar hilo» |
| Holo-Busto | «Usa el busto» |
| Holo-Orbe | «Usa el orbe» |
| Holo-Filamento | «Pon el filamento azul» |
| Ascuario (dragón) | «Pon el avatar dragón», «Usa Ascuario» |
| El Relojero | «Pon el relojero», «Avatar reloj» |
| Filamento (dorado) | «Pon el filamento», «Usa el filamento dorado» |
| Ninguno (personaje clásico) | «Quita el avatar», «Pon el personaje clásico» |

Las palabras corrientes («reloj», «hilo») necesitan «avatar» delante. Para cambiarlo sin voz:

- **Selector «Apariencia»** de Jarvis.
- **Ajustes:** Configuración → Avatar, con miniaturas y una vista previa.
- **Búsqueda:** `Ctrl+K` → «avatar orbe», «dragón»…

Más sobre los avatares: [personaje.md](personaje.md).

## Moverse por Jarvis

- **Secciones:** los números **0-9** (sin `Ctrl`) llevan a cada sección, igual que `Ctrl+0…9` en Drakter. Cada interfaz muestra sus atajos. La sección en la que estás se conserva al cambiar de modo.
- **Ratón:** clic en un anillo, maqueta o panel para abrir su sección; las interfaces responden al movimiento del ratón.
- **Chat:** puedes escribir a Drakter desde la propia interfaz: en Núcleo y en Holomesa, en su cuadro de conversación; en el Visor, en el sector Núcleo.
- **Confirmaciones:** cuando el agente o tú pedís algo destructivo (borrar, olvidar…), aparece **arriba al centro y por encima de todo** el aviso «Drakter necesita tu confirmación». Pulsa **Revisar** y decide en el diálogo del sistema. Nunca se ejecuta nada destructivo sin ese paso.

## Ajustes del modo Jarvis

En **Configuración → Modo Jarvis**:

- **Interfaz:** Núcleo, Holomesa o Visor.
- **Al arrancar:**
  - «Siempre en Drakter» (por defecto);
  - «Recordar el último modo»: si cerraste en Jarvis, vuelve a abrir en Jarvis.
- **Calidad gráfica:**
  - **Automática** (por defecto): elige según tu gráfica y baja sola si la máquina va justa.
  - **Cine:** más partículas y brillo, hasta 60 fps.
  - **Equilibrado:** la de una gráfica integrada como la Intel UHD 620.
  - **Ahorro:** dibuja lo mínimo.

En **Configuración → Apariencia**, **Reducir movimiento** quita la secuencia de entrada, el movimiento de cámara y las animaciones continuas. También se respeta la preferencia de movimiento reducido del sistema.

Jarvis es siempre oscuro: el tema claro u oscuro de Ajustes solo cambia Drakter.

## Rendimiento

Medido en la máquina de referencia (i7-8665U, Intel UHD 620), con el avatar por defecto y en Equilibrado, en reposo: el proceso que dibuja la ventana usa entre el **7 % y el 9 %** de un núcleo, y la gráfica entre el **8 % y el 9 %**. Con la ventana minimizada baja a menos del 1 %. Si notas la máquina cargada, pon Calidad gráfica en **Ahorro**.

## Problemas

- **No hay 3D, solo paneles:** tu gráfica no tiene WebGL2 o se perdió el contexto. Jarvis sigue funcionando sin el lienzo 3D. Vuelve a Drakter y entra otra vez para reintentarlo.
- **No se abre Jarvis y sale «No se pudo abrir el modo Jarvis»:** vuelves a Drakter sin perder nada. Reinténtalo; si se repite, mira el log de la app ([problemas.md](problemas.md)).
- **La voz no cambia de modo:**
  - En reposo, empieza por «Hey Jarvis» o usa la frase completa («activa el modo Jarvis»).
  - Si Drakter dice la frase pero la pantalla no cambia, comprueba que la app está abierta. Varias órdenes seguidas en menos de un segundo cuentan como una.
- **Un avatar no aparece:** si el avatar elegido no puede cargarse, se ve el personaje clásico.

## Para quien toca el código

- Diseño y contratos: el artefacto `jarvis-arquitectura.md`, más las entradas «Modo Jarvis» y «J1»/«V1» de [DECISIONS.md](../DECISIONS.md). Estado: sección «Modo Jarvis» de [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md).
- Escritorio:
  - `desktop/src/stores/{uiMode,appearance}.ts` y `desktop/src/app/{ModeRoot,SessionHosts}.tsx`;
  - `desktop/src/jarvis/` (`JarvisShell.tsx`, `stage/` es el lienzo único, `layouts/<id>/` las interfaces y `data/` los datos);
  - `desktop/src/character/avatars/`.
- Voz y agente:
  - `voice/conversation/layer0.{py,es.toml}` (`classify_ui`, `classify_appearance`);
  - `backend/app/tools/ui.py` (`ui_set_mode`, `ui_set_appearance`);
  - `backend/app/services/ui_mode.py` (eventos `ui.mode` y `ui.appearance`).
