# Instalación de Drakter

Guías para instalar Drakter en esta máquina. Se contrastaron con `drakter/integracion` (`2e05ba6`) el 2026-11-13; el `.deb` se construyó en esta máquina, pero nadie las ha ejecutado de principio a fin: lo que no se ha podido probar lleva `NO COMPROBADO` y lo que falta, `Pendiente`.

## Orden de lectura

1. [Instalar](instalar.md): requisitos, dependencias, arranque y comprobación.
2. [Clave de API](clave-api.md): `~/.config/drakter/.env`, con permisos 600 y sin espacio tras el igual.
3. [Sandbox de Electron](sandbox-electron.md): paso opcional con sudo. En esta máquina hace falta para ejecutar con sandbox desde el repositorio.
4. [Hermes y OpenViking](hermes-y-openviking.md): el agente, en su propio venv.
5. [Voz](voz.md): entorno, modelos y prueba de micrófono.
6. [Paquete .deb](paquete-deb.md): instalador; construido, sin instalar todavía.

Uso diario: [usage](../usage/README.md).
