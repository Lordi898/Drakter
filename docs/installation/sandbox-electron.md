# Sandbox de Electron en modo desarrollo (opcional, con sudo)

> **Estado:** contrastada con `drakter/integracion` (`2e05ba6`): `scripts/check-env.sh` (lo avisa en esta máquina), `scripts/dev.sh`, el lanzador y el `.deb` ya construido (ver [paquete-deb.md](paquete-deb.md)). NO COMPROBADO: el paso con sudo no se ha ejecutado, porque esta sesión no tiene sudo.

Este paso solo importa si lanzas Drakter desde el repositorio: `scripts/dev.sh`, `npm run dev` o `scripts/drakter`. Si instalas el paquete `.deb`, no lo necesitas: véase [paquete-deb.md](paquete-deb.md).

Para saber si te afecta, ejecuta `scripts/check-env.sh`. Avisa cuando Electron va a abortar por su sandbox.

## Qué pasa si no lo haces

`desktop/electron/main/index.ts` llama a `app.enableSandbox()` y la ventana usa `sandbox: true`, así que el sandbox de Chromium está activo. Electron necesita uno de estos dos mecanismos para arrancarlo:

- Espacios de nombres de usuario sin privilegios. En esta máquina `kernel.unprivileged_userns_clone=1`, pero `kernel.apparmor_restrict_unprivileged_userns=1` los restringe a programas con perfil AppArmor, y el Electron de `node_modules` no tiene perfil.
- El binario `desktop/node_modules/electron/dist/chrome-sandbox` con SUID root.

Si el binario no es SUID (lo normal tras `npm ci`, pues pertenece a tu usuario) y el kernel restringe userns, Electron aborta al arrancar con un error sobre `chrome-sandbox`. `README.md` y `scripts/check-env.sh` lo dan por hecho en esta máquina. El binario de Electron contiene el texto ` is owned by root and has mode 4755.`, que es lo que pide el mensaje. `scripts/drakter` ni siquiera lo intenta: se niega a arrancar y avisa del «paso U-2».

## El paso con sudo

Ejecútalo tú, a mano, desde `desktop/`:

```
sudo chown root:root node_modules/electron/dist/chrome-sandbox
sudo chmod 4755 node_modules/electron/dist/chrome-sandbox
```

Comprueba:

```
stat -c '%U %a' node_modules/electron/dist/chrome-sandbox
```

Esperado: `root 4755`. Luego arranca `scripts/dev.sh` sin variables extra.

El lanzador acepta exactamente este estado: propietario root y modo 4755.

## Sin sudo: solo para desarrollo

Son dos salidas que **desactivan el sandbox** en esa sesión. Sirven para probar, no para el uso diario:

- `ELECTRON_DISABLE_SANDBOX=1 scripts/dev.sh`. Según `README.md`, es lo que se ha probado.
- `DRAKTER_DEV_NO_SANDBOX=1 scripts/drakter`. El lanzador añade `--no-sandbox` e imprime un aviso.

## Repetirlo y deshacerlo

- Cada `npm ci` (o reinstalar `electron`) reemplaza el binario y pierde el propietario y el bit SUID: repite los dos comandos y vuelve a comprobar con `stat`.
- Deshacer: `sudo chown "$USER":"$(id -gn)" node_modules/electron/dist/chrome-sandbox` y `chmod 755 node_modules/electron/dist/chrome-sandbox`. O borra `node_modules` y haz `npm ci`. **NO COMPROBADO.**

## Por qué es opcional y qué alternativas hay

- Un binario SUID root es una superficie privilegiada en tu equipo. Por eso se deja a tu decisión.
- Alternativa soportada: el `.deb`. Según `desktop/electron-builder.README.md` (`drakter/automejora`), su `postinst` deja `chrome-sandbox` en `4755` solo si el kernel no soporta userns; si los soporta lo deja en `0755` e instala un perfil AppArmor `/etc/apparmor.d/drakter`, que es lo que permite el sandbox con `apparmor_restrict_unprivileged_userns=1`. Ese README no está probado.
- AppImage: no puede tener SUID y, con esta restricción y sin perfil, falla; no se soporta.
- Perfil AppArmor propio para el Electron de `node_modules`: **Pendiente**. El lanzador lo aceptaría (`/etc/apparmor.d/*drakter*` o `*electron*`), pero ninguna rama lo trae.
- **Nunca sin sandbox** para uso real. Tampoco quites `chrome-sandbox`.

## Pendiente

- Probar el paso con sudo en esta máquina. Debes hacerlo tú: ejecuta los dos comandos, comprueba con `stat` y arranca `scripts/dev.sh` sin variables extra.
- Siguiente: [clave-api.md](clave-api.md).
