// Materiales de Ascuario. Todo es ShaderMaterial: iluminación propia (clave + recorte cálido + entorno de estudio
// procedural), sin luces de Three ni postprocesado. El brillo es falso y vive en el propio shader.
import * as THREE from 'three';

export const U = {
  uTime: { value: 0 },
  uKey: { value: new THREE.Vector3(-0.5, 0.62, 0.6).normalize() },
  uRimDir: { value: new THREE.Vector3(0.78, 0.3, -0.55).normalize() },
  uRimCol: { value: new THREE.Color(1, 0.6, 0.3) },
  uFireCol: { value: new THREE.Color(1, 0.4, 0.1) },
  uGlow: { value: 1 }, uFire: { value: 0.5 }, uCold: { value: 0 }, uThroat: { value: 0 }, uMouthGlow: { value: 0 },
  uRipple: { value: -1 }, uRippleO: { value: new THREE.Vector3() }, uGlint: { value: 0 },
};

const COMMON = /* glsl */ `
uniform float uTime, uGlow, uFire, uCold, uThroat, uMouthGlow, uRipple, uGlint;
uniform vec3 uKey, uRimDir, uRimCol, uFireCol, uRippleO;
vec3 h3(vec3 p){ p = fract(p * vec3(.1031, .1030, .0973)); p += dot(p, p.yxz + 33.33); return fract((p.xxy + p.yxx) * p.zyx); }
float vnoise(vec3 p){
  vec3 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  float a = h3(i).x, b = h3(i + vec3(1,0,0)).x, c = h3(i + vec3(0,1,0)).x, d = h3(i + vec3(1,1,0)).x;
  float e = h3(i + vec3(0,0,1)).x, g = h3(i + vec3(1,0,1)).x, k = h3(i + vec3(0,1,1)).x, l = h3(i + vec3(1,1,1)).x;
  return mix(mix(mix(a,b,f.x), mix(c,d,f.x), f.y), mix(mix(e,g,f.x), mix(k,l,f.x), f.y), f.z);
}
// Estudio procedural: ventana cálida arriba a la izquierda, tira de recorte detrás a la derecha, suelo oscuro.
vec3 env(vec3 r, float sharp){
  vec3 c = mix(vec3(.006,.005,.007), vec3(.035,.028,.03), smoothstep(-.5, .9, r.y));
  float k = dot(r, normalize(vec3(-.5, .62, .6)));
  c += vec3(1., .86, .66) * 2.4 * smoothstep(mix(.82, .955, sharp), mix(.97, .99, sharp), k);
  c += vec3(1., .86, .66) * .25 * smoothstep(.4, 1., k);
  float s = dot(r, normalize(vec3(.85, .25, -.45)));
  c += uRimCol * 1.6 * smoothstep(mix(.7, .88, sharp), .97, s);
  c += vec3(.22, .26, .4) * .25 * smoothstep(.3, 1., dot(r, normalize(vec3(-.8, -.4, .3))));
  return c;
}
vec3 grade(vec3 c, vec3 w){
  float f = smoothstep(-3.0, -2.05, w.y); c *= f; // el busto se funde con la penumbra
  float l = dot(c, vec3(.3, .59, .11));
  return mix(c, vec3(l) * vec3(.62, .72, .95) * .75, uCold);
}
`;

