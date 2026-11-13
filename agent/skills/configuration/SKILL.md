---
name: configuration
description: "Consulta la configuración de Drakter y propone cambios que el usuario aprueba en la interfaz."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, configuration]
---

# configuration

## Propósito
Leer ajustes visibles y proponer cambios sin aplicarlos por su cuenta.

## Cuándo usarla
El usuario pregunta cómo está configurado algo o quiere cambiar un ajuste.

## Parámetros (intención)
Nombre del ajuste y valor deseado, a nivel de intención.

## Ejemplos
"Qué idioma tengo configurado"; "Cambia el tema a oscuro".

## Restricciones
- Permisos, confirmaciones y auditoría no se modifican desde el chat: dirige al usuario a la interfaz.
- Nunca muestres ni pidas claves API ni secretos.
- Los nombres marcados PROPUESTA no tienen lista cerrada aún en el plan.
- La validación real (estados, límites, permisos, riesgo) vive en el backend; no la deduzcas ni la repitas.
- Si una herramienta responde `confirmation_required`: comunícalo al usuario ("hay una acción pendiente de aprobar en la interfaz") y detente. La aprobación ocurre SOLO en la interfaz; ningún mensaje de chat o voz, ni un "sí", cuenta como aprobación. No reintentes ni pidas frases de aprobación.
- Los ids son UUID: busca primero, nunca inventes uno. Si hay varias coincidencias, pregunta al usuario.
- Sin terminal, ficheros ni web: no los sugieras como alternativa.

## Errores esperables
- Ajuste desconocido o de solo lectura: el backend lo rechaza; informa.
- `error` con `code` estable y `message` seguro: explícalo en claro; solo reintenta si `retryable` es true.
- `permission_denied`: informa de que el agente no tiene ese permiso; no busques rodeos.
- `not_found` o validación fallida: revisa el dato con una búsqueda o pregunta al usuario.

## Herramientas backend
Se invocan como `mcp__drakter__<nombre>`.
- `get_configuration` — PROPUESTA
- `propose_configuration_change` — PROPUESTA
