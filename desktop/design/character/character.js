/*
 * Drakter: rig parametrico SVG del personaje (sustituto del .riv de Rive).
 *
 * Script clasico, sin dependencias. Expone en window:
 *   createCharacter(contenedor, { state })  -> { setState, getState, destroy }
 *   DRAKTER_STATES                          -> los 9 nombres del catalogo cerrado
 *
 * Idea central: un estado no dibuja nada. Solo declara valores objetivo para
 * los parametros de PARAMS. Un unico bucle requestAnimationFrame acerca los
 * valores actuales a los objetivos y redibuja, asi que cualquier transicion es
 * suave aunque se cambie de estado a mitad de otra.
 */
(function (global) {
  'use strict';

  var STATE_NAMES = [
    'idle', 'listening', 'thinking', 'speaking', 'executing',
    'success', 'error', 'interrupted', 'offline'
  ];

  /* Cada parametro corresponde a una entrada numerica de la maquina de Rive. */
  var PARAMS = {
    eyeOpen: 0.84,    // apertura de ojos: 0 cerrado, 1 abierto, 1.2 desorbitado
    lidBend: 0,       // curva del ojo cerrado: -1 contento, 1 dormido
    pupil: 0.38,      // anchura de la pupila vertical: 0 rendija, 1 dilatada
    gazeX: 0,         // mirada: -1 izquierda, 1 derecha
    gazeY: 0,         // mirada: -1 arriba, 1 abajo
    browAngleL: 0,    // grados; positivo ceno, negativo preocupacion
    browAngleR: 0,
    browRaiseL: 0,    // unidades del viewBox hacia arriba
    browRaiseR: 0,
    mouthOpen: 0,     // 0 cerrada, 1 abierta del todo
    mouthCurve: 0.15, // -1 hacia abajo, 1 sonrisa
    mouthWidth: 1,    // 1 boca ancha de reposo
    mouthX: 0,        // desplazamiento lateral
    fang: 1,          // tamano del colmillo
    headTilt: 0,      // grados
    headY: 0,         // unidades del viewBox hacia abajo
    headScale: 1,
    finL: 0,          // grados; positivo levantada, negativo caida
    finR: 0,
    ember: 0.35,      // intensidad de la brasa: 0 apagada, 1 viva
    emberHue: 0,      // 0 naranja, 1 cobalto
    crackle: 0,       // chisporroteo de la brasa
    sparks: 0,        // chispas
    smoke: 0,         // humo por el orificio del hocico
    flame: 0,         // llamarada que asoma por detras de la mandibula
    sat: 1,           // saturacion global
    value: 1,         // luminosidad global
    breath: 1,        // amplitud de la respiracion
    breathRate: 0.24, // respiraciones por segundo
    blink: 1,         // frecuencia del parpadeo: 0 no parpadea
    talk: 0,          // mezcla del generador de articulacion
    scan: 0           // vaiven de trabajo: la mirada recorre algo
  };

  /*
   * Solo se anota lo que difiere de PARAMS.
   * rate: velocidad de aproximacion, por segundo.
   * settle: { param: [inicio, fin, ms] } objetivo que decae de inicio a fin
   *         tras entrar en el estado. Es asentamiento interno, no un cambio
   *         de estado: el estado solo cambia con setState.
   */
  var STATES = {
    idle: { rate: 7, set: {} },
    listening: {
      rate: 9,
      set: {
        eyeOpen: 1, pupil: 0.82, gazeX: 0.15,
        browRaiseL: 7, browRaiseR: 5, browAngleL: -4, browAngleR: -4,
        mouthOpen: 0.05, mouthCurve: 0.2,
        headTilt: 8, headY: -2, headScale: 1.03,
        finL: 34, finR: 30, ember: 0.5, breathRate: 0.3, blink: 0.6
      }
    },
    thinking: {
      rate: 6,
      set: {
        eyeOpen: 0.78, pupil: 0.42, gazeX: 0.85, gazeY: -0.85,
        browRaiseL: -2, browRaiseR: 13, browAngleL: 6, browAngleR: -8,
        mouthCurve: -0.12, mouthWidth: 0.62, mouthX: 12,
        headTilt: -5, headY: -2, finL: -6, finR: 12,
        ember: 0.5, smoke: 0.9, blink: 0.5
      }
    },
    speaking: {
      rate: 8,
      set: {
        eyeOpen: 0.9, pupil: 0.48, mouthOpen: 0.07, mouthCurve: 0.2, talk: 1,
        ember: 0.6, finL: 8, finR: 8, breathRate: 0.32
      }
    },
    executing: {
      rate: 9,
      set: {
        eyeOpen: 0.7, pupil: 0.02,
        browAngleL: 18, browAngleR: 18, browRaiseL: -4, browRaiseR: -4,
        mouthCurve: -0.15, mouthWidth: 0.82, headY: 3, finL: -8, finR: -8,
        ember: 0.95, sparks: 1, crackle: 0.2, scan: 1,
        blink: 0.4, breathRate: 0.5
      }
    },
    success: {
      rate: 11,
      set: {
        eyeOpen: 0, lidBend: -1,
        browRaiseL: 8, browRaiseR: 8, browAngleL: -6, browAngleR: -6,
        mouthOpen: 0.2, mouthCurve: 1, mouthWidth: 1.08, fang: 1.3,
        finL: 20, finR: 20, ember: 1, blink: 0
      },
      settle: { flame: [0.9, 0, 900], headY: [-12, -4, 450] }
    },
    error: {
      rate: 8,
      set: {
        eyeOpen: 0.86, pupil: 0.2, gazeX: -0.35, gazeY: 0.55,
        browAngleL: -20, browAngleR: -20, browRaiseL: 4, browRaiseR: 4,
        mouthOpen: 0.1, mouthCurve: -0.85, mouthWidth: 0.8,
        headTilt: -4, headY: 5, finL: -18, finR: -18,
        ember: 0.7, emberHue: 1, crackle: 1, sparks: 0.4, blink: 0.7
      },
      settle: { smoke: [1, 0.3, 1400] }
    },
    interrupted: {
      rate: 26,
      set: {
        eyeOpen: 1.2, pupil: 0.26,
        browRaiseL: 14, browRaiseR: 14, browAngleL: -6, browAngleR: -6,
        mouthOpen: 0.3, mouthCurve: 0, mouthWidth: 0.3, fang: 0.8,
        finL: 14, finR: 14, ember: 0.5, breath: 0, blink: 0
      },
      settle: { headScale: [0.95, 1, 240] }
    },
    offline: {
      rate: 2.6,
      set: {
        eyeOpen: 0, lidBend: 1, pupil: 0.3,
        browAngleL: -3, browAngleR: -3, browRaiseL: -5, browRaiseR: -5,
        mouthCurve: 0, headTilt: -6, headY: 12, headScale: 0.98,
        finL: -30, finR: -30, ember: 0, sat: 0.16, value: 0.62,
        breath: 0.7, breathRate: 0.1, blink: 0
      }
    }
  };

  var PALETTE = {
    line: '#24142A',   // manganeso hondo: contorno
    head: '#3A9A8C',   // cardenillo
    pool: '#1F6E66',   // charco de esmalte
    lid: '#287A70',    // parpados y cejas
    snout: '#8FD0B8',  // hocico
    bone: '#EADFC6',   // cuernos y colmillo
    amber: '#EFA21E',  // iris
    mouth: '#2B1426',
    tongue: '#A8443F',
    gloss: '#E9FBF0',  // brillo del vidriado
    spark: '#FFF2C8',
    smoke: '#D9D2DC',
    coal: '#3B3338',   // brasa apagada
    ember: '#FF6B22',  // brasa
    emberHot: '#FFD166',
    cobalt: '#4C74FF', // brasa en error
    cobaltHot: '#CAD8FF'
  };

  /* Geometria fija, en el viewBox -16 -8 352 352. */
  var HEAD = 'M160 72C208 72 250 94 254 146C256 172 240 184 237 202' +
    'C235 222 238 236 224 250C206 266 184 264 160 264C136 264 114 266 96 250' +
    'C82 236 85 222 83 202C80 184 64 172 66 146C70 94 112 72 160 72Z';
  var SNOUT = 'M160 156C168 146 182 138 196 146C208 154 214 170 220 186' +
    'C230 212 224 236 206 246C190 254 176 254 160 254C144 254 130 254 114 246' +
    'C96 236 90 212 100 186C106 170 112 154 124 146C138 138 152 146 160 156Z';
  var HORN = 'M190 90C202 72 222 58 246 50C246 72 240 92 228 110Z';
  var SOCKET = 'M-38 6C-34 -26 -14 -36 6 -36C26 -36 40 -18 42 -6' +
    'C38 14 20 28 0 28C-18 28 -32 20 -38 6Z';
  var FIN = 'M-8 -30Q26 -56 64 -54Q46 -44 46 -30Q52 -20 70 -16Q50 -12 46 -4' +
    'Q46 8 56 18Q24 22 -8 30Z';
  var BROW = 'M-32 7Q-29 -4 -17 -6Q-10 -12 0 -9Q9 -13 19 -8Q29 -8 36 1' +
    'Q12 5 -32 7Z';
  var FLAME = 'M160 306C120 312 84 298 66 270C52 266 40 256 30 238' +
    'C44 240 50 238 56 234C44 216 36 194 44 164C58 184 74 196 90 210L160 230' +
    'L230 210C246 196 262 184 276 164C284 194 276 216 264 234' +
    'C270 238 276 240 290 238C280 256 268 266 254 270' +
    'C236 298 200 312 160 306Z';
  var GEM = 'M0 -18C8 -9 14 -3 14 5C14 13 8 17 0 17C-8 17 -14 13 -14 5C-14 -3 -8 -9 0 -18Z';
  var CURL = 'M-12 8C-18 -6 -2 -14 6 -6C12 0 4 8 -2 3';
  var SPARK = 'M0 -7L4 0L0 7L-4 0Z';

  var FIN_PIVOT_X = 76;
  var EYE_L = { x: 118, y: 130 };
  var EYE_R = { x: 202, y: 130 };
  var BROW_Y = 103;
  var MOUTH_Y = 206;
  var EMBER_X = 160;
  var EMBER_Y = 276;
  var NOSTRIL_X = 140;
  var NOSTRIL_Y = 166;
  var SMOKE_COUNT = 4;
  var SPARK_COUNT = 10;

  /* Formas de boca del generador: apertura, anchura, curva. */
  var VISEMES = [
    [0.85, 0.95, 0], [0.4, 1.1, 0.25], [0.22, 1.15, 0.3],
    [0.62, 0.62, -0.1], [0.28, 0.5, 0], [0.02, 0.85, 0.1], [0.5, 0.8, -0.2]
  ];

  var instances = 0;

  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function frac(v) { return v - Math.floor(v); }
  function n(v) { return Math.round(v * 100) / 100; }
  function rand(lo, hi) { return lo + Math.random() * (hi - lo); }

  function rgb(hex) {
    var v = parseInt(hex.slice(1), 16);
    return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
  }

  function mixRgb(a, b, t) {
    return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
  }

  function tone(c, sat, value) {
    var gray = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2];
    return 'rgb(' +
      Math.round((gray + (c[0] - gray) * sat) * value) + ',' +
      Math.round((gray + (c[1] - gray) * sat) * value) + ',' +
      Math.round((gray + (c[2] - gray) * sat) * value) + ')';
  }

  var COLORS = {};
  Object.keys(PALETTE).forEach(function (k) { COLORS[k] = rgb(PALETTE[k]); });

  function fin(key) {
    return '<g data-k="' + key + '">' +
      '<path d="' + FIN + '" data-f="head" data-s="line" stroke-width="5"/>' +
      '<path d="M2 -6L52 -40M2 0L54 -15M2 6L44 12" fill="none" data-s="pool" ' +
      'stroke-width="4" stroke-linecap="round"/></g>';
  }

  function horn(mirror) {
    return '<g' + (mirror ? ' transform="matrix(-1 0 0 1 320 0)"' : '') + '>' +
      '<path d="' + HORN + '" data-f="bone" data-s="line" stroke-width="5"/>' +
      '<path d="M204 80Q218 84 232 94M220 66Q230 70 239 78" fill="none" ' +
      'data-s="line" stroke-width="3" stroke-linecap="round" opacity=".35"/></g>';
  }

  function eye(side, id) {
    var e = side === 'L' ? EYE_L : EYE_R;
    return '<path d="' + SOCKET + '" data-f="lid" transform="translate(' + e.x + ' ' + e.y + ')' +
      (side === 'L' ? 'scale(-1 1)' : '') + '"/>' +
      '<path data-k="eye' + side + '" data-f="amber"/>' +
      '<g clip-path="url(#' + id + '-eye' + side + ')">' +
      '<ellipse data-k="pupil' + side + '" data-f="line"/>' +
      '<circle data-k="glint' + side + '" r="3.6" data-f="gloss"/></g>' +
      '<path data-k="rim' + side + '" fill="none" data-s="line" ' +
      'stroke-width="6" stroke-linejoin="round" stroke-linecap="round"/>';
  }

  function repeat(count, make) {
    var out = '';
    for (var i = 0; i < count; i++) out += make(i);
    return out;
  }

  function markup(id) {
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-16 -8 352 352" ' +
      'width="100%" height="100%" aria-hidden="true" focusable="false" ' +
      'stroke-linejoin="round">' +
      '<defs>' +
      '<clipPath id="' + id + '-head"><path d="' + HEAD + '"/></clipPath>' +
      '<clipPath id="' + id + '-eyeL"><path data-k="clipL"/></clipPath>' +
      '<clipPath id="' + id + '-eyeR"><path data-k="clipR"/></clipPath>' +
      '<clipPath id="' + id + '-mouth"><path data-k="clipMouth"/></clipPath>' +
      '<radialGradient id="' + id + '-halo"><stop data-k="haloIn" offset=".35"/>' +
      '<stop data-k="haloOut" offset="1" stop-opacity="0"/></radialGradient>' +
      '</defs>' +
      '<g data-k="root">' +
      '<g data-k="flame">' +
      '<path d="' + FLAME + '" data-k="flameOuter" data-s="line" stroke-width="5"/>' +
      '<path d="' + FLAME + '" data-k="flameInner" ' +
      'transform="matrix(.72 0 0 .72 44.8 73.4)"/></g>' +
      /* El halo va detrás de la cabeza para no manchar el hocico. */
      '<circle data-k="halo" cx="' + EMBER_X + '" cy="' + EMBER_Y + '" ' +
      'fill="url(#' + id + '-halo)"/>' +
      fin('finL') + fin('finR') + horn(false) + horn(true) +
      /* El charco de esmalte es la misma cabeza, desplazada y recortada. */
      '<path d="' + HEAD + '" data-f="pool"/>' +
      '<g clip-path="url(#' + id + '-head)">' +
      '<path d="' + HEAD + '" data-f="head" ' +
      'transform="matrix(.97 0 0 .97 4.8 -3)"/></g>' +
      '<path d="' + HEAD + '" fill="none" data-s="line" stroke-width="5"/>' +
      '<path d="M146 92q7 8 14 0q7 8 14 0M153 80q7 7 14 0" ' +
      'fill="none" data-s="pool" stroke-width="4" stroke-linecap="round"/>' +
      '<g data-k="gloss">' +
      '<path d="M92 98C104 86 120 80 138 78C122 86 110 92 100 102' +
      'C96 106 88 103 92 98Z" data-f="gloss" opacity=".7"/></g>' +
      '<path d="' + SNOUT + '" data-f="snout" data-s="pool" stroke-width="4"/>' +
      '<g data-k="glossSnout">' +
      '<path d="M110 186C112 172 118 162 128 156C122 168 120 178 120 190' +
      'C119 196 110 194 110 186Z" data-f="gloss" opacity=".8"/></g>' +
      '<ellipse cx="140" cy="168" rx="7.5" ry="4.8" transform="rotate(24 140 168)" data-f="line"/>' +
      '<ellipse cx="180" cy="168" rx="7.5" ry="4.8" transform="rotate(-24 180 168)" data-f="line"/>' +
      eye('L', id) + eye('R', id) +
      '<path data-k="browL" d="' + BROW + '" data-f="lid" data-s="line" stroke-width="4"/>' +
      '<path data-k="browR" d="' + BROW + '" data-f="lid" data-s="line" stroke-width="4"/>' +
      '<path data-k="mouth" data-f="mouth"/>' +
      '<g clip-path="url(#' + id + '-mouth)">' +
      '<ellipse data-k="tongue" data-f="tongue"/></g>' +
      '<path data-k="mouthRim" fill="none" data-s="line" stroke-width="5" stroke-linecap="round"/>' +
      '<path data-k="fang" data-f="bone" data-s="line" stroke-width="4"/>' +
      '<circle cx="' + EMBER_X + '" cy="' + EMBER_Y + '" r="21" data-f="mouth" ' +
      'data-s="line" stroke-width="5"/>' +
      '<path data-k="gem" d="' + GEM + '"/>' +
      '<path data-k="gemCore" d="' + GEM + '"/>' +
      repeat(SMOKE_COUNT, function (i) {
        return '<g data-k="smoke' + i + '"><path d="' + CURL + '" fill="none" ' +
          'data-s="smoke" stroke-width="7" stroke-linecap="round"/></g>';
      }) +
      repeat(SPARK_COUNT, function (i) {
        return '<path data-k="spark' + i + '" d="' + SPARK + '"/>';
      }) +
      '</g></svg>';
  }

  /* ---------- Ticker compartido por todas las instancias ---------- */

  var rigs = [];
  var frame = 0;

  function tick(now) {
    frame = rigs.length ? global.requestAnimationFrame(tick) : 0;
    for (var i = 0; i < rigs.length; i++) rigs[i].step(now);
  }

  function startTicker() {
    if (!frame) frame = global.requestAnimationFrame(tick);
  }

  var motionQuery = global.matchMedia
    ? global.matchMedia('(prefers-reduced-motion: reduce)')
    : null;

  function reducedMotion() { return !!(motionQuery && motionQuery.matches); }

  /* ---------- Fabrica ---------- */

  function createCharacter(container, options) {
    if (!container || container.nodeType !== 1) {
      throw new TypeError('createCharacter necesita un elemento contenedor');
    }

    var id = 'drakter-' + (++instances);
    var state = 'idle';
    var requested = options && options.state;
    if (requested !== undefined) {
      if (STATE_NAMES.indexOf(requested) !== -1) {
        state = requested;
      } else {
        console.warn('Estado desconocido de Drakter: ' + requested);
      }
    }

    container.innerHTML = markup(id);
    var svg = container.querySelector('svg');
    var parts = {};
    Array.prototype.forEach.call(svg.querySelectorAll('[data-k]'), function (el) {
      parts[el.getAttribute('data-k')] = el;
    });
    var fills = Array.prototype.slice.call(svg.querySelectorAll('[data-f]'));
    var strokes = Array.prototype.slice.call(svg.querySelectorAll('[data-s]'));

    var cur = {};
    Object.keys(PARAMS).forEach(function (k) { cur[k] = 0; });

    var last = 0;
    var time = rand(0, 30);     // desfasa respiracion y humo entre instancias
    var enteredAt = 0;
    var phase = rand(0, 6.28);
    var blinkAt = rand(1, 5);
    var blinkFrom = -1;
    var crackleValue = 1;
    var crackleLeft = 0;
    var toneKey = '';
    var alive = true;
    var talk = {
      o: 0, w: 1, c: 0,       // valores suavizados
      to: 0, tw: 1, tc: 0,    // destino actual
      left: 0, phrase: rand(1, 2.4), rest: 0, last: -1
    };

    function put(el, attr, value) {
      var seen = el.__rig || (el.__rig = {});
      if (seen[attr] !== value) {
        seen[attr] = value;
        el.setAttribute(attr, value);
      }
    }

    function target(key) {
      var def = STATES[state];
      var reduced = reducedMotion();
      var s = def.settle && def.settle[key];
      if (s) {
        if (reduced) return s[1];
        var elapsed = (time - enteredAt) * 1000;
        return s[1] + (s[0] - s[1]) * Math.exp(-elapsed / s[2]);
      }
      return key in def.set ? def.set[key] : PARAMS[key];
    }

    function stepTalk(dt) {
      talk.left -= dt;
      talk.phrase -= dt;
      if (talk.left <= 0) {
        if (talk.phrase <= 0) {
          /* Fin de frase: silencio con la boca casi cerrada. */
          talk.phrase = rand(1.1, 3);
          talk.to = 0.02;
          talk.tw = 0.88;
          talk.tc = 0.1;
          talk.left = rand(0.26, 0.6);
        } else if (Math.random() < 0.14) {
          /* Pausa breve entre palabras. */
          talk.to = 0.03;
          talk.tw = 0.9;
          talk.tc = 0;
          talk.left = rand(0.08, 0.18);
        } else {
          var i;
          do { i = Math.floor(Math.random() * VISEMES.length); } while (i === talk.last);
          talk.last = i;
          talk.to = VISEMES[i][0] * rand(0.75, 1.1);
          talk.tw = VISEMES[i][1];
          talk.tc = VISEMES[i][2];
          talk.left = rand(0.07, 0.2);
        }
      }
      var k = 1 - Math.exp(-dt * 24);
      talk.o += (talk.to - talk.o) * k;
      talk.w += (talk.tw - talk.w) * k;
      talk.c += (talk.tc - talk.c) * k;
    }

    function stepBlink(dt) {
      if (cur.blink < 0.05) {
        blinkFrom = -1;
        return 1;
      }
      if (blinkFrom < 0 && time >= blinkAt) blinkFrom = time;
      if (blinkFrom < 0) return 1;
      var u = (time - blinkFrom) / 0.17;
      if (u >= 1) {
        blinkFrom = -1;
        var gap = Math.random() < 0.18 ? 0.24 : rand(2.4, 7);
        blinkAt = time + gap / cur.blink;
        return 1;
      }
      return 1 - Math.sin(u * Math.PI);
    }

    function stepCrackle(dt) {
      crackleLeft -= dt;
      if (crackleLeft <= 0) {
        crackleLeft = rand(0.04, 0.13);
        crackleValue = Math.random() < 0.3 ? rand(0.1, 0.45) : rand(0.7, 1.1);
      }
      return lerp(1, crackleValue, cur.crackle);
    }

    function drawEye(side, e, open, bend, gazeX, gazeY) {
      var outer = side === 'L' ? -1 : 1;
      var ox = e.x + outer * 28;
      var ix = e.x - outer * 28;
      var oy = e.y - 2;
      var iy = e.y + 3;
      var my = e.y + bend * 20;
      var d = 'M' + ix + ' ' + iy +
        'Q' + e.x + ' ' + n(my - open * 46) + ' ' + ox + ' ' + oy +
        'Q' + e.x + ' ' + n(my + open * 30) + ' ' + ix + ' ' + iy + 'Z';
      put(parts['eye' + side], 'd', d);
      put(parts['clip' + side], 'd', d);
      put(parts['rim' + side], 'd', d);
      var px = e.x + gazeX * 12;
      var py = e.y - 2 + gazeY * 9;
      var pupil = parts['pupil' + side];
      var rx = lerp(3, 14.5, cur.pupil);
      put(pupil, 'cx', n(px));
      put(pupil, 'cy', n(py));
      put(pupil, 'rx', n(rx));
      put(pupil, 'ry', 21);
      var glint = parts['glint' + side];
      put(glint, 'cx', n(px - rx * 0.35 - 1));
      put(glint, 'cy', n(py - 9));
    }

    function drawBrow(el, x, angle, raise, mirror) {
      put(el, 'transform',
        'translate(' + x + ' ' + n(BROW_Y - raise) + ')' +
        (mirror ? 'scale(-1 1)' : '') +
        'rotate(' + n(-angle) + ')');
    }

    function drawMouth(open, curve, width) {
      var hw = 68 * width;
      var cx = 160 + cur.mouthX;
      var xl = cx - hw;
      var xr = cx + hw;
      var yc = MOUTH_Y - curve * 13;
      var yu = MOUTH_Y + curve * 13;
      var yl = yu + open * 86;
      var d = 'M' + n(xl) + ' ' + n(yc) +
        'Q' + n(cx) + ' ' + n(yu) + ' ' + n(xr) + ' ' + n(yc) +
        'Q' + n(cx) + ' ' + n(yl) + ' ' + n(xl) + ' ' + n(yc) + 'Z';
      put(parts.mouth, 'd', d);
      put(parts.clipMouth, 'd', d);
      put(parts.mouthRim, 'd', d);

      var tongue = parts.tongue;
      var lowY = (yc + yl) / 2;
      put(tongue, 'cx', n(cx));
      put(tongue, 'cy', n(lowY + 5));
      put(tongue, 'rx', n(hw * 0.56));
      put(tongue, 'ry', n(6 + open * 20));

      /* El colmillo se apoya siempre sobre la curva del labio superior. */
      var t = 0.74;
      var fx = lerp(xl, xr, t);
      var fy = (1 - t) * (1 - t) * yc + 2 * t * (1 - t) * yu + t * t * yc;
      var size = cur.fang * clamp(0.55 + width * 0.45, 0.6, 1.1);
      var w = 12 * size;
      var h = 31 * size;
      put(parts.fang, 'd',
        'M' + n(fx - w) + ' ' + n(fy - 1) +
        'Q' + n(fx - w * 0.6) + ' ' + n(fy + h * 0.62) + ' ' + n(fx + 2) + ' ' + n(fy + h) +
        'Q' + n(fx + w * 0.7) + ' ' + n(fy + h * 0.5) + ' ' + n(fx + w) + ' ' + n(fy - 1) + 'Z');
    }

    function drawEmber(level, sat, value) {
      var hue = cur.emberHue;
      var color = mixRgb(COLORS.ember, COLORS.cobalt, hue);
      var hot = mixRgb(COLORS.emberHot, COLORS.cobaltHot, hue);
      var lit = clamp(level * 1.7, 0, 1);
      var core = clamp((level - 0.2) / 0.5, 0, 1);
      var gemColor = mixRgb(COLORS.coal, color, lit);
      var size = 0.8 + level * 0.25;
      put(parts.gem, 'fill', tone(gemColor, sat, value));
      put(parts.gem, 'transform',
        'translate(' + EMBER_X + ' ' + EMBER_Y + ')scale(' + n(size) + ')');
      put(parts.gemCore, 'fill', tone(mixRgb(gemColor, hot, core), sat, value));
      put(parts.gemCore, 'transform',
        'translate(' + EMBER_X + ' ' + EMBER_Y + ')scale(' + n(size * 0.48) + ')');
      put(parts.haloIn, 'stop-color', tone(color, sat, value));
      put(parts.haloOut, 'stop-color', tone(color, sat, value));
      put(parts.halo, 'r', n(24 + level * 40));
      put(parts.halo, 'opacity', n(clamp(level * 0.9, 0, 0.75)));
      return { color: color, hot: hot };
    }

    function drawFlame(colors, sat, value, wobble) {
      var f = cur.flame;
      var group = parts.flame;
      if (f < 0.02) {
        put(group, 'visibility', 'hidden');
        return;
      }
      put(group, 'visibility', 'visible');
      var scale = 0.62 + 0.5 * f;
      put(group, 'transform',
        'translate(160 262)rotate(' + n(wobble * 1.6) + ')' +
        'scale(' + n(scale * (1 + wobble * 0.02)) + ' ' + n(scale) + ')' +
        'translate(-160 -262)');
      put(parts.flameOuter, 'fill', tone(colors.color, sat, value));
      put(parts.flameInner, 'fill', tone(colors.hot, sat, value));
    }

    function drawSmoke(t) {
      for (var i = 0; i < SMOKE_COUNT; i++) {
        var p = frac(t * 0.21 + i / SMOKE_COUNT);
        var alpha = Math.sin(p * Math.PI) * clamp(cur.smoke * 1.3, 0, 1);
        var el = parts['smoke' + i];
        if (alpha < 0.01) {
          put(el, 'visibility', 'hidden');
          continue;
        }
        /* Sube fino por el puente entre los ojos y se riza sobre las cejas. */
        var free = clamp((p - 0.42) / 0.58, 0, 1);
        var x = NOSTRIL_X + 20 * clamp(p / 0.1, 0, 1) +
          Math.sin(p * 7 + i * 2.1) * 14 * free;
        var y = NOSTRIL_Y + 2 - 158 * p;
        put(el, 'visibility', 'visible');
        put(el, 'opacity', n(alpha));
        put(el, 'transform',
          'translate(' + n(x) + ' ' + n(y) + ')' +
          'rotate(' + n(p * 70 - 20 + i * 40) + ')' +
          'scale(' + n(0.3 + free * 1.3) + ')');
      }
    }

    function drawSparks(t, colors, sat, value) {
      for (var i = 0; i < SPARK_COUNT; i++) {
        var el = parts['spark' + i];
        var speed = 0.9 + (i % 3) * 0.28;
        var p = frac(t * speed + i * 0.317);
        var gate = i / SPARK_COUNT < cur.sparks;
        var alpha = gate ? (1 - p * p) * clamp(cur.sparks * 2.5, 0, 1) : 0;
        if (alpha < 0.01) {
          put(el, 'visibility', 'hidden');
          continue;
        }
        var side = i % 2 ? 1 : -1;
        var angle = 0.32 + (i % 5) * 0.2;
        var reach = 96 + (i % 4) * 16;
        var x = EMBER_X + side * Math.cos(angle) * reach * p;
        var y = EMBER_Y - Math.sin(angle) * reach * p + 74 * p * p;
        put(el, 'visibility', 'visible');
        put(el, 'opacity', n(alpha));
        put(el, 'fill', tone(mixRgb(COLORS.spark, colors.color, p), sat, value));
        put(el, 'transform',
          'translate(' + n(x) + ' ' + n(y) + ')rotate(' + n(p * 200 + i * 37) + ')');
      }
    }

    function retone(sat, value) {
      var key = n(sat) + '/' + n(value);
      if (key === toneKey) return;
      toneKey = key;
      fills.forEach(function (el) {
        put(el, 'fill', tone(COLORS[el.getAttribute('data-f')], sat, value));
      });
      strokes.forEach(function (el) {
        put(el, 'stroke', tone(COLORS[el.getAttribute('data-s')], sat, value));
      });
    }

    function draw(dt) {
      var reduced = reducedMotion();
      var live = !reduced;
      var t = live ? time : 1.7;     // particulas congeladas con movimiento reducido

      var breath = 0;
      if (live) {
        phase += dt * cur.breathRate * Math.PI * 2;
        breath = Math.sin(phase) * cur.breath;
      }

      var blink = live ? stepBlink(dt) : 1;
      var flicker = live ? stepCrackle(dt) : 1;
      if (live && cur.talk > 0.01) stepTalk(dt);

      var talkO = live ? talk.o : 0.45;
      var talkW = live ? talk.w : 0.95;
      var talkC = live ? talk.c : 0;
      var scan = live ? cur.scan : 0;
      var nod = scan * Math.sin(time * 9.5) * 1.3;
      var speak = cur.talk * (live ? 1 : 0);

      var tilt = cur.headTilt + speak * Math.sin(time * 1.3) * 1.6;
      var y = cur.headY + breath * 1.6 + nod;
      var scaleY = cur.headScale * (1 + breath * 0.012);
      put(parts.root, 'transform',
        'translate(160 ' + n(262 + y) + ')rotate(' + n(tilt) + ')' +
        'scale(' + n(cur.headScale) + ' ' + n(scaleY) + ')translate(-160 -262)');

      /* El brillo no gira con la pieza: se queda con la luz de la sala. */
      var glossShift = 'translate(' + n(-tilt * 0.9) + ' ' + n(tilt * 0.3) + ')';
      put(parts.gloss, 'transform', glossShift);
      put(parts.glossSnout, 'transform', glossShift);

      var lift = speak * talkO * 7;
      put(parts.finR, 'transform',
        'translate(' + (320 - FIN_PIVOT_X) + ' 130)rotate(' + n(-(cur.finR + lift)) + ')');
      put(parts.finL, 'transform',
        'translate(' + FIN_PIVOT_X + ' 130)scale(-1 1)rotate(' + n(-(cur.finL + lift)) + ')');

      var gazeX = cur.gazeX;
      if (scan) gazeX += scan * (Math.sin(time * 2.7) + 0.4 * Math.sin(time * 6.1)) * 0.6;
      var open = cur.eyeOpen * blink;
      drawEye('L', EYE_L, open, cur.lidBend, gazeX, cur.gazeY);
      drawEye('R', EYE_R, open, cur.lidBend, gazeX, cur.gazeY);

      var browLift = cur.talk * talkO * 4;
      drawBrow(parts.browL, EYE_L.x - 2, cur.browAngleL, cur.browRaiseL + browLift, true);
      drawBrow(parts.browR, EYE_R.x + 2, cur.browAngleR, cur.browRaiseR + browLift, false);

      drawMouth(
        Math.max(0, cur.mouthOpen + cur.talk * talkO),
        cur.mouthCurve + cur.talk * talkC,
        cur.mouthWidth * (1 + cur.talk * (talkW - 1))
      );

      var sat = clamp(cur.sat, 0, 1);
      var value = clamp(cur.value, 0, 1);
      retone(sat, value);

      var level = clamp((cur.ember + breath * 0.03 + speak * talkO * 0.25) * flicker, 0, 1);
      var colors = drawEmber(level, sat, value);
      drawFlame(colors, sat, value, live ? Math.sin(time * 11) + Math.sin(time * 17.3) * 0.6 : 0);
      drawSmoke(t);
      drawSparks(t, colors, sat, value);
    }

    function advance(dt) {
      time += dt;
      var k = 1 - Math.exp(-dt * STATES[state].rate);
      for (var key in PARAMS) cur[key] += (target(key) - cur[key]) * k;
      draw(dt);
    }

    var rig = {
      step: function (now) {
        var dt = last ? Math.min((now - last) / 1000, 0.05) : 0;
        last = now;
        advance(dt);
      }
    };

    function setState(name) {
      if (!alive) return false;
      if (typeof name !== 'string' || STATE_NAMES.indexOf(name) === -1) {
        console.warn('Estado desconocido de Drakter: ' + String(name));
        return false;
      }
      if (name !== state) {
        state = name;
        enteredAt = time;
      }
      return true;
    }

    function destroy() {
      if (!alive) return;
      alive = false;
      rigs.splice(rigs.indexOf(rig), 1);
      if (!rigs.length && frame) {
        global.cancelAnimationFrame(frame);
        frame = 0;
      }
      if (svg.parentNode === container) container.removeChild(svg);
    }

    /* Primer fotograma ya en pose: nunca se ve la pieza a medio montar. */
    enteredAt = time;
    Object.keys(PARAMS).forEach(function (k) { cur[k] = target(k); });
    draw(0);

    rigs.push(rig);
    startTicker();

    return {
      setState: setState,
      getState: function () { return state; },
      destroy: destroy
    };
  }

  global.createCharacter = createCharacter;
  global.DRAKTER_STATES = STATE_NAMES.slice();
})(window);