const VERT = /* glsl */ `
attribute float aMat; attribute vec3 aAux; attribute vec2 aUv;
uniform float uBendOn; uniform mat3 uBendR; uniform vec3 uPivot;
uniform vec4 uMouthDef; uniform vec3 uMouthX; uniform vec3 uCorner;
flat varying float vMat; varying vec3 vW, vN, vO, vAux; varying vec2 vUv;
void main(){
  vec3 p = position, n = normal;
  if (uMouthX.x > .5) { // boca en coordenadas de la cabeza (uCorner = desplazamiento de la malla: 0 cabeza, bisagra mandíbula)
    vec3 h = p + uCorner; float side = sign(h.x);
    float my = -.26 + .05 * h.z;
    float yb = exp(-pow((h.y - my) / .12, 2.)), lat = smoothstep(.1, .28, abs(h.x));
    float cr = side > 0. ? uMouthDef.z : uMouthDef.w;
    float back = smoothstep(.95, .02, h.z); // la sonrisa curva la mitad trasera de la línea de la boca
    float w = back * yb * lat;
    vec3 cn = vec3(side * .43, -.26, .02); vec3 d = h - cn; float wc = exp(-dot(d, d) / .06);
    p += vec3(side * (uMouthDef.x * .03 - uMouthDef.y * .05) * wc, cr * .15 * w - uMouthDef.x * .012 * wc, (uMouthDef.y * .09 - uMouthDef.x * .07) * wc - max(cr, 0.) * .05 * w);
    float wf = smoothstep(.55, 1.15, h.z) * exp(-pow((h.y - my) / .09, 2.)); // labios redondos (O, U): la punta se estrecha y adelanta
    p.x *= 1. - uMouthDef.y * .22 * wf; p.z += uMouthDef.y * .05 * wf; p.y += uMouthDef.y * .025 * wf * (uMouthX.x < 1.5 ? -1. : 1.);
    if (uMouthX.x < 1.5) {
      float lip = side > 0. ? uMouthX.y : uMouthX.z;
      float edge = exp(-pow((h.y - my - .025) / .07, 2.)) * smoothstep(-.1, .25, h.z) * smoothstep(1.3, .85, h.z) * smoothstep(.04, .18, abs(h.x));
      p.y += lip * .075 * edge;
    }
  }
  if (uBendOn > .5) { float w = aAux.z; p = mix(p, uPivot + uBendR * (p - uPivot), w); n = normalize(mix(n, uBendR * n, w)); }
  vO = position; vMat = aMat; vAux = aAux; vUv = aUv;
  vec4 wp = modelMatrix * vec4(p, 1.); vW = wp.xyz; vN = normalize(mat3(modelMatrix) * n);
  gl_Position = projectionMatrix * viewMatrix * wp;
}`;

