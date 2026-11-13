# Hoy y Configuración

> **Estado:** integrado en `drakter/integracion` (`7fd30e1`): **Hoy** es la pantalla inicial y **Configuración** está en la navegación; las APIs `today` y `settings` se montan solas. Ojo: `GET /api/v1/today` no figura en la lista de rutas permitidas de Electron (`desktop/electron/shared/routes.generated.ts`), así que el puente puede rechazarla. Las notas «Pendiente» del cuerpo se escribieron sobre `drakter/build` (`2da8bef`) y alguna puede estar ya resuelta. NO COMPROBADO en la app real (ver «Estado de la integración» en [README](README.md)).

## Para qué sirve

- **Hoy** resume tu día en una sola pantalla: lo vencido, lo de hoy, proyectos activos, agenda y hábitos. Solo lee, no modifica nada.
- **Configuración** guarda la apariencia y los avisos en este equipo, muestra el estado de la conexión con Drakter, fija la zona horaria y crea copias de seguridad.

## Moverse por la aplicación

- La barra lateral tiene estas secciones, con su atajo: Drakter (Ctrl+1), Hábitos (Ctrl+2), Tareas (Ctrl+3), Proyectos (Ctrl+4), Almacén (Ctrl+5), Calendario (Ctrl+6), Asignaturas (Ctrl+7), Relaciones (Ctrl+8) y Configuración (Ctrl+9).
- Ctrl+\ muestra u oculta el panel de contexto (botón "Mostrar panel de contexto" / "Ocultar panel de contexto" arriba a la derecha). Solo existe cuando la ventana es ancha.

## Hoy

**Pendiente de conectar:** en el código, la sección Drakter (Ctrl+1) sigue mostrando la pantalla de inicio con el personaje y el chat. Esa pantalla dice "El resumen del día y la actividad reciente aparecerán aquí cuando el espacio de trabajo esté conectado" y ofrece accesos rápidos a Tareas, Calendario y Hábitos.

La pantalla Hoy (`desktop/src/pages/today/`) está pensada así:

1. Arriba ves el día de la semana, el día y el mes, y una frase con recuentos reales, por ejemplo "2 vencidas y 3 para hoy." o "Nada pendiente para hoy.".
2. Botón **Actualizar** para recargar. También se recarga sola al volver a enfocar la ventana y cuando cambia el día en tu zona horaria (comprueba cada minuto).
3. Columna izquierda:
   - **Vencidas**: tareas abiertas con fecha pasada, en rojo.
   - **De hoy**: tareas del día con hora, prioridad (Urgente, Alta) y "En pausa" si procede.
   - **Proyectos activos**: tareas abiertas y vencidas por proyecto, con una línea de progreso en porcentaje y la fecha objetivo. Sin tareas muestra "Sin tareas todavía".
4. Columna derecha:
   - **Agenda**: eventos de hoy (los de todo el día arriba, los demás con horario "inicio a fin").
   - **Hábitos**: cada hábito con su estado: Pendiente, Hecho, Omitido o No hecho.
5. Pulsar cualquier fila te lleva a su sección (Tareas, Proyectos, Calendario, Hábitos). Los bloques vacíos ofrecen un enlace: "Ver tareas", "Ver proyectos", "Ver calendario", "Ver hábitos".
6. Cada bloque enseña como máximo 100 elementos; si hay más, aparece "Mostrando N de M."

Qué es "hoy" lo decide la zona horaria guardada en Configuración. Si no hay ninguna, usa la del sistema.

## Configuración

Abre Configuración con Ctrl+9 o desde la barra lateral.

**Apariencia** (se guarda en este equipo)
- **Tema**: Según el sistema, Claro u Oscuro.
- **Reducir movimiento**: quita animaciones y transiciones.

**Notificaciones**
- **Avisos de escritorio**: muestra los avisos importantes también fuera de la ventana.
- **Enviar notificación de prueba**: lanza una "Notificación de prueba" para ver cómo te llega.

