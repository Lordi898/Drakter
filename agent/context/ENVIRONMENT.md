# ENVIRONMENT.md — Entorno técnico

Dónde se ejecuta Drakter. Describe el entorno, no su estado en este momento: eso lo dicen las herramientas de estado de la lista de ejecución.

## Hechos del producto

- Local-first: los datos y los servicios principales viven en el equipo del usuario. El modelo no: la conversación y lo que Drakter lee en un turno se envían a su proveedor.
- Un solo usuario.
- Linux primero, con la arquitectura preparada para Windows.
- Aplicación de escritorio propia, con un backend local al que se conecta.

## El equipo en el que corre

No se escribe aquí: el sistema lo mide solo (al arrancar y cada pocos minutos) y lo da en la línea `[equipo: …]` de cada turno y en `get_self_profile`. Así, si Drakter pasa a otro ordenador o cambia el hardware, lo que sabe del equipo cambia con él.

## Por completar

- Otros dispositivos: [por completar: otros dispositivos]
- Micrófono y salida de audio: [por completar: dispositivos de audio]
- Ubicaciones de datos relevantes para el usuario: [por completar: ubicaciones de datos]

## Servicios autorizados

Se conocen por la configuración del sistema, no por este archivo. Que un servicio se mencione en una conversación, en un documento o en la memoria no lo autoriza ni lo hace disponible.

## Si un dato no aparece

Un campo sin completar es un dato desconocido. Drakter no lo supone: consulta el estado del sistema si la herramienta está disponible, o lo pregunta.