const FRAG = /* glsl */ `
uniform mat4 modelMatrix;
uniform float uDensity, uGold, uSoft;
flat varying float vMat; varying vec3 vW, vN, vO, vAux; varying vec2 vUv;
${COMMON}
void voro(vec3 x, out float f1, out float ed, out vec3 id, out vec3 rc){
  vec3 p = floor(x), f = fract(x); float d1 = 9., d2 = 9.;
  for (int k = -1; k <= 1; k++) for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
    vec3 b = vec3(float(i), float(j), float(k)), o = h3(p + b), r = b + o * .8 + .1 - f; float d = dot(r, r);
    if (d < d1) { d2 = d1; d1 = d; id = o; rc = r; } else if (d < d2) d2 = d;
  }
  f1 = sqrt(d1); ed = sqrt(d2) - f1;
}
vec3 dielectric(vec3 N, vec3 V, vec3 alb, float ao, float pw, float sharp, float f0){
  vec3 R = reflect(-V, N); float NoV = clamp(dot(N, V), 0., 1.), F = f0 + (1. - f0) * pow(1. - NoV, 5.);
  float ndl = max(dot(N, uKey), 0.), sp = pow(max(dot(N, normalize(uKey + V)), 0.), pw) * pw * .03;
  float rim = pow(max(dot(N, uRimDir), 0.), 1.5) * pow(1. - NoV, 1.6);
  return alb * (ndl * .9 + .08) * ao + (env(R, sharp) * ao + vec3(1., .93, .82) * sp) * F + uRimCol * rim * .55;
}
vec3 metal(vec3 N, vec3 V, vec3 g, float ao){
  vec3 R = reflect(-V, N); float NoV = clamp(dot(N, V), 0., 1.); vec3 F = g + (1. - g) * pow(1. - NoV, 5.);
  float ndl = max(dot(N, uKey), 0.), sp = pow(max(dot(N, normalize(uKey + V)), 0.), 90.) * 3.;
  float rim = pow(max(dot(N, uRimDir), 0.), 1.5) * pow(1. - NoV, 1.2);
  return F * (env(R, .2) * 1.15 + sp) * ao + g * (ndl * .22 + .03) * ao + uRimCol * g * rim * .5;
}
void main(){
  vec3 N = normalize(vN); if (!gl_FrontFacing) N = -N;
  vec3 V = normalize(cameraPosition - vW);
  float m = vMat, ao = vAux.x, ws = vAux.y;
  vec3 col, em = vec3(0.);
  vec3 gold = vec3(1., .72, .34);
  float band = uRipple > 0. ? exp(-pow((length(vW - uRippleO) - uRipple * 4.2) / .28, 2.)) : 0.;
  if (m < .5 || (m > 6.5 && m < 8.5)) {
    // Escamas de obsidiana: celdas de Voronoi 3D abombadas y facetadas; juntas de oro; brasa en el fondo de la grieta.
    vec3 q = vO * uDensity * mix(vec3(1., 1., .62), vec3(.32, 1.25, .32), uSoft > 1.5 ? ws : 0.); // garganta: escudos anchos
    float f1, ed; vec3 id, rc; voro(q, f1, ed, id, rc);
    float aa = fwidth(ed) + .002;
    vec3 rw = mat3(modelMatrix) * rc; rw -= N * dot(rw, N);
    vec3 Nb = normalize(N - rw * .28 * smoothstep(0., .3, ed) + (id - .5) * .24);
    float vn = vnoise(vO * 1.35 + 7.) + vnoise(vO * 3.1 + 2.) * .25; float vm = 1. - smoothstep(.025, .07, abs(vn - .62)); // vetas de kintsugi: ríos finos
    float crack = (1. - smoothstep(0., .028 + aa, ed)) * vm;
    float edge = ((1. - smoothstep(.02, .055 + aa, ed)) * vm + (1. - smoothstep(.012, .03 + aa, ed)) * .07) * uGold;
    vec3 tint = mix(vec3(.012, .01, .016), vec3(.03, .018, .02), id.x);
    vec3 ob = dielectric(Nb, V, tint, ao * (.35 + .65 * smoothstep(0., .07, ed)), 260., 1., .05);
    float NoV = clamp(dot(Nb, V), 0., 1.);
    ob += (.5 + .5 * cos(6.2832 * (id.y + (1. - NoV) * 1.3 + vec3(0., .33, .67)))) * .012 * pow(1. - NoV, 2.); // irisación
    col = mix(ob, metal(normalize(N + (id - .5) * .15), V, gold, ao), edge);
    float flick = .65 + .35 * vnoise(vO * 3.5 + vec3(0., uTime * 1.4, uTime * .3));
    em += uFireCol * crack * uFire * flick * 1.8;
    em += vec3(1., .8, .45) * band * (edge + crack) * 2.2;
    if (m > 6.5) { // ribete dorado del párpado
      float rimL = m < 7.5 ? 1. - smoothstep(.0, .12, vUv.y) : smoothstep(.88, 1., vUv.y);
      col = mix(col, metal(N, V, gold, 1.), rimL);
    }
    if (uSoft > .5 && uSoft < 1.5) { // carne de la boca, iluminada por dentro
      vec3 fl = vec3(.05, .01, .008) * (.25 + max(dot(N, uKey), 0.)) * ao;
      col = mix(col, fl, ws); float deep = smoothstep(.95, -.15, vO.z); deep *= deep; em += uFireCol * uMouthGlow * ws * (.5 + .5 * flick) * deep * .8;
    } else if (uSoft > 1.5) { // escudos ventrales: la fragua respira por sus juntas con la voz
      em += uFireCol * (1. - smoothstep(0., .05 + aa, ed)) * ws * (.03 + uThroat * 1.9) * flick;
    }
  } else if (m < 1.5) { // cuerno: queratina oscura que aclara a marfil ahumado, con estrías y virola de oro
    float s = vUv.x, rid = .5 + .5 * sin(s * 120.);
    vec3 alb = mix(vec3(.018, .015, .017), vec3(.55, .47, .37), pow(s, 2.2)) * (.92 + .12 * rid);
    col = dielectric(normalize(N + (rid - .5) * .05 * normalize(vO)), V, alb, ao, 90., .6, .045);
    float fer = step(.06, s) * step(s, .12) + step(.145, s) * step(s, .158);
    col = mix(col, metal(N, V, gold, ao), fer * uGold * step(.5, uSoft) * step(uSoft, 1.5));
  } else if (m < 2.5) { // diente
    col = dielectric(N, V, vec3(.5, .44, .34), .5, 60., .4, .05) + uFireCol * uMouthGlow * .25;
  } else if (m < 3.5) {
    col = metal(N, V, gold, ao);
  } else if (m < 6.5) { // membrana: piel fina, translúcida a la brasa interior
    float v = vUv.x, NoV = abs(dot(N, V));
    vec3 alb = vec3(.035, .015, .015);
    col = dielectric(N, V, alb, 1., 40., .3, .04) * .8;
    float vein = smoothstep(.85, 1., sin(vUv.y * 40. + v * 3.) * .5 + .5);
    em += uFireCol * (uFire * .5 + .1) * (1. - v * .6) * (.5 + .5 * (1. - NoV)) * (1. - vein * .5) * .32;
    col = mix(col, metal(N, V, gold, 1.), smoothstep(.93, .99, v) * .8);
  } else { // cadena del monóculo
    float l = fract(vUv.x * 70.), gap = smoothstep(0., .18, l) * smoothstep(1., .82, l);
    col = metal(N, V, gold, 1.) * (.25 + .75 * gap);
  }
  col += em * uGlow * (1. - uCold * .85);
  gl_FragColor = vec4(grade(col, vW), 1.);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;

export function skin(opts: { density?: number; gold?: number; soft?: number; bend?: boolean; mouth?: THREE.Vector3; mouthKind?: number; side?: THREE.Side }): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: {
      ...U, uDensity: { value: opts.density ?? 9 }, uGold: { value: opts.gold ?? 1 }, uSoft: { value: opts.soft ?? 0 },
      uBendOn: { value: opts.bend ? 1 : 0 }, uBendR: { value: new THREE.Matrix3() }, uPivot: { value: new THREE.Vector3() },
      uMouthDef: { value: new THREE.Vector4() }, uMouthX: { value: new THREE.Vector3(opts.mouthKind ?? 0, 0, 0) }, uCorner: { value: opts.mouth ?? new THREE.Vector3() },
    },
    vertexShader: VERT, fragmentShader: FRAG, side: opts.side ?? THREE.FrontSide,
  });
}

const SIMPLE_VERT = /* glsl */ `
varying vec3 vW, vN, vO; varying vec2 vUv;
void main(){ vO = position; vUv = uv; vec4 wp = modelMatrix * vec4(position, 1.); vW = wp.xyz; vN = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * wp; }`;

/** Ojo de brasa: iris completo, pupila de rendija que se dilata, córnea húmeda. */
export function eyeMat(): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: { ...U, uPupil: { value: 0.35 }, uEye: { value: 1 } },
    vertexShader: SIMPLE_VERT,
    fragmentShader: /* glsl */ `
