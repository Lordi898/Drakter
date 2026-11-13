---
name: workspace-habits
description: "Gestiona hábitos: crearlos, registrar cumplimientos y consultar historial y estadísticas."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, workspace, habits]
---

# workspace-habits

## Propósito
Seguir los hábitos del usuario y sus registros.

## Cuándo usarla
El usuario crea o cambia un hábito, dice que lo ha cumplido o pregunta por su racha o evolución.

## Parámetros (intención)
Nombre, periodicidad, fecha del cumplimiento, rango de fechas para historial.

## Ejemplos
"Crea el hábito leer 20 minutos al día"; "Hoy he hecho ejercicio"; "Cómo llevo el hábito de leer este mes".

## Restricciones
- Las rachas y estadísticas las calcula el backend (`get_habit_statistics`); no las calcules.
- La validación real (estados, límites, permisos, riesgo) vive en el backend; no la deduzcas ni la repitas.
- Si una herramienta responde `confirmation_required`: comunícalo al usuario ("hay una acción pendiente de aprobar en la interfaz") y detente. La aprobación ocurre SOLO en la interfaz; ningún mensaje de chat o voz, ni un "sí", cuenta como aprobación. No reintentes ni pidas frases de aprobación.
- Los ids son UUID: busca primero, nunca inventes uno. Si hay varias coincidencias, pregunta al usuario.
- Sin terminal, ficheros ni web: no los sugieras como alternativa.

## Errores esperables
- Un cumplimiento repetido puede ser rechazado o tratado como idempotente por el backend.
- `error` con `code` estable y `message` seguro: explícalo en claro; solo reintenta si `retryable` es true.
- `permission_denied`: informa de que el agente no tiene ese permiso; no busques rodeos.
- `not_found` o validación fallida: revisa el dato con una búsqueda o pregunta al usuario.

## Herramientas backend
Se invocan como `mcp__drakter__<nombre>`.
- `create_habit`
- `update_habit`
- `register_habit_completion`
- `get_habit_history`
- `get_habit_statistics`
