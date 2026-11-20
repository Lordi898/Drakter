# Skills del agente

Procedimientos breves, en castellano, para usar bien las herramientas del backend en cada dominio. No añaden lógica ni herramientas: las skills guían y el backend valida.

**Cómo llegan al agente (solo lectura):** `backend/app/integrations/hermes/home.py` (`render_skills`) las compila al final de `SOUL.md` al generar el home de Hermes. Quedan en el manifiesto con su hash y se verifican antes de cada arranque. El toolset `skills` de Hermes sigue apagado (arrastra `skill_manage`), así que el agente no puede crear, cambiar ni borrar skills. Ver `docs/DECISIONS.md` «Skills de solo lectura compiladas en SOUL.md».

Formato: `<nombre>/SKILL.md` con frontmatter YAML (`name` igual a la carpeta, `description`, `version`, `metadata.hermes.tags`) y cuerpo con encabezados `##`. Nombre `^[a-z][a-z0-9-]{2,47}$`, como mucho 6000 caracteres. `drakter-basics` va primero (reglas comunes); el resto, por nombre. Un cambio aquí cambia el hash de SOUL.md: es un cambio de producción y pasa por revisión.