uniform float uPupil, uEye;
varying vec3 vW, vN, vO; varying vec2 vUv;
${COMMON}
void main(){
  vec3 p = normalize(vO), N = normalize(vN), V = normalize(cameraPosition - vW);
  float front = smoothstep(-.2, .35, p.z), r = length(p.xy);
  float pw = mix(.05, .3, uPupil), sl = p.x * p.x / (pw * pw) + p.y * p.y / .5;
  float pupil = (1. - smoothstep(.7, 1., sl)) * front;
  float ang = atan(p.y, p.x);
  float rays = vnoise(vec3(ang * 4., r * 6. - uTime * .4, uTime * .2)) * .6 + vnoise(vec3(ang * 11., r * 3., 3.)) * .4;
  vec3 hot = mix(vec3(1., .82, .42), uFireCol, smoothstep(.0, .55, r));
  vec3 iris = mix(hot * 1.35, uFireCol * .22, smoothstep(.35, .98, r)) * (.78 + .4 * rays);
  iris *= (1. - .8 * smoothstep(.8, .97, r)) * front;
  vec3 c = iris * uEye * (1. - pupil * .97);
  c += uFireCol * 1.4 * smoothstep(.45, .95, sl) * (1. - smoothstep(.95, 1.5, sl)) * front * uEye * .5;
  vec3 R = reflect(-V, N); float NoV = max(dot(N, V), 0.), F = .04 + .96 * pow(1. - NoV, 5.);
  c += env(R, 1.) * (F + .05) + pow(max(dot(R, uKey), 0.), 400.) * 5.;
  c *= (uGlow * .3 + .7) * 1.2;
  gl_FragColor = vec4(grade(c, vW), 1.);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}` });
}

/** Lente del monóculo: reflejo de estudio y destello que barre el cristal. */
export function glassMat(): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: { ...U }, transparent: true, depthWrite: false, side: THREE.DoubleSide,
    vertexShader: SIMPLE_VERT,
    fragmentShader: /* glsl */ `
