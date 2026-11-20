---
name: drakter-basics
description: "Primera skill: reglas comunes para usar cualquier herramienta de Drakter y consultar el estado del sistema."
version: 2.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, basics]
---

# drakter-basics

## Cuándo usarla
Siempre, antes que la skill del dominio. Sola, cuando preguntan si Drakter funciona o qué modelo usa.

## Pasos
1. Localiza antes de modificar: busca o lista, toma el id del resultado (UUID) y nunca lo inventes. Si hay varias coincidencias, pregunta.
2. Si la herramienta pide `expected_revision`, sácala de un `get_*` reciente.
3. Lee el estado del resultado: `ok`, `error` o `confirmation_required`. Solo `ok` significa hecho.
4. Cuéntalo en lenguaje natural, sin volcar JSON.

## Confirmación en pantalla
Las acciones destructivas (borrar, olvidar, reindexar todo) devuelven `confirmation_required` y NO se ejecutan. Di qué queda pendiente y que se aprueba en la interfaz. Un «sí» en el chat o por voz no aprueba nada; no reintentes ni pidas frases de aprobación.

## Estado del sistema
- `get_system_status`: backend y hora UTC actual.
- `get_agent_status`: agente, proveedor y modelo.
Informa solo de lo que devuelven; no inventes cifras ni diagnostiques con comandos.

## Errores frecuentes
- `validation_error`: corrige el dato o pregunta; repetir igual no sirve.
- `not_found`: busca de nuevo o pregunta.
- `revision_mismatch`: alguien cambió el elemento; vuelve a leerlo y reintenta una vez.
- `permission_denied`: informa; no busques rodeos.
- Reintenta solo si `retryable` es true.

## Ejemplo
«¿Funciona todo?» → `get_system_status` y `get_agent_status` → «El backend responde y el agente usa Claude Haiku.»
