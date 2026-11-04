# Personaje de Drakter (sustituto SVG)

Sustituto SVG del `.riv`, sin dependencias ni compilación. Abre `index.html` como archivo o sírvelo estático. `?state=nombre` fija el estado inicial; las teclas 1-9 lo cambian.

## API

```html
<script src="character.js"></script>
<script>
  const drakter = createCharacter(document.getElementById('sitio'), { state: 'idle' });
  drakter.setState('thinking'); // true
  drakter.setState('dormido');  // false y console.warn, no cambia nada
  drakter.getState();           // 'thinking'
  drakter.destroy();            // quita el SVG y deja de animar
</script>
```

- `index.html` expone además `window.setState(nombre)`, con el mismo contrato, sobre el personaje grande.
- `DRAKTER_STATES` es el catálogo cerrado: `idle`, `listening`, `thinking`, `speaking`, `executing`, `success`, `error`, `interrupted`, `offline`.
- El estado solo cambia con `setState`. `success`, `error` e `interrupted` se asientan por dentro, pero no vuelven solos a `idle`.
- El SVG lleva `aria-hidden`: el texto accesible del estado lo pone quien lo usa.
- Con `prefers-reduced-motion` no hay respiración, parpadeo, chisporroteo ni partículas en movimiento. Humo y chispas quedan fijos y `speaking` deja la boca abierta.

## Cómo funciona

`STATES` declara para cada estado solo valores objetivo de `PARAMS`, una velocidad `rate` y, si hace falta, `settle` (un objetivo que decae al entrar). Un único bucle `requestAnimationFrame`, compartido por todas las instancias, acerca los valores actuales a los objetivos y redibuja. Por eso una transición puede cortarse a mitad sin saltos.

## Portar a React

`createCharacter` ya tiene la forma de un efecto:

```tsx
function Character({ state }: { state: CharacterState }) {
  const host = useRef<HTMLDivElement>(null);
  const rig = useRef<ReturnType<typeof createCharacter>>();
  useEffect(() => {
    rig.current = createCharacter(host.current!, { state });
    return () => rig.current?.destroy();
  }, []);
  useEffect(() => { rig.current?.setState(state); }, [state]);
  return <div ref={host} />;
}
```

Convierte `character.js` en módulo cambiando la envoltura `(function (global) {...})(window)` por exports. El resto de la app solo debe conocer `<Character state={...} />`.

## Pasar a Rive

Crea una máquina de estados con una entrada numérica por cada clave de `PARAMS`, con el mismo nombre y rango, y una entrada `state` con los nueve valores. Traslada cada bloque de `STATES` a un estado de la máquina, `rate` a la duración de la transición y `settle` a una animación de entrada. Las partículas y el generador de articulación pasan a animaciones internas; `talk` queda como mezcla. Cuando haya voz, la apertura de la boca debe venir de la intensidad del audio y no del generador aleatorio. Después cambia el interior de `<Character>` por el `.riv` manteniendo la misma prop `state`.
