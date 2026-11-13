# Uso diario de Drakter

Una guía por módulo. Cada una abre con su estado respecto a `drakter/integracion` (`2e05ba6`), que reúne todas las ramas. El backend monta solo cada `backend/app/api/<módulo>.py`; voz tiene código, pero su router aún no se monta, y automejora no tiene pantalla.

## Estado de la integración

Que algo esté en el código no significa que funcione ya en la app. En la pasada integrada del cierre (`scripts/verify-all.sh`, con LLM de pruebas, 2026-11-13) los módulos de datos respondieron bien por API, pero fallaron la sesión de chat (`agent_unavailable`), el borrado sin confirmar (503 en vez de 409) y la apertura de la ventana por CDP. Estas guías salen de leer el código; nadie las ha seguido paso a paso en la app.

Para instalar, ve a [installation](../installation/README.md).

## Día a día

- [Hoy y ajustes](hoy-y-ajustes.md)
- [Recordatorios](recordatorios.md)
- [Búsqueda](busqueda.md)
- [Chat y personaje](chat-y-personaje.md)
- [Voz](voz.md)
- [Perfiles de voz](voces.md): los IDs de Fish Audio, cómo cambiarlos y cambiar de voz

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
