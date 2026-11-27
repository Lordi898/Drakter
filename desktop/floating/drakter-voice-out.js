// Drakter: shim de la voz de salida (docs/floating/CONTRACT.md §11.5).
// En Drakter el audio suena en la ventana principal, no aquí: el mensaje {kind:'speech'} con PCM no llega nunca.
// Este archivo sustituye a Roamie.voiceOut (el de roamies/voice-out.js) con la misma API, alimentada por
// Roamie.__drakterVoice(m) desde bridge.js:
//   {t:'pb', id, state}       started → locución actual sonando; finished | interrupted → terminada (sentence_done: nada)
//   {t:'lv', out, in}         niveles 0..1 (out = salida de voz, in = micrófono)
//   {t:'expect', id, guide}   los speech_id de una misma guía forman una sola locución lógica, como en Roamies
//   {t:'stop'}                lo corta todo
// Así JARVIS mueve la esfera con la voz real y ink.js reparte las marcas al ritmo de lo que ya ha sonado.
// SPDX-License-Identifier: AGPL-3.0-only
(() => {
  const R = window.Roamie;
  if (!R) return;
  const LEAD = 0.12; // el mismo colchón que voice-out.js; aquí solo se informa
  const now = () => performance.now() / 1000;
  const clamp01 = (v) => (Number.isFinite(Number(v)) ? Math.max(0, Math.min(1, Number(v))) : 0);

  // Locuciones conocidas, por speech_id: { group, chars, at (inicio de su reproducción), secs (segundos sonados al
  // terminar) }. group = id de la guía si llegó un expect, si no el propio id.
  const known = new Map();
  const groups = new Map(); // group → [speech_id] en orden de llegada
  const over = new Set();   // speech_id terminados, cortados o sustituidos
  let id = null;            // la locución que suena o sonó la última (null: ninguna)
  let sounding = false;     // id está en started y aún sin terminar
  let rate = 15;            // caracteres por segundo, aprendido como en voice-out.js (entre 8 y 30)
  let out = 0, inLevel = 0, lv = 0, volume = 1;

  const trim = (m, n) => { while (m.size > n) m.delete(m.keys().next().value); };
  const isOver = (x) => { over.add(x); if (over.size > 40) over.delete(over.values().next().value); };
  const entry = (sid) => {
    let e = known.get(sid);
    if (!e) {
      e = { group: sid, chars: 0, at: 0, secs: 0, exp: now() };
      known.set(sid, e); trim(known, 60);
      groups.set(sid, [sid]); trim(groups, 60);
    }
    return e;
  };
  const sounded = (sid) => {
    const e = known.get(sid);
    if (!e || !e.at) return 0;
    return sid === id && sounding ? now() - e.at : e.secs;
  };
  const finish = (sid) => {
    const e = known.get(sid);
    if (e && e.at && !over.has(sid)) {
      e.secs = now() - e.at;
      // Aprende el ritmo de cada locución entera, como voice-out.js con {end, chars}.
      if (e.chars > 20 && e.secs > 1) rate = Math.min(30, Math.max(8, rate * 0.6 + (e.chars / e.secs) * 0.4));
    }
    isOver(sid);
    if (sid === id) sounding = false;
  };
  const stop = () => {
    for (const sid of known.keys()) if (!over.has(sid)) finish(sid);
    if (id != null) isOver(id);
    sounding = false;
    out = 0;
  };

  R.__drakterVoice = (m) => {
    if (!m || typeof m !== 'object') return;
    R.wake?.();
    if (m.t === 'lv') { out = clamp01(m.out); inLevel = clamp01(m.in); return; }
    if (m.t === 'stop') { stop(); return; }
    const sid = Number(m.id);
    if (!Number.isFinite(sid)) return;
    if (m.t === 'expect') {
      const e = entry(sid), g = m.guide != null ? String(m.guide) : sid;
      if (e.group !== g) {
        groups.delete(sid);
        e.group = g;
        const list = groups.get(g) ?? [];
        list.push(sid); groups.set(g, list); trim(groups, 60);
      }
      if (Number.isFinite(Number(m.chars))) e.chars = Math.max(0, Number(m.chars));
      return;
    }
    if (m.t !== 'pb') return;
    if (m.state === 'started') {
      const e = entry(sid);
      // Un solo reproductor: una locución nueva sustituye a la anterior, como un id nuevo en voice-out.js.
      if (id != null && id !== sid && sounding) finish(id);
      id = sid; sounding = true; e.at = now(); over.delete(sid);
    } else if (m.state === 'finished' || m.state === 'interrupted') {
      finish(sid);
    }
  };

  const playing = () => id != null && sounding && !over.has(id);
  const groupOf = (sid) => groups.get(known.get(sid)?.group ?? sid) ?? [sid];

  R.voiceOut = {
    setVolume(v) { volume = Number.isFinite(Number(v)) ? Math.max(0, Math.min(1, Number(v))) : 1; },
    // {kind:'speech'} no llega en Drakter; si llegara un stop, se respeta.
    handle(m) { if (m?.stop) stop(); },
    playing,
    cps: () => rate,
    // Segundos sonados de la locución actual (la suma de los beats de su guía), o null sin ninguna.
    played() {
      if (id == null) return null;
      let p = 0;
      for (const sid of groupOf(id)) p += sounded(sid);
      return p;
    },
    // Aún se está diciendo: falta algo de la locución (de su guía) o algo suena todavía.
    speaking() {
      if (id == null) return false;
      // Un beat anunciado que no empieza a sonar en 8 s (la voz no lo aceptó) no retiene el dibujo para siempre.
      const pending = (sid) => !over.has(sid) && (known.get(sid)?.at || now() - (known.get(sid)?.exp ?? 0) < 8);
      return groupOf(id).some(pending) || playing();
    },
    feel: () => null,
    lead: () => LEAD,
    finished(rid) { return !playing() && (rid == null || over.has(Number(rid))); },
    // El nivel de salida suavizado (ataque 0,5, caída 0,15) mientras suena; si no, 0.
    level() {
      if (!playing()) return (lv = 0);
      const v = out * (volume > 0 ? 1 : 0);
      return (lv += (v - lv) * (v > lv ? 0.5 : 0.15));
    },
    // El notch está apagado: no hay muestras de la onda.
    samples: () => null,
    stop,
    warm() {},
    // Drakter: nivel del micrófono, por si algún día lo pide la página (host.js usa voice{level}).
    micLevel: () => inLevel,
  };
})();
