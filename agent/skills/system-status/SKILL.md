---
name: system-status
description: "Informa del estado del sistema, agente, voz, memoria y resumen del Workspace."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, system, status]
---

# system-status

## Propósito
Responder de forma fiable a preguntas sobre el estado de Drakter.

## Cuándo usarla
El usuario pregunta si algo funciona, qué componentes están activos o pide un resumen general.

## Parámetros (intención)
Normalmente ninguno; opcionalmente, qué componente interesa.

## Ejemplos
"Cómo está el sistema"; "Funciona la voz"; "Dame un resumen de mi Workspace".

## Restricciones
- Informa solo de lo que devuelven las herramientas; no inventes cifras de latencia ni de uso.
- Solo lectura: no cambia nada.
- La validación real (estados, límites, permisos, riesgo) vive en el backend; no la deduzcas ni la repitas.
- Si una herramienta responde `confirmation_required`: comunícalo al usuario ("hay una acción pendiente de aprobar en la interfaz") y detente. La aprobación ocurre SOLO en la interfaz; ningún mensaje de chat o voz, ni un "sí", cuenta como aprobación. No reintentes ni pidas frases de aprobación.
- Los ids son UUID: busca primero, nunca inventes uno. Si hay varias coincidencias, pregunta al usuario.
- Sin terminal, ficheros ni web: no los sugieras como alternativa.

## Errores esperables
- Componente no disponible: indícalo tal cual; no lo diagnostiques con comandos.
- `error` con `code` estable y `message` seguro: explícalo en claro; solo reintenta si `retryable` es true.
- `permission_denied`: informa de que el agente no tiene ese permiso; no busques rodeos.
- `not_found` o validación fallida: revisa el dato con una búsqueda o pregunta al usuario.

## Herramientas backend
Se invocan como `mcp__drakter__<nombre>`.
- `get_system_status`
- `get_agent_status`
- `get_voice_status` (en el catálogo; el backend aún no la sirve)
- `get_memory_status`
- `get_workspace_summary` (en el catálogo; el backend aún no la sirve)