varying vec3 vW, vN, vO; varying vec2 vUv;
${COMMON}
void main(){
  vec3 N = normalize(vN), V = normalize(cameraPosition - vW); if (dot(N, V) < 0.) N = -N;
  vec3 R = reflect(-V, N); float NoV = max(dot(N, V), 0.), F = .04 + .96 * pow(1. - NoV, 5.);
  vec3 c = env(R, 1.) * (F + .1) * 1.4;
  float s = (vO.x + vO.y) * 3.5, pos = mix(1.6, -1.6, uGlint);
  float streak = smoothstep(.22, 0., abs(s - pos)) * step(.001, uGlint);
  c += vec3(1., .93, .78) * streak * 1.8;
  float a = clamp(.07 + F * .8 + dot(c, vec3(.33)) * .5, 0., .85);
  gl_FragColor = vec4(c + vec3(.04, .03, .02), a);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}` });
}

/** Gema del medallón: el piloto del estado. */
export function gemMat(): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: { ...U },
    vertexShader: SIMPLE_VERT,
    fragmentShader: /* glsl */ `
varying vec3 vW, vN, vO; varying vec2 vUv;
${COMMON}
void main(){
  vec3 N = normalize(cross(dFdx(vW), dFdy(vW))), V = normalize(cameraPosition - vW);
  vec3 R = reflect(-V, N); float NoV = max(dot(N, V), 0.), F = .05 + .95 * pow(1. - NoV, 4.);
  float core = pow(NoV, 2.);
  vec3 c = uRimCol * (.25 + core * 1.3) * (.6 + .5 * uGlow) + env(R, 1.) * F * .8 + uRimCol * uGlint * 1.5;
  gl_FragColor = vec4(grade(c, vW), 1.);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}` });
}

/** Astrolabio grabado al fondo: anillos, graduación y una red excéntrica que gira al pensar. */
export function haloMat(): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: { ...U, uSpin: { value: 0 }, uHalo: { value: 0.5 } }, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`,
    fragmentShader: /* glsl */ `
uniform float uSpin, uHalo, uCold; uniform vec3 uRimCol;
varying vec2 vUv;
float ln(float d, float w){ float a = fwidth(d) * 1.2; return 1. - smoothstep(w, w + a, abs(d)); }
void main(){
  vec2 p = vUv * 2. - 1.; float r = length(p), a = atan(p.y, p.x) / 6.2832;
  float glow = exp(-r * r * 5.) * .1 * uHalo;
  float L = ln(r - .9, .002) + ln(r - .83, .0012) * .7 + ln(r - .58, .001) * .5 + ln(r - .3, .001) * .3;
  float t = fract(a * 96. + uSpin * .5), tick = ln(t - .5, .03) * step(.83, r) * step(r, .9);
  float t2 = fract(a * 12. - uSpin * .25), maj = ln(t2 - .5, .006) * step(.76, r) * step(r, .9);
  vec2 c2 = vec2(cos(uSpin), sin(uSpin)) * .2;
  float rete = ln(length(p - c2) - .46, .0012) * .6 + ln(length(p + c2 * .6) - .62, .001) * .4;
  float ecl = ln(dot(p, vec2(cos(uSpin * .6 + 1.), sin(uSpin * .6 + 1.))), .001) * step(r, .83) * .35;
  float lines = (L + tick * .6 + maj + rete + ecl) * .06 * (.35 + uHalo);
  vec3 c = uRimCol * (glow + lines) * smoothstep(1., .92, r) * (1. - uCold * .7);
  gl_FragColor = vec4(c, 1.);
  #include <colorspace_fragment>
}` });
}

