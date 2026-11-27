// Drakter (solo desarrollo): panel de pruebas de dev/fake-host.html. Inyecta en la página los mensajes de
// docs/floating/CONTRACT.md §11.4 tal como los mandaría Electron main, y simula una guía (draw → draw_started →
// draw_wait_done → siguiente segmento) como haría el DrawRunner del backend. window.__fake.run(nombre) los lanza
// desde fuera (las capturas automáticas).
// SPDX-License-Identifier: AGPL-3.0-only
(() => {
  const F = window.__fake;
  if (!F) return;
  const { host, emit, state } = F;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const $ = (sel) => document.querySelector(sel);
  const rectOf = (sel) => { const r = $(sel).getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; };
  const center = (r) => [r[0] + r[2] / 2, r[1] + r[3] / 2];
  const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2));
  let speechSeq = 40;

  // ---------- la voz de la ventana principal, simulada (float:voice) ----------
  let lvTimer = null;
  const levels = (on, kind = 'out') => {
    clearInterval(lvTimer); lvTimer = null;
    if (!on) { emit('voice', { t: 'lv', out: 0, in: 0 }); return; }
    const t0 = performance.now();
    lvTimer = setInterval(() => {
      const t = (performance.now() - t0) / 1000, v = Math.max(0, 0.35 + 0.35 * Math.sin(t * 9) * Math.sin(t * 2.3) + 0.2 * Math.sin(t * 23));
      emit('voice', kind === 'out' ? { t: 'lv', out: v, in: 0 } : { t: 'lv', out: 0, in: v });
      if (kind === 'in') host({ kind: 'voice', type: 'level', v });
    }, 33);
  };
  const speak = async (id, ms, turn = 't') => {
    emit('voice', { t: 'pb', id, turn, state: 'started' });
    levels(true, 'out');
    await sleep(ms);
    levels(false);
    emit('voice', { t: 'pb', id, turn, state: 'finished' });
  };

  // ---------- escenarios ----------
  const S = {};
  S.saludo = () => { host({ kind: 'summon', show: true }); host({ kind: 'greet' }); };
  S.turno = async () => {
    const sid = ++speechSeq;
    host({ kind: 'agent', e: { type: 'start', agentish: false } });
    await sleep(1400);
    host({ kind: 'agent', e: { type: 'tool', id: 'c1', anim: { tool: 'read', variant: 'search', label: 'consultando', detail: 'tus datos' } } });
    await sleep(1600);
    host({ kind: 'agent', e: { type: 'tool_end', id: 'c1', isError: false } });
    await sleep(500);
    const text = 'Hoy tienes repaso de Física a las 17:00 y la entrega de la práctica de Redes el viernes. ¿Te preparo un plan?';
    const talk = speak(sid, 4200);
    for (const w of text.match(/\S+\s*/g)) { host({ kind: 'agent', e: { type: 'text', text: w } }); await sleep(70); }
    await talk;
    host({ kind: 'agent', e: { type: 'done', speech: sid } });
  };
  S.herramientas = async () => {
    host({ kind: 'agent', e: { type: 'start', agentish: false } });
    await sleep(700);
    const tools = [
      ['c1', { tool: 'look', variant: 'screen', label: 'mirando', detail: 'tu pantalla' }, false],
      ['c2', { tool: 'write', variant: 'edit', label: 'guardando', detail: 'en tu espacio' }, false],
      ['c3', { tool: 'write', variant: 'crumble', label: 'borrando', detail: '(con tu permiso)' }, true],
    ];
    for (const [id, anim, err] of tools) {
      host({ kind: 'agent', e: { type: 'tool', id, anim } });
      await sleep(1500);
      host({ kind: 'agent', e: { type: 'tool_end', id, isError: err } });
      await sleep(400);
    }
    host({ kind: 'agent', e: { type: 'text', text: 'Listo: tarea guardada.' } });
    await sleep(1500);
    host({ kind: 'agent', e: { type: 'done', speech: null } });
  };
  S.error = async () => {
    host({ kind: 'agent', e: { type: 'start', agentish: false } });
    await sleep(1200);
    host({ kind: 'agent', e: { type: 'error', message: 'No he podido terminar: el backend no responde.', speech: null } });
  };
  S.escucha = async () => {
    host({ kind: 'voice', type: 'state', state: 'listening', mode: 'handsfree' });
    levels(true, 'in');
    await sleep(2600);
    levels(false);
    host({ kind: 'voice', type: 'final', text: '¿Qué tengo hoy?' });
    host({ kind: 'voice', type: 'state', state: 'idle' });
    await sleep(300);
    await S.turno();
  };
  S.decir = () => host({ kind: 'say', text: 'Recordatorio: llamar a Ana a las seis.', mood: 'determined' });
  S.permiso = () => host({ kind: 'say', text: 'Necesito tu permiso: mira el cuadro de diálogo.', mood: 'concerned' });
  S.pregunta = () => host({ kind: 'ask', id: `bar:${uuid()}`, placeholder: 'Pregúntame lo que quieras…', bar: true });
  S.esc = () => host({ kind: 'esc' });
  S.pequeño = () => host({ kind: 'size', size: 'small' });
  S.cursor = () => host({ kind: 'size', size: 'cursor' });
  S.normal = () => host({ kind: 'size', size: 'default' });
  S.borrar = () => host({ kind: 'agent', e: { type: 'ink_clear', all: true } });

  // Un dibujo de ejemplo: anillo, subrayado, flecha y una tarjeta (criterio de hecho de D1).
  S.dibujo = async () => {
    const voiced = $('#fp-voz').checked, sid = voiced ? ++speechSeq : null;
    const archivo = rectOf('#fk-archivo'), titulo = rectOf('#fk-titulo'), guardar = rectOf('#fk-guardar');
    const say = 'Este es el menú Archivo, aquí el título del documento, y con este botón guardas.';
    const e = {
      type: 'draw', id: `g-${uuid()}`, seg: 0, last: true, edits: [], win: rectOf('#fk-win'), busy: [],
      beats: [{ say, caption: say, voiced, n: 1, marks: [
        { kind: 'ring', part: 'p1', at: { rect: archivo }, label: 'Archivo' },
        { kind: 'underline', part: 'p2', at: { rect: titulo } },
        { kind: 'arrow', part: 'p3', points: [[titulo[0] + titulo[2] + 40, titulo[1] + 90], center(guardar)] },
        { kind: 'card', part: 'p4', title: 'consejo', heading: 'Guarda a menudo', text: 'Pulsa Ctrl+S cada pocos minutos para no perder lo que llevas hecho.', items: ['Ctrl+S guarda', 'Ctrl+Mayús+S guarda como…'] },
      ] }],
    };
    if (sid != null) e.speech_id = sid;
    host({ kind: 'agent', e: { type: 'start', agentish: false } });
    await sleep(300);
    host({ kind: 'agent', e });
    if (sid != null) { await sleep(400); await speak(sid, 5200); }
    await new Promise((res) => { const f = (msg) => { if (msg.type === 'draw_done' && msg.id === e.id) { state.onSidecar = state.onSidecar.filter((x) => x !== f); res(); } }; state.onSidecar.push(f); });
    host({ kind: 'agent', e: { type: 'done', speech: sid } });
  };

  // Una guía de dos pasos: el primero espera un clic en «Guardar» (wait:'click'), el segundo marca un tic.
  S.guia = async () => {
    const id = `g-${uuid()}`, guardar = rectOf('#fk-guardar'), voiced = $('#fp-voz').checked;
    const seg1 = { type: 'draw', id, seg: 0, last: false, edits: [], win: rectOf('#fk-win'), busy: [],
      beats: [{ say: 'Primero, pulsa aquí en Guardar.', caption: 'Primero, pulsa aquí en Guardar.', voiced, n: 1, wait: 'click',
        marks: [{ kind: 'target', part: 'p1', at: { rect: guardar } }] }] };
    const seg2 = { type: 'draw', id, seg: 1, last: true, edits: [], win: null, busy: [],
      beats: [{ say: '¡Perfecto, ya está guardado!', caption: '¡Perfecto, ya está guardado!', voiced, n: 2,
        marks: [{ kind: 'check', part: 'p2', at: { rect: guardar } }] }] };
    const s1 = voiced ? ++speechSeq : null;
    if (s1 != null) seg1.speech_id = s1;
    const wait = new Promise((res) => {
      const f = (msg) => { if (msg.type === 'draw_wait_done' && msg.id === id) { state.onSidecar = state.onSidecar.filter((x) => x !== f); res(msg); } };
      state.onSidecar.push(f);
    });
    host({ kind: 'agent', e: { type: 'start', agentish: false } });
    await sleep(300);
    host({ kind: 'agent', e: seg1 });
    if (s1 != null) speak(s1, 1800);
    const r = await wait;
    F.log('·', `guía: paso 1 → ${r.result}`);
    const s2 = voiced ? ++speechSeq : null;
    if (s2 != null) seg2.speech_id = s2;
    host({ kind: 'agent', e: seg2 });
    if (s2 != null) await speak(s2, 1600); else await sleep(1800);
    host({ kind: 'agent', e: { type: 'done', speech: s2 } });
  };
  // Lo que haría main con Button(1, pressed) sobre el objetivo mientras ink_wait está encendido.
  S.clic = () => { const [x, y] = center(rectOf('#fk-guardar')); F.log('·', `clic simulado (ink_wait ${state.inkWait})`); if (state.inkWait) emit('click', x, y, performance.now()); };

  // ---------- puntero simulado ----------
  let simTimer = null;
  const simPtr = (on) => {
    clearInterval(simTimer); simTimer = null; F.ptr.sim = on;
    if (!on) return;
    const t0 = performance.now();
    simTimer = setInterval(() => {
      const t = (performance.now() - t0) / 1000, W = innerWidth - 340, H = innerHeight;
      F.sendPtr(W * (0.5 + 0.32 * Math.sin(t * 0.7)), H * (0.5 + 0.3 * Math.sin(t * 1.1 + 1)));
    }, 8);
  };
  S.puntero = () => { const on = !simTimer; simPtr(on); $('#fp-ptr').textContent = on ? 'Puntero: simulado' : 'Puntero: ratón'; };
  // Puntero simulado quieto en (x, y) (el ratón real deja de contar hasta pulsar «Puntero»).
  S.ir = (x, y) => { simPtr(false); F.ptr.sim = true; F.sendPtr(x, y); };

  // ---------- DOM: escritorio de mentira, cursor, regiones y panel ----------
  const css = `
  #fk-desk { position: fixed; inset: 0; z-index: 0; background: radial-gradient(120% 90% at 30% 20%, #2b3a55 0%, #141a26 60%, #0b0f16 100%); font: 14px system-ui, sans-serif; color: #dde3ee; }
  #fk-bar { position: absolute; left: 0; right: 0; top: 0; height: 32px; background: #000c; display: flex; align-items: center; justify-content: center; font-size: 13px; }
  #fk-win { position: absolute; left: 90px; top: 110px; width: 620px; height: 420px; background: #f4f5f7; color: #222; border-radius: 12px; box-shadow: 0 20px 60px #0008; overflow: hidden; }
  #fk-win .menu { display: flex; gap: 18px; padding: 10px 16px; background: #e4e6ea; }
  #fk-win .menu span { padding: 3px 8px; border-radius: 6px; }
  #fk-titulo { display: inline-block; margin: 26px 24px 8px; font-size: 24px; font-weight: 700; }
  #fk-win p { margin: 0 24px; line-height: 1.6; color: #444; }
  #fk-guardar { position: absolute; right: 24px; bottom: 22px; padding: 8px 18px; border-radius: 8px; background: #3465a4; color: #fff; border: 0; font: inherit; }
  #fk-cursor { position: fixed; width: 18px; height: 18px; margin: -9px 0 0 -9px; z-index: 2147482000; pointer-events: none; display: none; }
  #fk-cursor::before, #fk-cursor::after { content: ''; position: absolute; background: #ff4fd8; }
  #fk-cursor::before { left: 8px; top: 0; width: 2px; height: 18px; } #fk-cursor::after { top: 8px; left: 0; height: 2px; width: 18px; }
  #fk-rects { position: fixed; inset: 0; z-index: 2147481000; pointer-events: none; }
  #fake-panel { position: fixed; right: 10px; top: 42px; bottom: 10px; width: 310px; z-index: 2147483000; background: #10151ef2; color: #cfe; border: 1px solid #2c3a4a; border-radius: 10px; font: 12px system-ui, sans-serif; display: flex; flex-direction: column; }
  #fake-panel h1 { font-size: 13px; margin: 10px 12px 6px; color: #8ff; }
  #fake-panel .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; padding: 0 10px; }
  #fake-panel button { background: #1d2a3a; color: #dff; border: 1px solid #2f4a63; border-radius: 6px; padding: 5px 4px; font: inherit; cursor: pointer; }
  #fake-panel button:hover { background: #26405a; }
  #fake-panel label { display: block; padding: 6px 12px 0; }
  #fp-log { flex: 1; margin: 8px 10px 10px; padding: 6px; background: #0007; border-radius: 6px; overflow: auto; font: 11px ui-monospace, monospace; white-space: pre-wrap; }`;
  const mount = () => {
    const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    const desk = document.createElement('div'); desk.id = 'fk-desk';
    desk.innerHTML = `<div id="fk-bar">mié 27 nov  18:04</div>
      <div id="fk-win"><div class="menu"><span id="fk-archivo">Archivo</span><span>Editar</span><span>Ver</span><span>Ayuda</span></div>
      <span id="fk-titulo">Práctica de Redes</span>
      <p>Apuntes del tema 3: encaminamiento estático y dinámico, tablas de rutas y métricas.</p>
      <button id="fk-guardar" type="button">Guardar</button></div>`;
    document.body.prepend(desk);
    $('#fk-guardar').addEventListener('click', () => F.log('·', 'la app de debajo recibió el clic en Guardar'));
    const cur = document.createElement('div'); cur.id = 'fk-cursor'; document.body.appendChild(cur);
    const rc = document.createElement('canvas'); rc.id = 'fk-rects'; document.body.appendChild(rc);
    const panel = document.createElement('div'); panel.id = 'fake-panel';
    const B = [['turno', 'Turno completo'], ['escucha', 'Voz: escuchar'], ['herramientas', 'Herramientas'], ['error', 'Error'],
      ['decir', 'say (aviso)'], ['permiso', 'say (permiso)'], ['pregunta', 'Barra de pregunta'], ['esc', 'Esc'],
      ['dibujo', 'Dibujo de ejemplo'], ['guia', 'Guía con clic'], ['clic', 'Clic en Guardar'], ['borrar', 'Borrar dibujo'],
      ['pequeño', 'Tamaño pequeño'], ['cursor', 'Tamaño cursor'], ['normal', 'Tamaño normal'], ['saludo', 'Saludo']];
    panel.innerHTML = `<h1>drakterFloat falso · §11.4</h1><div class="grid">${B.map(([k, t]) => `<button data-run="${k}" type="button">${t}</button>`).join('')}
      <button id="fp-ptr" data-run="puntero" type="button">Puntero: ratón</button></div>
      <label><input id="fp-voz" type="checkbox"> Beats con voz (speech_id + float:voice)</label>
      <label><input id="fp-rects" type="checkbox"> Mostrar regiones (set_hit_rects)</label>
      <div id="fp-log"></div>`;
    document.body.appendChild(panel);
    panel.addEventListener('click', (e) => { const k = e.target.closest('[data-run]')?.dataset.run; if (k) S[k](); });
    window.__fakeCursor = (x, y) => { cur.style.display = F.ptr.sim ? 'block' : 'none'; cur.style.left = `${x}px`; cur.style.top = `${y}px`; };
    const out = $('#fp-log');
    window.__fakeLog = (dir, what, n) => {
      if (n) out.lastChild.textContent = out.lastChild.textContent.replace(/( ×\d+)?\n$/, ` ×${n}\n`);
      else { const l = document.createElement('div'); l.textContent = `${(performance.now() / 1000).toFixed(1).padStart(6)} ${dir} ${what}\n`; out.appendChild(l); }
      out.scrollTop = out.scrollHeight;
    };
    for (const [, d, w] of state.log) window.__fakeLog(d, w);
    const draw = () => {
      rc.width = innerWidth; rc.height = innerHeight;
      const c = rc.getContext('2d');
      c.clearRect(0, 0, rc.width, rc.height);
      if ($('#fp-rects').checked) {
        c.strokeStyle = '#ff4fd8'; c.lineWidth = 1; c.setLineDash([4, 3]);
        const r = state.rects; for (let i = 0; i + 3 < r.length; i += 4) c.strokeRect(r[i] + 0.5, r[i + 1] + 0.5, r[i + 2], r[i + 3]);
      }
      requestAnimationFrame(draw);
    };
    requestAnimationFrame(draw);
  };
  if (document.body) mount(); else document.addEventListener('DOMContentLoaded', mount);

  // P (fuera de un campo) o __fake.panel(false): esconde el panel para ver la página limpia.
  F.panel = (on) => { const el = $('#fake-panel'); if (el) el.style.display = on ? '' : 'none'; };
  addEventListener('keydown', (e) => { if (e.key.toLowerCase() === 'p' && !e.target.closest?.('input, textarea')) { const el = $('#fake-panel'); F.panel(el?.style.display === 'none'); } });
  F.rectsShown = (on) => { $('#fp-rects').checked = !!on; };
  F.run = (k, ...a) => S[k](...a);
  F.scenarios = Object.keys(S);
})();
