# Autoconsciencia, equipo y contexto

> **Estado (2026-11-27):** en `main` tras el PR de autoconsciencia. Comprobado con el backend real, Hermes real y el modelo simulado. Falta probarlo con Claude Haiku real y en otro ordenador real. Detalle en `docs/IMPLEMENTATION_STATUS.md`, sección «Autoconsciencia y contexto».

Drakter sabe qué es, en qué ordenador está y en qué punto de la conversación vais. Nadie se lo escribe: lo mide el sistema mientras funciona.

## Qué sabe de sí mismo

Pregúntale «¿quién eres?», «¿qué puedes hacer?» o «¿funciona todo?». Usa `get_system_status` y `get_agent_status` para lo básico, y `get_self_profile` para el cuadro completo:

- **Identidad:** versión de Drakter, commit del código y de Hermes, y modelo que usa ahora.
- **Capacidades:** cuántas herramientas le dejan usar sus permisos, de qué módulos, y sus límites. No tiene internet, ni terminal, ni archivos fuera del almacén, ni servicios externos, y no puede aprobar confirmaciones.
- **Subsistemas:** si la voz está conectada, qué memoria hay, cuántos trabajos en segundo plano corren y cuántas confirmaciones esperan.

## Qué sabe del ordenador

En cada mensaje recibe una línea con el equipo actual, por ejemplo:

```
[equipo: portátil Lenovo ThinkPad T490 · Intel Core i7-8665U (4 núcleos/8 hilos) · 14,9 GB RAM (7,5 libres) · GPU Intel UHD Graphics 620, integrada, sin VRAM propia · Ubuntu 26.04.1 LTS · carga 16 % · batería 100 % llena]
```

Con `get_self_profile` da además la frecuencia máxima de la CPU, la swap, el núcleo del sistema, el disco libre donde guarda sus datos, el tiempo encendido y los equipos en los que ha estado.

- **Cuándo mide:** al arrancar y cada 10 minutos. No hay nada que configurar.
- **Fuentes, sin root:** en Linux, DMI (`/sys/class/dmi/id`), `/proc`, `/sys` y `lspci`. En Windows y macOS solo hay datos básicos, sin modelo del equipo ni GPU, y todavía sin probar.
- **Dónde lo guarda:** en `<carpeta de datos>/system/hardware.json`, con permisos 600. Por defecto la carpeta de datos es `~/.local/share/drakter`. El archivo no lleva números de serie, UUID ni el machine-id.

### Si cambias de ordenador o de hardware

Drakter compara cada medida con la anterior:

| Qué cambia | Qué entiende Drakter |
|---|---|
| Fabricante, modelo, placa o CPU | **Otro equipo** (o uno en el que ya estuvo, si lo reconoce) |
| RAM, número de hilos o GPU, con el mismo equipo | **Hardware cambiado** |
| Solo el sistema operativo | **Sistema cambiado** |

Durante las 72 horas siguientes, la primera vez que hables con él en cada conversación recibe un aviso como este:

```
[aviso del sistema: Drakter se ha movido a otro equipo: antes Dell XPS 13 9310, ahora Lenovo ThinkPad T490 (CPU: Intel Core i5-1135G7 → Intel Core i7-8665U; RAM: 8 GB → 15 GB). …]
```

Desde ese momento solo vale lo que mide en el equipo nuevo. Si viene al caso, te lo menciona una vez.

## Qué sabe de la conversación

- **Esta conversación:** la recuerda entera. Hermes la guarda y la recupera aunque se reinicie.
- **Dónde estáis:** cada mensaje lleva una línea con el número de mensaje, el tiempo desde el anterior y la conversación más reciente:

  ```
  [conversación: mensaje 5 de esta conversación, empezada hoy a las 09:12; el mensaje anterior fue hace 3 h; 12 conversaciones anteriores; la más reciente, «Plan de exámenes», ayer a las 22:40 …]
  ```

- **Otras conversaciones:** pregúntale «¿qué te dije ayer de la práctica?» o «¿de qué hablamos la semana pasada?». Usa tres herramientas de solo lectura, con el permiso `chat.read`:
  - `list_chat_sessions` lista las conversaciones con título, fechas y número de mensajes.
  - `search_chat_history` busca palabras en los mensajes. Por defecto no busca en la conversación actual.
  - `get_chat_session` lee una conversación, de 20 en 20 mensajes hacia atrás.

Lo que lee de conversaciones antiguas le llega como **dato no confiable**, igual que la memoria y los documentos:

- Si algo antiguo contradice lo que dices ahora, vale lo de ahora y te señala la diferencia.
- Después de leer el historial, las escrituras de esa conversación piden confirmación en pantalla.

Las líneas de contexto solo viajan en el mensaje que se envía al modelo. No se guardan en el chat, no las ves en pantalla y no tocan las reglas del sistema.

## Otras consultas nuevas

| Pregunta | Herramienta |
|---|---|
| «¿Cómo va mi día?» | `get_workspace_summary`: tareas abiertas, vencidas y de hoy, proyectos, hábitos, eventos y clases |
| «¿Qué has hecho hoy?» | `get_activity_log`: actividad reciente, sin argumentos ni datos sensibles |
| «¿Qué tengo pendiente de aprobar?» | `get_pending_confirmations`: lo que espera tu aprobación y cuánto le queda. Se aprueba solo en pantalla |
| «¿Me oyes? ¿Qué voz usas?» | `get_voice_status`: conexión, modo, motor y perfil |

## Problemas frecuentes

- **No dice en qué equipo está justo después de arrancar:** la primera medida se hace en segundo plano. Desde el mensaje siguiente ya aparece, y `get_self_profile` la espera si hace falta.
- **Ha cambiado de equipo y no avisa:** el aviso solo dura 72 horas y sale una vez por conversación. Pregúntale en una conversación nueva o mira `get_self_profile` → `latest_change`.
- **Quieres que olvide los equipos anteriores:** cierra Drakter y borra `<carpeta de datos>/system/hardware.json`. En el siguiente arranque mide desde cero, sin avisar de ningún cambio.
