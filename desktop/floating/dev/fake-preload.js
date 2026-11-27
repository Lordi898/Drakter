// Drakter (solo desarrollo): un window.drakterFloat falso con la forma de docs/floating/CONTRACT.md §4.3, para abrir la
// página flotante en un Chromium normal sin Electron main ni la extensión GNOME. Hace de main: contesta a ui_ready
// (§4.2 paso 5), manda el puntero (el ratón real o uno simulado), __roamieSafe, y registra cada invoke en el panel.
// No se empaqueta: electron-builder solo copia desktop/floating sin dev/.
// SPDX-License-Identifier: AGPL-3.0-only
(() => {
  const CMDS = new Set(['sidecar_send', 'set_hot', 'set_hit_rects', 'set_typing', 'esc_watch', 'ink_wait', 'buddy']);
  const CHANNELS = new Set(['host', 'ptr', 'click', 'safe', 'moved', 'voice']);
  const listeners = new Map();
  const state = { inkWait: false, typing: false, esc: false, rects: [], log: [], ready: false, onSidecar: [] };

  const emit = (ch, ...a) => { for (const cb of listeners.get(ch) ?? []) { try { cb(...a); } catch (err) { console.error(err); } } };
  let lastWhat = '';
  const log = (dir, what) => {
    // Las ráfagas (deltas de texto, niveles de voz) se cuentan en una sola línea.
    if (what === lastWhat && state.log.length) { const l = state.log[state.log.length - 1]; l[3] = (l[3] ?? 1) + 1; window.__fakeLog?.(dir, what, l[3]); return; }
    lastWhat = what;
    state.log.push([performance.now(), dir, what]);
    if (state.log.length > 200) state.log.shift();
    window.__fakeLog?.(dir, what);
  };
  const host = (m) => { log('→', m.kind === 'agent' ? `agent ${m.e?.type}` : m.kind === 'voice' ? `voice ${m.type}${m.state ? ' ' + m.state : ''}` : m.kind); emit('host', m); };

  // Lo que hace main al recibir ui_ready (§4.2 paso 5 y §11.4).
  const onReady = () => {
    state.ready = true;
    host({ kind: 'look', look: 'jarvis' });
    host({ kind: 'size', size: 'default' });
    host({ kind: 'sound', on: true });
    host({ kind: 'volume', v: 1 });
    host({ kind: 'notch', on: false });
    host({ kind: 'summon', show: true });
    host({ kind: 'greet' });
  };

  window.drakterFloat = Object.freeze({
    config: Object.freeze({ unit: 400, only: Object.freeze(['sidekick']), autosound: true, linux: 'wayland' }),
    invoke(cmd, args) {
      if (!CMDS.has(cmd)) { log('✗', `cmd rechazado: ${cmd}`); return Promise.reject(new Error(`cmd no permitido: ${cmd}`)); }
      args = args ?? {};
      switch (cmd) {
        case 'sidecar_send': {
          const msg = args.msg ?? {};
          log('←', `sidecar ${msg.type}${msg.id != null ? ' ' + msg.id : ''}${msg.result ? ' ' + msg.result : ''}${msg.text !== undefined ? ' «' + msg.text + '»' : ''}`);
          if (msg.type === 'ui_ready') setTimeout(onReady, 30);
          for (const f of state.onSidecar) { try { f(msg); } catch (err) { console.error(err); } }
          break;
        }
        case 'set_hit_rects': state.rects = Array.isArray(args.rects) ? args.rects : []; break;
        case 'set_typing': state.typing = !!args.on; log('←', `set_typing ${state.typing}`); break;
        case 'esc_watch': state.esc = !!args.on; break;
        case 'ink_wait': state.inkWait = !!args.on; log('←', `ink_wait ${state.inkWait}`); break;
        case 'buddy': return Promise.resolve(false);
        default: break;
      }
      return Promise.resolve(undefined);
    },
    on(ch, cb) {
      if (!CHANNELS.has(ch) || typeof cb !== 'function') throw new Error(`canal no permitido: ${ch}`);
      if (!listeners.has(ch)) listeners.set(ch, []);
      listeners.get(ch).push(cb);
    },
  });

  // El puntero: el ratón real de esta ventana, o uno simulado (fake-panel.js) que se dibuja como una cruz.
  const ptr = { sim: false, x: 0, y: 0 };
  const sendPtr = (x, y) => { ptr.x = x; ptr.y = y; emit('ptr', x, y, performance.now()); window.__fakeCursor?.(x, y); };
  addEventListener('pointermove', (e) => { if (!ptr.sim) sendPtr(e.clientX, e.clientY); }, true);
  // ink_wait: como main con Button(1, pressed) mientras la página espera un clic (§4.3 float:click).
  addEventListener('pointerdown', (e) => { if (state.inkWait && !e.target.closest?.('#fake-panel')) emit('click', e.clientX, e.clientY, performance.now()); }, true);
  // Barra superior de GNOME simulada: 32 px arriba (§4.2 __roamieSafe).
  const safe = () => emit('safe', { top: 32, left: 0, bottom: 0, right: 0, ox: 0, oy: 0, notch: null });
  addEventListener('load', safe);
  setInterval(safe, 2000);

  window.__fake = { emit, host, state, ptr, sendPtr, safe, log };
})();
