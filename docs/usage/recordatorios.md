# Recordatorios

> **Estado:** integrado en `drakter/integracion` (`2e05ba6`): el router `notifications` se registra solo, `ReminderTicker` arranca en el `lifespan` y la interfaz monta `startNotificationFeed` (`AppShell`) y `RemindersNotice` (Configuración). Las notas «Pendiente» del cuerpo se escribieron sobre `drakter/build` (`2da8bef`) y alguna puede estar ya resuelta. NO COMPROBADO en la app real (ver «Estado de la integración» en [README](README.md)).

## Aviso importante

**Los recordatorios solo funcionan con Drakter abierto.** Con la app cerrada no recibirás avisos. El código lo confirma: el servicio es un temporizador dentro del backend (decisión D-29, comprobación cada 60 segundos) y la API de estado declara `requires_app_open: true`. La interfaz lo muestra con el texto "Los recordatorios solo funcionan con Drakter abierto. Con la app cerrada no recibirás avisos." (commit `219a9a0`).

## Para qué sirve

Drakter te avisa de lo que vence o empieza: tareas con fecha o con hora, y eventos de calendario con recordatorio. Los avisos llegan como notificación dentro de la app y, si lo activas, también como aviso de escritorio.

## Qué genera un aviso

1. **Tareas** abiertas (pendientes o en curso, no archivadas):
   - Con hora de vencimiento: aviso a esa hora, "Vence a las HH:MM".
   - Solo con fecha: aviso desde las 09:00 de ese día, "Vence hoy".
2. **Eventos** de calendario con "minutos antes" definido (sin recurrencia, no cancelados):
   - Con hora: aviso esos minutos antes de empezar, "Empieza a las HH:MM".
   - De todo el día: aviso relativo a las 09:00, "El DD/MM, todo el día".
3. La hora se calcula en tu zona horaria guardada. Si no hay ninguna, usa Europe/Madrid.
4. Cada aviso sale una sola vez. Reiniciar Drakter no lo repite. Si cambias la hora de una tarea o evento, genera un aviso nuevo.
5. Las ocurrencias recurrentes y los hábitos todavía no generan avisos (el código deja un punto de enganche para añadirlos).

## Cómo lo ves en el día a día

Los pasos 1 a 3 describen el comportamiento del código del módulo, que hoy no está montado en la interfaz (ver Pendiente).

1. Abre Drakter y déjalo abierto. Cada minuto consulta los avisos sin leer (también reacciona al instante al evento `notification.created`).
2. Hasta 3 avisos nuevos salen cada uno como notificación propia. Si hay más, se guardan todos en el centro de notificaciones y sale uno solo: "N recordatorios pendientes".
3. Para repasarlos, pulsa la campana de arriba a la derecha (nombre accesible "Notificaciones"; con avisos sin leer pone "Notificaciones, N sin leer"). El panel lista cada aviso con su hora relativa. Se marcan como leídos al abrirlo. **Vaciar** borra la lista del panel.
4. Los avisos fuera de la ventana dependen de **Avisos de escritorio** en Configuración (Ctrl+9, sección Notificaciones). Puedes probarlo con **Enviar notificación de prueba**. Ver [hoy-y-ajustes](hoy-y-ajustes.md).

## Al abrir la app después de un rato

Al arrancar, Drakter recupera lo que venció en las últimas 6 horas y lo que aún está por empezar. Lo anterior no se avisa. El aviso de la interfaz lo dice así: "Al abrirla verás los de las últimas 6 horas." Máximo 20 avisos por ciclo; el resto sale en el siguiente, del más antiguo al más nuevo.

## Estado del servicio

El texto de aviso (`RemindersNotice`) consulta `GET /api/v1/notifications/status`. Si el servicio no corre o el último ciclo falló, añade "Los recordatorios están detenidos ahora mismo." y se muestra en tono de advertencia.

## Lo que pide confirmación

Nada. No hay herramienta del agente sobre notificaciones ni forma de borrarlas en el backend; la interfaz solo marca como leídas. El texto de los avisos es dato del usuario y no se escribe en los registros.

## Problemas frecuentes

- **No me llegó un aviso con la app cerrada.** Es el comportamiento esperado. Solo se recuperan las últimas 6 horas al abrir.
- **Un aviso tardó hasta un minuto.** El ciclo es de 60 segundos.
- **Salen muchos juntos al abrir.** Con más de 3 se agrupan en "N recordatorios pendientes"; abre la campana.
- **"Los recordatorios están detenidos ahora mismo."** El servicio no corre o falló un ciclo. Los estados internos son `tick_failed` (el ciclo entero falló) y `source_failed` (falló una fuente, las demás siguen).
- **No sale aviso de escritorio.** Activa **Avisos de escritorio** en Configuración.

## Pendiente

- **Resuelto en 4a84a5d:** `notifications.router` se registra (`_discover_routers()`) y `ReminderTicker` se crea en `_install_services` y arranca/para en el `lifespan` de `backend/app/main.py`.
- **Pendiente:** montar `startNotificationFeed` y `RemindersNotice` en la interfaz (`AppShell.tsx` solo importa `NotificationCenter`, la campana; nada más usa esos exports). Sin eso, solo salen en la campana los avisos generados en el propio escritorio.
- **Resuelto:** las operaciones `notifications.list`, `notifications.read` y `notifications.status` ya no se copian a mano: Electron usa rutas generadas desde `contracts/api/routes.md` y esas tres rutas figuran en `routes.generated.ts`. La tabla `notifications` ya está en la migración `0001_core_entities.sql`.
- **Pendiente:** la pantalla donde se muestra `RemindersNotice` no está decidida en el código (nadie la importa).
- **Pendiente:** avisos de hábitos y ocurrencias recurrentes.
- Todos los pasos de esta guía: NO COMPROBADO.
