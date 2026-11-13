# Skills del agente

Hoy estas Skills son **inertes**: el toolset `skills` de Hermes está apagado porque arrastra `skill_manage`, una vía de persistencia que el agente podría usar para escribir sus propias instrucciones (H-06 / F14).

Solo se activarán con `skill_manage` bloqueado y dejando constancia en `docs/DECISIONS.md`.

Mientras tanto, las herramientas ya llevan su descripción y esquema por MCP (`mcp__drakter__<tool>`), que es lo que el modelo usa. La validación, los permisos y las confirmaciones residen siempre en el backend; las Skills no los duplican.

Formato: `<nombre>/SKILL.md` con frontmatter YAML (`name`, `description`, `version`, `metadata.hermes.tags`) compatible con Hermes v0.22.7. Los nombres marcados PROPUESTA (memoria y configuración) aún no tienen lista cerrada en el plan.
