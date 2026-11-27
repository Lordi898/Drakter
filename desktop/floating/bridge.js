// Drakter: puente entre el preload de la ventana flotante (window.drakterFloat) y la página de Roamies.
// Hace el papel del shell Tauri de Roamies: define los globales de configuración que core.js, sfx.js, voice-out.js,
// notch.js y host.js leen al cargar, window.__TAURI__.core.invoke (lo único que usa host.js) y el cableado
// main → página hacia __roamiePtr, __roamieClick, __roamieSafe, __roamieMoved y __roamieHost (docs/floating/CONTRACT.md §11.2).
// Se carga antes que roamies/core.js. Sin drakterFloat (la página abierta sola) no hace nada y host.js tampoco.
// SPDX-License-Identifier: AGPL-3.0-only
(() => {
  const D = window.drakterFloat;
  if (!D || typeof D.invoke !== 'function' || typeof D.on !== 'function') return;
  const C = D.config ?? {};

  window.ROAMIE_UNIT = C.unit ?? 400;
  window.ROAMIE_ONLY = Array.isArray(C.only) ? [...C.only] : ['sidekick'];
  window.ROAMIE_AUTOSOUND = C.autosound ?? true;
  // 'wayland': host.js manda set_hit_rects (la extensión fija la región de entrada en el compositor). El ADAPT de
  // voice-out.js queda sustituido por drakter-voice-out.js y el notch está apagado (§11.2).
  window.ROAMIE_LINUX = C.linux ?? 'wayland';

  // Como Tauri: siempre devuelve una Promise (host.js e ink.js hacen .catch en todas las llamadas).
  const invoke = (cmd, args) => {
    try { return Promise.resolve(D.invoke(cmd, args ?? {})); } catch (err) { return Promise.reject(err); }
  };
  window.__TAURI__ = Object.freeze({ core: Object.freeze({ invoke }) });

  // Caracteres que dirá la voz en un segmento del dibujo: con ellos el shim aprende el ritmo (cps) como voice-out.js.
  const sayChars = (e) => (Array.isArray(e.beats) ? e.beats.reduce((n, b) => n + String(b?.caption ?? b?.say ?? '').length, 0) : 0);

  // Lo que llega antes de que exista la función se pierde, como en Tauri (window.__roamieHost&&__roamieHost(msg)):
  // main no manda nada hasta ui_ready.
  D.on('ptr', (x, y, t) => window.__roamiePtr?.(x, y, t));
  D.on('click', (x, y, t) => window.__roamieClick?.(x, y, t));
  D.on('safe', (s) => window.__roamieSafe?.(s));
  D.on('moved', () => window.__roamieMoved?.());
  D.on('voice', (m) => window.Roamie?.__drakterVoice?.(m));
  D.on('host', (m) => {
    if (!m || typeof m !== 'object') return;
    // Un segmento de guía con voz: el shim agrupa sus speech_id como una sola locución (§11.2, §11.5).
    if (m.kind === 'agent' && m.e && m.e.type === 'draw' && 'speech_id' in m.e) {
      const { speech_id: id, ...e } = m.e;
      if (id != null) window.Roamie?.__drakterVoice?.({ t: 'expect', id, guide: e.id, chars: sayChars(e) });
      m = { ...m, e };
    }
    window.__roamieHost?.(m);
  });
})();
