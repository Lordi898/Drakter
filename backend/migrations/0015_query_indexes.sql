-- Checklist 17 «Optimizar consultas SQLite»: índices que faltaban en las rutas más usadas.
-- Medido con EXPLAIN QUERY PLAN sobre una base sembrada (5.000 tareas, 3.000 eventos,
-- 3.000 relaciones, 3.000 recuerdos, 40 hábitos con un año de registros). Cifras en DECISIONS.md.
-- Solo índices: no cambia datos ni restricciones. No hay migración inversa: «revertir» es
-- restaurar la copia previa del migrador.

-- «Hoy» busca los registros de hábitos por fecha (`occurrence_date IN (...)`); el único
-- índice era (habit_id, occurrence_date) y la consulta recorría la tabla entera.
CREATE INDEX ix_habit_records_date ON habit_records (occurrence_date);

-- Recordatorios: tareas con fecha sin hora en un rango (`status IN ... AND due_date BETWEEN`).
-- ix_tasks_status_due cubre `due_at`, no `due_date`.
CREATE INDEX ix_tasks_status_due_date ON tasks (status, due_date);

-- Listado de memoria: `ORDER BY created_at DESC, seq DESC LIMIT ?`, con o sin filtro de
-- estado, sin ordenar en un B-tree temporal. El compuesto sustituye al de solo `status`,
-- que es su prefijo.
CREATE INDEX ix_memory_records_created ON memory_records (created_at, seq);
CREATE INDEX ix_memory_records_status_created ON memory_records (status, created_at, seq);
DROP INDEX ix_memory_records_status;
