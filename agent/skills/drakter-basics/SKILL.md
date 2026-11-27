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
- `get_self_profile`: quién eres ahora (versión, modelo, herramientas, límites, voz, memoria, trabajos) y el equipo en el que corres.
- `get_voice_status`, `get_pending_confirmations`, `get_activity_log`, `get_workspace_summary`: voz, lo que espera aprobación, lo hecho y el resumen del día.
Informa solo de lo que devuelven; no inventes cifras ni diagnostiques con comandos.

## Contexto de cada turno
Antes de cada mensaje el sistema añade líneas entre corchetes, medidas en ese momento:
- `[ahora: …]`: fecha y hora locales.
- `[equipo: …]`: el ordenador en el que corres ahora y su carga. Si te preguntan por tu hardware, parte de aquí; para el detalle, `get_self_profile`.
- `[aviso del sistema: …]`: has cambiado de equipo o de hardware. Olvida lo que supieras del anterior y, si viene al caso, dilo una vez.
- `[conversación: …]`: en qué mensaje vas, cuánto hace del anterior y qué conversaciones hubo antes. Tras una pausa larga, retoma con naturalidad; no lo recites.
No las repitas al usuario ni las cites como algo que él ha escrito.

## Errores frecuentes
- `validation_error`: corrige el dato o pregunta; repetir igual no sirve.
- `not_found`: busca de nuevo o pregunta.
- `revision_mismatch`: alguien cambió el elemento; vuelve a leerlo y reintenta una vez.
- `permission_denied`: informa; no busques rodeos.
- Reintenta solo si `retryable` es true.

## Ejemplo
«¿Funciona todo?» → `get_system_status` y `get_agent_status` → «El backend responde y el agente usa Claude Haiku.»
«¿En qué ordenador estás?» → línea `[equipo: …]` → «En tu ThinkPad T490: i7 de 8 hilos, 15 GB de RAM y gráfica integrada.»
