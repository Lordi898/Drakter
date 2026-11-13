# Perfiles de voz

> **Estado:** preparado, sin voz en vivo. Esto deja listos el archivo de IDs, su validación, las herramientas del agente y el ajuste `voice_profile`. La voz con Fish Audio sobre Pipecat se construye después y leerá lo mismo. Hoy puedes comprobar y probar tus voces con `scripts/voces.sh`.

## Dónde van los IDs: un único sitio

`~/.config/drakter/voces.toml` (respeta `XDG_CONFIG_HOME`). Está **fuera del repositorio**, es tuyo y no se sube a ningún sitio. Si no existe, Drakter lo crea solo desde la plantilla (`contracts/python/drakter_contracts/templates/voces.template.toml`), con los IDs vacíos y permisos `600`. Nunca lo sobrescribe.

Viene con dos perfiles: `natural` (el de por defecto) y `neutral`.

## Poner un ID

1. En [fish.audio](https://fish.audio) abre la voz que quieres.
2. El ID es el trozo de la URL `fish.audio/.../m/<ID>/` (32 caracteres, solo `0-9` y `a-f`).
3. Pégalo en `reference_id` del perfil correspondiente.

Para **cambiar una voz basta con cambiar el ID**. El archivo se recarga solo al guardarlo, sin reiniciar. Un perfil con el ID vacío queda «sin configurar» y no rompe nada.

## Añadir un perfil

Copia un bloque `[perfiles.<nombre>]` entero. El nombre va en minúsculas, números y `_`. Rellena `reference_id`, `descripcion` y `alias` (las palabras con las que lo pedirás: «la seria», «la otra»). Los alias no distinguen mayúsculas ni tildes y no pueden repetirse entre perfiles.

## Qué se valida

- El modelo es `s2.1-pro-free`, fijado. Con otro modelo Fish cobra, así que se rechaza salvo que pongas tú `allow_paid = true` en `[tts]`.
- El ID tiene 32 caracteres hexadecimales.
- El perfil por defecto existe y los alias son únicos.
- Si algo está mal, el mensaje dice qué y dónde, sin repetir tus IDs.

## Comprobar y probar

```bash
scripts/voces.sh listar               # perfiles, alias, ID enmascarado y estado
scripts/voces.sh comprobar            # consulta a Fish cada voz: existe, estado "trained", idioma
scripts/voces.sh probar neutral "Hola, soy yo"   # genera una frase corta y la reproduce
                                                 # (un texto que empieza por "-": ponlo tras --)
```

`comprobar` y `probar` usan `FISH_API_KEY` de `~/.config/drakter/.env` (nunca se imprime). `probar` fija `s2.1-pro-free` en la cabecera `model` y se niega a usar un modelo fuera de la lista blanca. Con la plantilla vacía, `listar` y `comprobar` te dicen «Pon los IDs en <ruta>».

## Cambiar de voz por chat

Dile a Drakter «cambia tu voz a la neutral» o «pon la otra voz»; pregunta «¿qué voces tienes?» para ver la lista. Entiende el nombre o un alias, con o sin artículo («neutral», «la neutral», «la voz seria»). Por voz funcionará cuando exista la voz con Pipecat. Usa dos herramientas: `voice_list_profiles` y `voice_set_profile`. Si el perfil no tiene ID, responde que está sin configurar. El cambio no pide confirmación (solo guarda qué perfil está activo), pero queda auditado. En una sesión que ha leído documentos o memoria el backend sí lo pedirá, como con cualquier escritura.

El perfil activo es el ajuste `voice_profile` (se guarda en el backend, por nombre, nunca el ID) y se publica `voice.profile_changed`. **Hoy solo se guarda la preferencia:** ningún TTS usa todavía el perfil (Pipecat y Fish no están), así que la voz que suena no cambia y la herramienta lo dice (`applied_to_voice: false`). El mensaje IPC `voice.set_profile {profile}` está definido en `contracts` pero **no se envía**: lo cableará el trabajo de Pipecat. El evento solo lo publica la herramienta, no `POST /api/v1/settings/voice_profile`.
