# Uso diario de Drakter

Una guía por módulo. Cada una abre con su estado respecto a `drakter/integracion` (`7fd30e1`), que reúne todas las ramas. El backend monta solo cada `backend/app/api/<módulo>.py`; voz y automejora tienen código, pero sus routers aún no se montan.

## Estado de la integración

Que algo esté en el código no significa que funcione ya en la app. En la pasada integrada del cierre (`scripts/verify-all.sh`, con LLM de pruebas, 2026-11-13) los módulos de datos respondieron bien por API, pero fallaron la sesión de chat (`agent_unavailable`), el borrado sin confirmar (503 en vez de 409) y la apertura de la ventana por CDP. Estas guías salen de leer el código; nadie las ha seguido paso a paso en la app.

Para instalar, ve a [installation](../installation/README.md).

## Día a día

- [Hoy y ajustes](hoy-y-ajustes.md)
- [Recordatorios](recordatorios.md)
- [Búsqueda](busqueda.md)
- [Chat y personaje](chat-y-personaje.md)
- [Voz](voz.md)

## Organización

- [Tareas y proyectos](tareas-y-proyectos.md)
- [Hábitos](habitos.md)
- [Calendario](calendario.md)
- [Asignaturas](asignaturas.md)

## Conocimiento

- [Almacén](almacen.md)
- [Relaciones](relaciones.md)
- [Memoria](memoria.md)

## Sistema

- [Seguridad y copias](seguridad-y-copias.md)
- [Automejora](automejora.md)
