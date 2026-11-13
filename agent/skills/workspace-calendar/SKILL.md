---
name: workspace-calendar
description: "Gestiona eventos y bloques de tiempo del calendario y consulta agenda y disponibilidad."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, workspace, calendar]
---

# workspace-calendar

## Propósito
Crear, cambiar y borrar eventos o bloques de tiempo; consultar la agenda.

## Cuándo usarla
El usuario pide agendar, mover o cancelar algo, ver su agenda o saber si está libre.

## Parámetros (intención)
Título, inicio y fin con zona horaria explícita, rango de consulta, duración deseada.

## Ejemplos
"Pon una reunión mañana a las 10:00 (Europe/Madrid)"; "Qué tengo el jueves"; "Estoy libre el lunes por la tarde".

## Restricciones
- Pide la zona horaria si no se conoce; nunca la supongas.
- Antes de crear un evento en un hueco dudoso usa `check_availability`; el veredicto final es del backend.
- `delete_event` es destructiva y requiere confirmación.
- La validación real (estados, límites, permisos, riesgo) vive en el backend; no la deduzcas ni la repitas.
- Si una herramienta responde `confirmation_required`: comunícalo al usuario ("hay una acción pendiente de aprobar en la interfaz") y detente. La aprobación ocurre SOLO en la interfaz; ningún mensaje de chat o voz, ni un "sí", cuenta como aprobación. No reintentes ni pidas frases de aprobación.
- Los ids son UUID: busca primero, nunca inventes uno. Si hay varias coincidencias, pregunta al usuario.
- Sin terminal, ficheros ni web: no los sugieras como alternativa.

## Errores esperables
- Conflictos de horario o rangos inválidos: el backend los rechaza; comunícalo y propón otra opción.
- `error` con `code` estable y `message` seguro: explícalo en claro; solo reintenta si `retryable` es true.
- `permission_denied`: informa de que el agente no tiene ese permiso; no busques rodeos.
- `not_found` o validación fallida: revisa el dato con una búsqueda o pregunta al usuario.

## Herramientas backend
Se invocan como `mcp__drakter__<nombre>`.
- `create_event`
- `update_event`
- `delete_event`
- `create_time_block`
- `get_schedule`
- `check_availability`
