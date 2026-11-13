# Política de seguridad

## Versiones con soporte

Drakter está en pre-release. Solo recibe arreglos de seguridad la rama `main` (y la última versión publicada a partir de ella).

| Versión | Soporte |
|---|---|
| `main` / 0.1.x | ✅ |
| Anteriores | ❌ |

## Cómo reportar una vulnerabilidad

**No abras un issue público ni un PR con los detalles.**

Usa el reporte privado de vulnerabilidades de GitHub: [Report a vulnerability](https://github.com/Lordi898/Drakter/security/advisories/new) (pestaña *Security* del repositorio). Solo lo ve el propietario.

> Mientras el repositorio sea privado, GitHub no ofrece el reporte privado a terceros: si tienes acceso como colaborador, avisa al propietario (@Lordi898) por un canal privado. El reporte privado se activará al hacer público el repositorio.

Incluye, si puedes:

- Qué componente afecta (`backend/`, `desktop/`, agente/Hermes, memoria, almacén, voz…) y el commit o versión.
- Pasos para reproducirlo, o una prueba de concepto mínima.
- El impacto que esperas (lectura o escritura de datos, saltarse una confirmación, inyección de instrucciones, salida del directorio permitido…).

Qué esperar: acuse de recibo en unos 7 días y una valoración inicial en unos 14. Es un proyecto personal mantenido por una persona, así que los plazos son orientativos. Te avisaremos cuando haya un arreglo y, si quieres, te mencionaremos en el aviso.

## Modelo de amenazas, en breve

Drakter es local-first y para un solo usuario. Lo que se considera vulnerabilidad:

- Acceso al backend desde fuera de `127.0.0.1` o sin el token que reparte Electron.
- Saltarse una confirmación de una acción destructiva o masiva, o el registro de auditoría.
- Que un documento del almacén, una página web o la memoria recuperada consigan cambiar las instrucciones del agente o las reglas de seguridad (inyección de instrucciones).
- Lectura o escritura fuera de las rutas permitidas, o comprimidos que se saltan los límites de tamaño, número o profundidad.
- Que la automejora cambie producción, permisos, confirmaciones o auditoría sin aprobación.
- Fugas de claves de API u otros secretos a logs, auditoría o al modelo.

Fuera de alcance: ataques que ya requieren control total de la cuenta del usuario en la máquina, y el comportamiento de servicios de terceros (Anthropic, Hermes) fuera de cómo los usa Drakter.

## Problemas conocidos

La revisión adversarial de la v1 (banco de 200 ataques en `tests/security/`: 169 BLOCKED / 12 BREACH / 19 N/A / 0 ERROR) dejó brechas de diseño conocidas, mitigadas o de bajo riesgo, documentadas en:

- [DECISIONS: Brechas del red-team conocidas al cierre](docs/DECISIONS.md#2026-11-13-brechas-del-red-team-conocidas-al-cierre): INJ-05, CONF-46/INJ-26 (la contaminación de la sesión no persiste al reiniciar), INJ-11/25 (`TurnRequest` sin canal de datos aparte) y FILE-DB-02 (TOCTOU de bajo riesgo).
- [DECISIONS: Revisión adversarial de seguridad cerrada](docs/DECISIONS.md#2026-11-13-revisión-adversarial-de-seguridad-cerrada).

No hace falta reportarlas de nuevo; sí es útil cualquier forma nueva de explotarlas.
