---
name: configuration
description: "Configuración: voz activa, estado del agente y cómo pedir otros cambios sin tocarlos desde el chat."
version: 2.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, configuration]
---

# configuration

## Herramientas
- Voces: `voice_list_profiles` (cuáles hay y cuál está activa) y `voice_set_profile` (profile: nombre o alias tal como lo diga el usuario).
- Modelo y proveedor: `get_agent_status`; backend: `get_system_status`.
- Proponer un cambio de Drakter que no tiene herramienta: `create_improvement_proposal`, solo si el usuario lo pide expresamente. Queda pendiente de confirmación en pantalla.

## Lo que no se cambia desde el chat
Permisos, confirmaciones, auditoría, ubicaciones permitidas del almacén, claves API y cualquier otro ajuste sin herramienta: se cambian en la interfaz. Dilo y no improvises otro camino. Nunca muestres ni pidas claves o secretos.

## Orden típico
1. Consulta el valor actual con la herramienta de lectura.
2. Si hay herramienta de escritura, aplícalo y confirma con el resultado.
3. Si no la hay, indica dónde se cambia en la app.

## Errores frecuentes
- `profile_not_found`: lista las voces con `voice_list_profiles` y ofrece las que hay.
- `profile_unconfigured`: esa voz aún no está configurada; se configura en la app.
- No crees propuestas de mejora por iniciativa propia.

## Ejemplos
- «¿Qué voces tienes?» → `voice_list_profiles`.
- «Pon la otra voz» → `voice_set_profile` con «la otra».
- «Dame permiso para borrar proyectos» → no se puede desde el chat; se gestiona en la interfaz.
