# Memoria

> **Estado:** integrado en `drakter/integracion` (`2e05ba6`): el backend monta el router de memoria (`backend/app/integrations/memory/router.py`) y el agente recibe el servicio. No hay pantalla de memoria en `desktop/src`. Las notas «Pendiente» del cuerpo se escribieron sobre `drakter/build` (`2da8bef`) y alguna puede estar ya resuelta. NO COMPROBADO en la app real (ver «Estado de la integración» en [README](README.md)).

La memoria guarda cosas estables sobre ti (preferencias, datos, decisiones) para que Drakter no te las pida dos veces. Tú decides qué se queda.

## Qué recuerda

Tipos de recuerdo (`MemoryKind`): de trabajo, episódico (acontecimientos), semántico (hechos y preferencias) y procedimental (patrones). Categorías: perfil, preferencias, entidades, eventos, casos y patrones.

Un recuerdo guarda una referencia a tus tareas, proyectos u otras entidades, nunca una copia de su estado. Si el texto parece una credencial (clave, contraseña, token), se rechaza con el error `memory_secret_rejected`.

El extractor de frases (`pipeline/extract.py`) funciona por reglas, sin modelo, en español e inglés. Reconoce, por ejemplo, "recuerda que...", "prefiero...", "me llamo...", "vivo en...". **Pendiente:** en `2da8bef` nada lo llama desde la conversación; no puedo afirmar que Drakter apunte cosas solo.

## Capas L0, L1 y L2

Son niveles de detalle de un mismo recuerdo, no tipos distintos:

- **L0**: resumen de una línea (hasta 256 caracteres). Para buscar rápido.
- **L1**: resumen ampliado (hasta 4000 caracteres). Es el nivel que se lee por defecto.
- **L2**: el texto completo.

## Quién propone y quién aprueba

- Lo que creas tú desde la interfaz (`POST /api/v1/memory`) entra ya aprobado, salvo que contradiga otro recuerdo.
- Lo que propone el agente (`propose_memory`) queda **pendiente** hasta que lo apruebes tú. Nunca se aprueba solo.
- Lo que viene de documentos, resultados de herramientas o importaciones se trata siempre como dato de terceros, sin autoridad.
- Si dos recuerdos se contradicen, se registra el conflicto y decides tú cuál se queda; el otro pasa a "sustituido".

Estados de un recuerdo: `pending`, `approved`, `rejected`, `superseded`.

## Ver, corregir y borrar

Por chat, el agente puede (herramientas de `backend/app/tools/memory.py`):

- `get_memory_status`: dice si la memoria está disponible y qué motor la sirve.
- `search_memory`: busca entre los recuerdos aprobados.
- `get_memory_item`: lee uno en nivel `l0`, `l1` o `l2`.
- `propose_memory`: propone uno nuevo (queda pendiente).
- `forget_memory`: pide olvidar uno. Siempre exige tu confirmación antes de ejecutarse (ver [chat-y-personaje](chat-y-personaje.md)).

El agente no puede aprobar, corregir ni resolver conflictos. Eso solo lo hace la interfaz, mediante la API local `/api/v1/memory`:

| Para | Ruta |
|---|---|
| Listar (filtros por estado, tipo, categoría) | `GET /api/v1/memory` |
| Ver uno | `GET /api/v1/memory/{id}` |
| Buscar | `POST /api/v1/memory/search` |
| Crear | `POST /api/v1/memory` |
| Corregir | `PATCH /api/v1/memory/{id}` |
| Aprobar / rechazar | `POST /api/v1/memory/{id}/approve` y `/reject` |
| Ver / resolver conflictos | `GET /api/v1/memory/conflicts`, `POST /api/v1/memory/conflicts/{id}/resolve` |
| Olvidar | `POST /api/v1/memory/{id}/forget` |

Corregir un recuerdo lo marca como confirmado por ti (salvo si viene de terceros). Olvidar es permanente.

## La memoria no manda sobre las reglas

Lo recuperado de la memoria es dato no confiable. Se entrega al agente dentro de un bloque delimitado y marcado como `untrusted_data`, con su procedencia, y lo que diga no cambia el prompt ni las reglas. Orden de prioridad: seguridad y permisos, reglas del sistema, identidad, contexto del usuario, conversación, memoria, instrucción actual. Las reglas de seguridad son una constante en código, no un archivo editable. Un recuerdo nunca entra en el mensaje de sistema. Si un recuerdo parece una inyección de instrucciones, se marca con `injection_suspected`.

## Privacidad

El registro de operaciones (`logs/memory_operations.log` y `logs/retrieval.log`) guarda ids, huellas y resultados, nunca el contenido de los recuerdos ni consultas en claro.

## Problemas frecuentes

- `memory_secret_rejected`: el texto parece una clave; no se guarda.
- `memory_conflict_open`: al aprobar, resuelve antes el conflicto abierto.
- `memory_not_found`: el id no existe o ya se olvidó.
- `confirmation_required` al olvidar desde la API: falta la confirmación de la interfaz.

## Pendiente

- **Pendiente:** no hay pantalla de memoria en `desktop/src` (2da8bef); ver, corregir y borrar desde la interfaz no es posible todavía, solo existe la API.
- **Pendiente:** olvidar desde la interfaz no funciona hasta enchufar la puerta de confirmación real de `drakter/seguridad`; sigue usándose `DenyAllGate`, que no borra nada (`router.py`, `CONTRACT.md`, 2da8bef).
- **Pendiente:** OpenViking no está conectado: `openviking.py` es un hueco cerrado; hoy el motor es SQLite con FTS5. Ver [hermes-y-openviking](../installation/hermes-y-openviking.md).
- **Pendiente:** el router no está conectado a `main.py` (2da8bef). Las tablas `memory_*` ya están numeradas en `0010_memory_improvement.sql`; `schemas/ddl_memory.sql` queda como propuesta original y el `CONTRACT.md` aún la cita.
- Discrepancia: `memory/README.md` habla de OpenViking "con capas L0/L1/L2" como destino; el código solo tiene SQLite.