**Conexión** (lee el estado del servicio local)
- **Clave de API**: "Configurada", "Falta la clave de API" o "Clave de API: no comprobada". Drakter solo mira si la clave existe; no lee su valor. Si falta, el texto indica añadir `ANTHROPIC_API_KEY` a `~/.config/drakter/.env` y reiniciar Drakter. Más detalle en [clave-api](../installation/clave-api.md).
- **Modo de desarrollo**: si está activo, sale un aviso ámbar arriba: "Modo de desarrollo activo: las respuestas son simuladas, no vienen de un modelo real."
- **Proveedor** y **Modelo**, si el servicio los conoce.
- **Carpeta de datos** y **Versión del esquema** de la base de datos.

**Zona horaria**
1. Abre el selector "Zona horaria".
2. Elige una zona. Se guarda al momento y verás "Zona horaria guardada".
3. Si el espacio de trabajo no está listo, el selector queda desactivado ("Se podrá guardar cuando el espacio de trabajo esté listo").

**Copias de seguridad**
1. Pulsa **Crear copia ahora**. Mientras trabaja pone "Creando copia…".
2. Al terminar sale "Copia de seguridad creada" y la copia aparece en la lista con fecha, tipo (Manual o Antes de restaurar) y tamaño en MB.
3. Las copias están en la carpeta `backups` dentro de la carpeta de datos (la que muestra "Carpeta de datos").

**Acerca de Drakter**: versión de Drakter, Electron, Chromium, Node y plataforma. Solo en la aplicación de escritorio.

**Diagnóstico**: aparece solo si la app no está empaquetada. "Probar la gestión de errores" provoca un fallo controlado.

## Lo que pide confirmación

Nada en estas pantallas pide confirmación hoy. Restaurar una copia no se puede hacer desde la interfaz: el texto de la pantalla dice que se hará desde aquí "cuando esté disponible con confirmación".

Cada cambio de zona horaria y cada copia manual se anotan en la auditoría, sin guardar datos sensibles.

## Problemas frecuentes

- **"El servicio local de Drakter no está conectado."** El escritorio no consigue hablar con el servicio local. Pulsa **Reintentar**. En Hoy, si ya había datos, se siguen mostrando los últimos.
- **"No se pudo leer esta parte."** Un bloque de Hoy falló; los demás siguen funcionando.
- **"Las tareas todavía no están disponibles."** (o proyectos, agenda, hábitos) El módulo correspondiente no se pudo leer (por ejemplo, falta alguna tabla en la base).
- **No se puede guardar la zona horaria o crear la copia.** La base de datos o su tabla de ajustes aún no está migrada: el servicio responde "settings_unavailable" (503).
- **"Disponible solo en la aplicación de escritorio"** en Acerca de: abriste la interfaz fuera de Electron.

## Pendiente

- **Pendiente:** enganchar `TodayPage` a la navegación. En `desktop/src/navigation/pages.ts` (4a84a5d) la sección `home` apunta a `HomePage`; nada importa `TodayPage`. No hay entrada "Hoy" en la barra lateral.
- **Resuelto en 4a84a5d:** los routers `today` y `settings` ya se registran (`backend/app/main.py` descubre cada `app/api/<nombre>.py`).
- **Pendiente:** añadir `GET /api/v1/today` a `contracts/api/routes.md` (no figura). La lista de rutas permitidas de Electron (`desktop/electron/shared/routes.generated.ts`, generada desde ese archivo) tiene `/api/v1/settings*` pero no `/api/v1/today`: el proceso principal rechazaría la petición aunque la pantalla estuviera montada.
- **Pendiente:** restaurar copias desde la interfaz. `POST /api/v1/system/backups/{id}/restore` figura en el contrato como "sin construir", no hay `system.py` en `backend/app/api/` y la pantalla no lo usa (las copias usan `/api/v1/settings/backups`).
- Todos los pasos de esta guía: NO COMPROBADO en la app real.
