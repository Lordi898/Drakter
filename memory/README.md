# memory/

Plantillas y documentación de la memoria. **Aquí no hay datos del usuario:** lo vivo está en `DRAKTER_DATA_DIR`, fuera del repositorio.

## Cuatro capas (tipo de memoria)

| Capa | Qué guarda | Dónde vive hoy | Dónde vivirá con OpenViking |
|---|---|---|---|
| Trabajo | Sesión y operaciones activas | `DRAKTER_DATA_DIR/memory/working/` y sesión de Hermes | Sesión de Hermes |
| Episódica | Acontecimientos, casos, decisiones | `memory_records` (`events`, `cases`) | `viking://user/<usuario>/memories/` |
| Semántica | Hechos y preferencias estables | `memory_records` (`profile`, `preferences`, `entities`) y `USER.md` | Igual, más `USER.md` para lo esencial |
| Procedimental | Procedimientos y patrones | Skills y `memory_records` (`patterns`) | Skills de Hermes y `patterns` |

L0, L1 y L2 son **nivel de detalle**, no tipo: `abstract` (256 caracteres), `overview` (4.000) y `content`.

## Datos en ejecución

- Registros, conflictos e índice FTS5: tablas `memory_*` de la base del backend.
- Registros de operación: `logs/memory_operations.log` y `logs/retrieval.log`, sin contenido.

Los archivos de esta carpeta son contexto legible y auditable, no sustituyen a los motores de memoria (`MASTER_PLAN.md` §11).

## Código

`backend/app/integrations/memory/`; contrato en su `CONTRACT.md`.