/** Partículas: ascuas (aditivas) y humo (mezcla normal). */
export function pointsMat(kind: 'ember' | 'smoke'): THREE.ShaderMaterial {
  const ember = kind === 'ember';
  return new THREE.ShaderMaterial({
    uniforms: { ...U, uScale: { value: 300 } }, transparent: true, depthWrite: false, blending: ember ? THREE.AdditiveBlending : THREE.NormalBlending,
    vertexShader: /* glsl */ `
attribute float aLife, aSize, aSeed, aTint; uniform float uScale;
varying float vLife, vSeed, vTint;
void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.); gl_Position = projectionMatrix * mv; gl_PointSize = aLife > 0. ? aSize * uScale / -mv.z : 0.; vLife = aLife; vSeed = aSeed; vTint = aTint; }`,
    fragmentShader: ember ? /* glsl */ `
uniform vec3 uFireCol; uniform float uCold;
varying float vLife, vSeed, vTint;
void main(){
  vec2 c = gl_PointCoord - .5; float d = length(c), core = smoothstep(.5, 0., d); core *= core;
  vec3 hot = mix(uFireCol, vec3(1., .9, .6), vLife * .7);
  hot = mix(hot, vec3(1., .82, .4) * 1.3, vTint);
  float fl = .75 + .25 * sin(vSeed * 40. + vLife * 30.);
  gl_FragColor = vec4(hot * (1. + core * 1.5) * (1. - uCold * .6), core * smoothstep(0., .25, vLife) * fl);
}` : /* glsl */ `
uniform vec3 uFireCol, uRimCol; uniform float uCold;
varying float vLife, vSeed, vTint;
void main(){
  vec2 c = gl_PointCoord - .5; float an = vSeed * 6.28 + vLife * 2.;
  c = mat2(cos(an), -sin(an), sin(an), cos(an)) * c;
  float n = sin(c.x * 11. + vSeed * 20.) * sin(c.y * 9. - vSeed * 13.) * .08 + sin((c.x + c.y) * 17. + vSeed * 7.) * .04;
  float a = smoothstep(.5, .05, length(c) + n) * smoothstep(1., .8, vLife) * vLife;
  vec3 smk = mix(vec3(.42, .38, .4), vec3(.035, .03, .03), vTint);
  smk += uFireCol * .35 * smoothstep(.5, 1., vLife) * (1. - vTint) + uRimCol * .12 * (1. - vTint);
  gl_FragColor = vec4(mix(smk, vec3(dot(smk, vec3(.33))), uCold), a * mix(.42, .75, vTint));
}`,
  });
}
