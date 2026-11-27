# Almacén

> **Estado:** integrado en la integración de la v1 (`2e05ba6`, hoy en `main`): pantalla **Almacén** en la navegación y API `storage` montada. El selector de carpetas (`pickDirectory`) sigue sin existir en el puente de Electron. Las notas «Pendiente» del cuerpo se escribieron sobre `drakter/build` (`2da8bef`) y alguna puede estar ya resuelta. NO COMPROBADO en la app real (ver «Estado de la integración» en [README](README.md)).

El Almacén es un catálogo de tus archivos, enlaces y notas. Drakter puede buscarlos y abrirlos cuando se lo pides. Catalogar no copia ni mueve nada: el archivo original se queda donde está.

## Cómo funciona

- **Ubicaciones:** carpetas de tu disco que registras. Son de solo lectura.
- **Recursos:** cada nota, enlace o archivo del catálogo. Tipos: Imagen, Documento, PDF, Texto, Código, Enlace, Nota, Apunte, Comprimido, Otro.
- **Carpetas:** el árbol lógico del catálogo (panel izquierdo). Es independiente de las carpetas del disco.
- Drakter no escribe nunca en tus ubicaciones. No hay subir ni mover archivos reales: el código v1 no lo hace.

## Uso diario

La pantalla se llama **Almacén**. Arriba tienes el botón **Añadir recurso** y la barra de búsqueda.

### Añadir un recurso
1. Pulsa **Añadir recurso**. Elige **Nota**, **Enlace** o **Archivo**.
2. Escribe el **Título** (máx. 300 caracteres).
3. Según el tipo:
   - Nota: **Texto de la nota**.
   - Enlace: **Dirección (http o https)**.
   - Archivo: elige la **Ubicación** y escribe la **Ruta dentro de la ubicación**, por ejemplo `carpeta/documento.pdf`. Antes necesitas una ubicación activa.
4. Pulsa **Añadir**.

### Registrar una ubicación
1. En el panel **Ubicaciones**, pulsa **Añadir** y elige la carpeta.
2. Aparece el aviso «Ubicación añadida»: es de solo lectura y Drakter no puede leerla hasta que lo permitas.
3. Para permitirlo, activa **Permitir que Drakter lea esta ubicación**. El interruptor **Activa** la habilita o deshabilita.
4. Pulsa el icono **Escanear** de la ubicación para catalogar sus archivos. El aviso resume cuántos son nuevos, actualizados, movidos y no encontrados.

### Explorar y buscar
- **Todos los recursos** y el **Árbol de carpetas** filtran la lista.
- Busca en **Buscar por título, descripción o contenido** (espera 300 ms tras escribir). Los filtros **Todos los tipos** y **Cualquier disponibilidad** (Disponible, No encontrado, Movido, Inaccesible, Acceso denegado) se combinan con la búsqueda.
- **Cargar más** pagina la lista. Los archivados no salen en la búsqueda.

### Ver un recurso
Al elegirlo se abre el detalle a la derecha, con insignias de tipo, disponibilidad e índice (Sin indexar, Pendiente, Indexado, Con error, Omitido).
- **Descripción** (máx. 4000 caracteres) y **Guardar descripción**.
- **Etiquetas**: escribe en **Nueva etiqueta** (máx. 60 caracteres) y pulsa **Añadir**.
- **Leer** muestra el contenido; **Leer más** continúa. Cada lectura trae por defecto 8000 caracteres, tope 20 000.
- **Archivar** lo oculta de la lista.

### Indexar
- **Indexar el contenido** (interruptor): permite encontrarlo por lo que dice dentro. Solo vale para texto, código, PDF y documentos; nunca para comprimidos. Apagado, solo se busca por título, tipo, ruta, descripción y etiquetas.
- **Actualizar índice**: reindexa ese recurso.
- Icono **Refrescar el índice** del panel Ubicaciones: revisa todos los archivos y reindexa los modificados. Informa de revisados, reindexados, no encontrados y con error.

### Mover
No existe mover desde la pantalla. Si mueves un archivo en el disco, **Escanear** lo reconoce por su identidad de archivo (dev/inodo) dentro de la misma ubicación, actualiza la ruta y lo deja como Disponible. Si falta, queda **No encontrado**.

## Qué pide confirmación
- **Eliminar** un recurso: el diálogo «¿Eliminar «...» del almacén?» solo lo quita del catálogo; el archivo original no se borra. Si tiene relaciones, el botón pasa a **Desvincular y eliminar**.
- **Quitar** una ubicación (diálogo «¿Quitar «...» del almacén?»): solo si ya no tiene recursos; si los tiene, el servidor responde `has_dependents`. Tus archivos no se tocan.
- Quitar una carpeta del árbol también requiere confirmación en el servidor.
- Cuando se pide, la interfaz muestra «Espera aprobación: ...» y no hace ningún cambio. Si el agente lo intenta, la aprobación es siempre desde la interfaz.

## Ubicaciones permitidas
- Se rechazan symlinks en la ruta, `/` y toda la carpeta personal.
- Nunca se sirve nada de `~/.ssh`, `~/.gnupg`, `~/.aws`, `~/.config/drakter`, `~/.hermes`, `~/.mozilla`, `~/.config/google-chrome`, `~/.config/chromium` ni los directorios de datos y ejecución de Drakter, aunque queden dentro de una ubicación. Tampoco `.env`, `.env.*`, `.ssh` ni `.gnupg` dentro de una raíz.
- Rutas relativas sin `..`, sin absolutas, sin NUL ni caracteres de control. No se siguen enlaces simbólicos. Se omiten archivos con más de un enlace duro.

## Límites reales (valores iniciales, sin medir)
| Qué | Límite |
|---|---|
| Archivo leído | 64 MB |
| Texto leído | 8 MB |
| Caracteres por lectura | 20 000 |
| Texto indexado por recurso | 200 000 caracteres |
| Escaneo | 50 000 entradas, profundidad 32 |
| PDF | 2000 páginas |
| Enlace | 4 MB, 10 s, 3 redirecciones |
| Nota | 1 000 000 caracteres; 32 etiquetas por recurso |

**Comprimidos** (zip, tar, tar.gz, tar.bz2, tar.xz): solo se lista su contenido, nunca se extrae. Límites: 512 MB el archivo, 10 000 entradas, 2 GB totales, 100 MB por entrada, ratio de compresión 100, profundidad 16, ruta de 1024 bytes. Si se supera uno: «El comprimido supera los límites permitidos.»

**Enlaces:** solo http/https en los puertos 80 y 443, sin credenciales; se rechazan IP no públicas (loopback, privadas, etc.). Solo se lee texto, HTML y JSON.

## Datos no confiables
El contenido de documentos, enlaces y notas es dato sin verificar. Al leerlo, el detalle avisa «Contenido sin verificar» y Drakter no lo trata como instrucciones: no puede cambiar sus reglas ni los permisos. El agente solo lee ubicaciones con **Permitir que Drakter lea esta ubicación** activado, no puede gestionar ubicaciones ni borrar recursos y no acepta rutas: solo crea enlaces y notas.

## Problemas frecuentes
- «El almacén no está conectado»: no hay servicio local. Pulsa **Reintentar la conexión**.
- «Esa ruta no está permitida.»: la ubicación o archivo cae en una ruta denegada.
- «Ya existe un recurso igual.»: duplicado.
- «Este recurso ha cambiado mientras lo editabas...»: otro cambio llegó antes; se recarga solo.
- «El recurso no está disponible ahora mismo.»: la ubicación está desactivada.
- «Tiene relaciones con otros elementos.»: usa **Desvincular y eliminar**.

## Pendiente
- **Pendiente:** el botón **Añadir** de ubicaciones necesita `pickDirectory` en el puente de Electron. Sigue sin existir: ni `drakter/build` (2da8bef) ni `drakter/electron-host` lo definen (solo lo usa el renderer de `drakter/almacen-relaciones`, `modules/storage/bridge.ts`): sale desactivado con el texto «Elegir una carpeta necesita el selector nativo...». No hay otra forma en pantalla de registrar una carpeta.
- **Pendiente:** la interfaz no envía `confirmation_id` al reintentar un borrado, y el diálogo nativo de aprobación solo existe en el host de Electron de `drakter/build` (2da8bef), no en esa rama. Eliminar recursos o quitar ubicaciones puede quedarse en «Espera aprobación». NO COMPROBADO.
- **Pendiente:** no hay botón para crear ni mover carpetas del árbol (existe en el servidor).
- Enlaza con [Relaciones](relaciones.md) y [Seguridad y copias](seguridad-y-copias.md).
