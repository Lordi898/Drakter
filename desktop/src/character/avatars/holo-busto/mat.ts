// Materiales de Holo-busto: cristal de luz translúcido. Prepaso de profundidad + luz frontal (sin solapes) y una pasada
// interior de caras traseras sin prueba de profundidad (el volumen se ve por dentro). Fresnel fuerte, curvas de nivel y
// escaneo protagonistas, hebras de pelo, arrugas de edad que se marcan con el gesto. Dos temas con alfa premultiplicado:
// oscuro (luz aditiva) y claro (tinta de cobalto con mezcla normal), para flotar sobre la interfaz.
import * as THREE from 'three';

/** Uniformes compartidos por todos los materiales de UNA instancia del avatar (dos avatares no se pisan). */
export function makeUniforms() {
  return {
  uTime: { value: 0 }, uCol: { value: new THREE.Color(0.35, 0.8, 1) }, uCore: { value: new THREE.Color(0.8, 0.95, 1) },
  uGlow: { value: 1 }, uVoice: { value: 0 }, uCoreI: { value: 0.6 }, uCorePos: { value: new THREE.Vector3(0, -1.45, 0.15) },
  uScanY: { value: 0 }, uScanK: { value: 0.5 }, uCold: { value: 0 }, uFlow: { value: 1 }, uGlitch: { value: 0 }, uShimmer: { value: 0 },
  uRipple: { value: -1 }, uListen: { value: 0 }, uMouthOpen: { value: 0 }, uTheme: { value: 0 },
  uFace: { value: new THREE.Vector4() }, // cejas (alzado medio), sonrisa L, sonrisa R, —
  };
}
export type Uniforms = ReturnType<typeof makeUniforms>;
/** Lo que necesita cada fábrica de materiales: los uniformes y los materiales de luz de la instancia (para el tema). */
export interface Kit { readonly U: Uniforms; readonly lights: Set<THREE.ShaderMaterial> }
export const makeKit = (): Kit => ({ U: makeUniforms(), lights: new Set() });

const COMMON = /* glsl */ `
uniform float uTime, uGlow, uVoice, uCoreI, uScanY, uScanK, uCold, uFlow, uGlitch, uShimmer, uRipple, uListen, uMouthOpen, uTheme;
uniform vec3 uCol, uCore, uCorePos; uniform vec4 uFace;
float h1(float n){ return fract(sin(n * 127.1) * 43758.5453); }
float h3(vec3 p){ p = fract(p * .3183099 + .1); p *= 17.; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float vnoise(vec3 x){ vec3 i = floor(x), f = fract(x); f = f * f * (3. - 2. * f);
  return mix(mix(mix(h3(i), h3(i + vec3(1,0,0)), f.x), mix(h3(i + vec3(0,1,0)), h3(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(h3(i + vec3(0,0,1)), h3(i + vec3(1,0,1)), f.x), mix(h3(i + vec3(0,1,1)), h3(i + vec3(1,1,1)), f.x), f.y), f.z); }
float aline(float v, float w){ float d = abs(fract(v) - .5) * 2.; float fw = fwidth(v) * 2.; return 1. - smoothstep(w, w + fw, 1. - d); }
// Salida con alfa premultiplicado. Oscuro: luz que se suma. Claro: tinta de cobalto (más intensidad = más tinta y más profunda).
vec4 outc(vec3 c){
  c *= uGlow * (1. - uCold * .6);
  c = mix(c, vec3(dot(c, vec3(.3, .5, .2))) * vec3(.55, .68, .9), uCold * .6);
  float a = clamp(max(c.r, max(c.g, c.b)), 0., 1.);
  if (uTheme < .5) return vec4(c, a);
  float k = clamp(a * 1.25, 0., .96);
  vec3 ink = mix(vec3(.3, .55, .92), vec3(.02, .13, .45), smoothstep(.1, .85, a));
  ink = mix(ink, vec3(.6, .32, .05), smoothstep(.15, .6, c.r - c.b)); // los acentos cálidos (error) se mantienen
  return vec4(ink * k, k);
}
`;

const VERT = /* glsl */ `
attribute float aMat; attribute vec3 aAux; attribute vec4 aRig;
uniform float uKind; uniform vec4 uBrow; uniform vec4 uMouth; uniform vec4 uLips; uniform mat3 uBendR; uniform vec3 uPivot; uniform vec3 uHinge;
uniform float uTime, uGlitch, uShimmer;
varying vec3 vW, vN, vO, vAux; varying vec4 vRig;
void main(){
  vec3 p = position, n = normal;
  if (uKind < .5) { // cabeza: rig facial por pesos horneados
    float side = p.x >= 0. ? 1. : -1., ax = abs(p.x);
    float bw = aRig.x, raise = side > 0. ? uBrow.x : uBrow.y, inner = smoothstep(.34, .08, ax);
    p.y += bw * (raise * .07 - uBrow.z * inner * .05);
    p.x -= side * bw * inner * max(uBrow.z, 0.) * .022;
    p.z -= bw * max(raise, 0.) * .01;
    float mw = aRig.z, cr = side > 0. ? uLips.x : uLips.y;
    vec3 C = vec3(side * .235, -.6, .9), d = p - C; float wc = exp(-dot(d, d) / .018);
    p += vec3(side * ((uMouth.y * .03 - uMouth.z * .055) + max(cr, 0.) * .022) * wc, cr * .085 * wc, -max(cr, 0.) * .03 * wc);
    p.z += uMouth.z * .04 * mw * smoothstep(.22, 0., ax);
    vec3 ck = vec3(side * .34, -.28, .8), dk = p - ck; p.y += max(cr, 0.) * .032 * exp(-dot(dk, dk) / .02);
    float lu = side > 0. ? uLips.z : uLips.w; p.y += lu * .024 * mw * smoothstep(-.605, -.585, p.y) * smoothstep(.26, .05, ax);
    float ang = uMouth.x * .15 * aRig.y, c = cos(ang), s = sin(ang);
    vec3 q = p - uHinge; p = uHinge + vec3(q.x, q.y * c - q.z * s, q.y * s + q.z * c);
    n = mix(n, vec3(n.x, n.y * c - n.z * s, n.y * s + n.z * c), aRig.y);
    p.z -= aRig.w * uMouth.x * .28;
  } else if (uKind < 1.5) { // cuello y torso: el cuello se dobla con la cabeza
    float w = aRig.x; p = mix(p, uPivot + uBendR * (p - uPivot), w); n = normalize(mix(n, uBendR * n, w));
  }
  vec4 wp = modelMatrix * vec4(p, 1.);
  wp.x += uGlitch * .06 * sin(wp.y * 37. + uTime * 61.) * step(.82, fract(wp.y * 3.1 + uTime * 7.)); // interferencia (error)
  wp.xyz += normalize(mat3(modelMatrix) * n) * uShimmer * .08 * (sin(wp.y * 23. + uTime * 9.) * .5 + .5); // se recompone
  vO = position; vAux = aAux; vRig = aRig;
  vW = wp.xyz; vN = normalize(mat3(modelMatrix) * n);
  gl_Position = projectionMatrix * viewMatrix * wp;
}`;

const FRAG = /* glsl */ `
uniform float uKind; uniform float uBack;
varying vec3 vW, vN, vO, vAux; varying vec4 vRig;
${COMMON}
void main(){
  vec3 N = normalize(vN), V = normalize(cameraPosition - vW);
  if (uBack > .5) N = -N;
  float ao = vAux.x, hairW = uKind < .5 ? vAux.y : 0., browW = uKind < .5 ? vAux.z : 0.;
  float NoV = clamp(dot(N, V), 0., 1.), fres = pow(1. - NoV, 2.) * smoothstep(.2, .85, ao);
  float key = max(dot(N, normalize(vec3(-.4, .52, .75))), 0.), fill = max(dot(N, normalize(vec3(.65, .05, .76))), 0.);
  // Cristal de luz: modelado contenido, borde fresnel fuerte; el centro de las formas queda translúcido.
  vec3 col = uCol * (.015 + pow(key, 1.7) * .34 + fill * .08) * (.4 + .6 * ao);
  col += uCol * fres * 1.35 + vec3(.78, .94, 1.) * pow(fres, 3.) * .6;
  // Curvas de nivel y escaneo (protagonistas): finas, densas, más vivas en los bordes.
  float cl = aline(vO.y * 16. - uTime * .06 * uFlow, .04) * (.1 + .3 * key + .7 * fres);
  float cl2 = aline(vO.y * 4. - uTime * .03 * uFlow, .02) * .25;
  float lines = cl + cl2;
  if (uKind < .5) {
    // Edad: arrugas de frente (se marcan al alzar las cejas), patas de gallo (al sonreír) y pliegue del párpado.
    float ax = abs(vO.x), side = vO.x >= 0. ? 1. : -1.;
    float fore = smoothstep(.62, .78, vO.z) * smoothstep(.45, .3, ax) * smoothstep(.3, .38, vO.y) * smoothstep(.72, .6, vO.y);
    float wr = aline((vO.y - .02 * cos(vO.x * 4.)) * 15.5, .06) * fore * (.12 + .7 * max(uFace.x, 0.));
    vec2 cf = vec2(ax - .45, vO.y - .045); float cr = length(cf), ca = atan(cf.y, cf.x);
    float crow = aline(ca * 2.2, .1) * smoothstep(.02, .04, cr) * smoothstep(.1, .06, cr) * step(0., cf.x) * (.1 + .8 * max(side > 0. ? uFace.y : uFace.z, 0.));
    float crease = exp(-pow((vO.y - (.112 + .03 * cos((ax - .29) * 9.))) / .007, 2.)) * smoothstep(.15, .2, ax) * smoothstep(.45, .4, ax) * smoothstep(.75, .82, vO.z);
    col += vec3(.7, .92, 1.) * (wr + crow) * .55 + uCol * crease * .45;
    // Cejas: hebras oblicuas; labios: línea del bermellón.
    float bs = vO.x * 30. + vO.y * 70. * sign(vO.x);
    col += vec3(.75, .94, 1.) * browW * (.3 + .7 * aline(bs, .3)) * .55;
    float lip = vRig.z * exp(-pow((abs(vO.y + .6) - .045) / .016, 2.));
    col += uCol * lip * .5;
    // El pelo lo dibujan las hebras; la superficie del pelo queda como un velo con plata en las sienes.
    float silver = smoothstep(.5, .66, ax) * smoothstep(.55, .2, vO.y);
    col = mix(col, col * .45 + mix(uCol, vec3(.88, .96, 1.), silver) * .1, hairW);
    float faceMask = smoothstep(.45, .75, vO.z) * smoothstep(.75, .5, ax) * smoothstep(.62, .3, vO.y);
    lines *= 1. - faceMask * .7;
    // Interior de la boca.
    float inM = min(1., vRig.w * 1.4) * smoothstep(.0, .1, uMouthOpen);
    vec3 mouthIn = uCore * (.03 + uVoice * .25) * vec3(.6, .85, 1.) + vec3(.6, .85, 1.) * .2 * smoothstep(-.6, -.588, vO.y) * (.6 + .4 * aline(vO.x * 24., .5));
    col = mix(col, mouthIn, inM);
    col *= 1. - min(1., vRig.w * 1.6) * .75 * (1. - inM); // boca cerrada: el fondo de la hendidura queda en sombra
  } else {
    // Ropa: solapas en V de la chaqueta y canalé del cuello alto, como líneas de luz.
    float ax = abs(vO.x), jw = vRig.y;
    float lw = .22 + max(0., -1.12 - vO.y) * .42;
    float lapel = exp(-pow((ax - lw) / .012, 2.)) * smoothstep(.15, .4, vO.z) * smoothstep(-1.08, -1.2, vO.y);
    float lapel2 = exp(-pow((ax - lw - .16 - max(0., -1.3 - vO.y) * .1) / .01, 2.)) * smoothstep(.15, .4, vO.z) * smoothstep(-1.2, -1.4, vO.y) * smoothstep(-2.1, -1.8, vO.y) * .6;
    float rib = aline(atan(vO.x, vO.z + .06) * 26., .18) * (1. - jw) * smoothstep(-1.3, -1.15, vO.y) * .35;
    col += vec3(.75, .94, 1.) * (lapel + lapel2) * .8 + uCol * rib;
    lines *= .55 + .45 * jw;
  }
  col += uCol * lines * (1. - browW);
  float cd = length(vW - uCorePos);
  col += uCore * uCoreI * exp(-cd * cd * 1.6) * (.35 + .65 * fres) * (.7 + .6 * uVoice);
  col += uCol * exp(-pow((vW.y - uScanY) / .06, 2.)) * uScanK * (.5 + fres);
  if (uListen > .01) col += uCol * uListen * aline(length(vW - vec3(0., .4, .9)) * 4. - uTime * 1.5, .1) * .35 * (.3 + fres);
  if (uRipple > 0.) col += vec3(.9, .97, 1.) * exp(-pow((length(vW - vec3(0., -1.4, .3)) - uRipple * 4.) / .25, 2.)) * .7;
  float fade = smoothstep(-2.35, -1.7, vW.y);
  col *= mix(aline(vW.y * 26. - uTime * .4, .3) * smoothstep(-2.7, -2.35, vW.y) * .8, 1., fade);
  col += vec3(.8, .95, 1.) * pow(fres, 5.) * .3;
  col *= .9 + .1 * sin(gl_FragCoord.y * 1.5708);
  col *= .96 + .04 * sin(uTime * 23. + vW.y * 3.) * sin(uTime * 7.1);
  if (uBack > .5) { col = uCol * fres * .5 + uCol * cl2 * .4; col *= .12; } // interior: solo el contorno del volumen, tenue
  gl_FragColor = outc(col);
}`;

const PRE_FRAG = /* glsl */ `void main(){ gl_FragColor = vec4(0.); }`;
const BLEND_DARK = { blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor, blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneFactor };
const BLEND_LIGHT = { blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor, blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneMinusSrcAlphaFactor };
function lightMat(k: Kit, p: THREE.ShaderMaterialParameters): THREE.ShaderMaterial { const m = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, ...p, ...BLEND_DARK }); k.lights.add(m); return m; }
/** Cambia todos los materiales de luz entre tema oscuro (suma) y claro (tinta). */
export function setThemeBlending(k: Kit, light: boolean): void {
  k.U.uTheme.value = light ? 1 : 0;
  for (const m of k.lights) { Object.assign(m, light ? BLEND_LIGHT : BLEND_DARK); m.needsUpdate = true; }
}

export interface RigU { uKind: { value: number }; uBrow: { value: THREE.Vector4 }; uMouth: { value: THREE.Vector4 }; uLips: { value: THREE.Vector4 }; uBendR: { value: THREE.Matrix3 }; uPivot: { value: THREE.Vector3 }; uHinge: { value: THREE.Vector3 } }
export function rigUniforms(kind: number): RigU {
  return { uKind: { value: kind }, uBrow: { value: new THREE.Vector4() }, uMouth: { value: new THREE.Vector4() }, uLips: { value: new THREE.Vector4() }, uBendR: { value: new THREE.Matrix3() }, uPivot: { value: new THREE.Vector3() }, uHinge: { value: new THREE.Vector3() } };
}
/** Prepaso de profundidad + luz frontal + interior (caras traseras, sin prueba de profundidad). */
export function holo(k: Kit, rig: RigU): { pre: THREE.ShaderMaterial; light: THREE.ShaderMaterial; back: THREE.ShaderMaterial } {
  const uniforms = { ...k.U, ...rig, uBack: { value: 0 } };
  const pre = new THREE.ShaderMaterial({ uniforms, vertexShader: VERT, fragmentShader: PRE_FRAG, colorWrite: false });
  const light = lightMat(k, { uniforms, vertexShader: VERT, fragmentShader: FRAG, depthFunc: THREE.LessEqualDepth });
  const back = lightMat(k, { uniforms: { ...uniforms, uBack: { value: 1 } }, vertexShader: VERT, fragmentShader: FRAG, side: THREE.BackSide, depthTest: false });
  return { pre, light, back };
}

const LID_VERT = /* glsl */ `
attribute vec2 aUv; varying vec3 vW, vN, vO; varying vec2 vUv;
void main(){ vO = position; vUv = aUv; vec4 wp = modelMatrix * vec4(position, 1.); vW = wp.xyz; vN = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * wp; }`;
const SIMPLE_VERT = /* glsl */ `
varying vec3 vW, vN, vO; varying vec2 vUv;
void main(){ vO = position; vUv = uv; vec4 wp = modelMatrix * vec4(position, 1.); vW = wp.xyz; vN = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * wp; }`;

/** Ojo creíble: iris con fibras radiales, limbo oscuro, pupila que se dilata, esclerótica tenue y un brillo especular. */
export function eyeMat(k: Kit): THREE.ShaderMaterial {
  return lightMat(k, {
    uniforms: { ...k.U, uPupil: { value: 0.4 }, uEye: { value: 1 } }, depthFunc: THREE.LessEqualDepth,
    vertexShader: SIMPLE_VERT,
    fragmentShader: /* glsl */ `
uniform float uPupil, uEye;
varying vec3 vW, vN, vO; varying vec2 vUv;
${COMMON}
void main(){
  vec3 p = normalize(vO), N = normalize(vN), V = normalize(cameraPosition - vW);
  float front = smoothstep(.1, .5, p.z), r = length(p.xy), a = atan(p.y, p.x);
  float pr = mix(.1, .19, uPupil), ir = .36;
  float inIris = (1. - smoothstep(ir - .012, ir + .006, r)) * front;
  float fib = .55 + .45 * vnoise(vec3(a * 9., r * 14., 2.)) * (.7 + .3 * sin(a * 40.));
  vec3 c = vec3(.5, .72, .88) * .07 * front * smoothstep(1., .35, r) * (1. - inIris); // esclerótica tenue
  float iris = inIris * smoothstep(pr, pr + .03, r);
  c += mix(uCol * .55, vec3(.8, .95, 1.), smoothstep(ir, pr, r) * .5) * iris * fib * .85;
  c *= 1. - .6 * exp(-pow((r - ir) / .02, 2.)) * front; // anillo límbico, más oscuro (como un ojo real)
  c += uCol * .35 * exp(-pow((r - pr - .02) / .015, 2.)) * front; // collarete alrededor de la pupila
  vec3 R = reflect(-V, N); c += vec3(1.) * pow(max(dot(R, normalize(vec3(-.4, .5, .75))), 0.), 260.) * 1.8;
  c *= uEye;
  gl_FragColor = outc(c);
}` });
}

/** Párpados: mismo cristal, con la línea de las pestañas encendida. */
export function lidMat(k: Kit, upper: boolean): { pre: THREE.ShaderMaterial; light: THREE.ShaderMaterial } {
  const uniforms = { ...k.U };
  const frag = /* glsl */ `
varying vec3 vW, vN, vO; varying vec2 vUv;
${COMMON}
void main(){
  vec3 N = normalize(vN), V = normalize(cameraPosition - vW);
  float NoV = clamp(dot(N, V), 0., 1.), fres = pow(1. - NoV, 2.4);
  float key = max(dot(N, normalize(vec3(-.42, .5, .76))), 0.);
  vec3 c = (uCol * (.03 + pow(key, 1.4) * .4 + max(N.z, 0.) * .06) + uCol * fres * .35) * .6;
  float rim = ${upper ? '1. - smoothstep(.0, .045, vUv.y)' : 'smoothstep(.94, 1., vUv.y)'};
  c += vec3(.7, .92, 1.) * rim * ${upper ? '.9' : '.3'};
  gl_FragColor = outc(c);
}`;
  const pre = new THREE.ShaderMaterial({ uniforms, vertexShader: LID_VERT, fragmentShader: PRE_FRAG, colorWrite: false });
  const light = lightMat(k, { uniforms, vertexShader: LID_VERT, fragmentShader: frag, depthFunc: THREE.LessEqualDepth });
  return { pre, light };
}

/** Hebras de pelo: líneas de luz sobre el cuero cabelludo, con plata en las sienes y un pulso que las recorre. */
export function hairMat(k: Kit): THREE.ShaderMaterial {
  return lightMat(k, {
    uniforms: { ...k.U }, depthFunc: THREE.LessEqualDepth,
    vertexShader: /* glsl */ `
attribute vec3 aAux; varying float vU, vS, vSilver; varying vec3 vW;
void main(){ vU = aAux.x; vS = aAux.y; vSilver = aAux.z; vec4 wp = modelMatrix * vec4(position, 1.); vW = wp.xyz; gl_Position = projectionMatrix * viewMatrix * wp; }`,
    fragmentShader: /* glsl */ `
varying float vU, vS, vSilver; varying vec3 vW;
${COMMON}
void main(){
  float taper = smoothstep(0., .15, vU) * smoothstep(1., .6, vU);
  float pulse = .55 + .45 * smoothstep(.8, 1., fract(vU * 1.5 - uTime * .25 * uFlow + vS * 5.));
  vec3 c = mix(uCol * .75, vec3(.9, .97, 1.), vSilver * .8 + .1) * taper * pulse * (.5 + .5 * vS);
  gl_FragColor = outc(c * .9);
}` });
}

/** Núcleo: esfera de luz que late con la voz; se ve a través del cristal. */
export function coreMat(k: Kit): THREE.ShaderMaterial {
  return lightMat(k, {
    uniforms: { ...k.U }, depthTest: false, vertexShader: SIMPLE_VERT,
    fragmentShader: /* glsl */ `
varying vec3 vW, vN, vO; varying vec2 vUv;
${COMMON}
void main(){
  vec3 N = normalize(vN), V = normalize(cameraPosition - vW);
  float NoV = clamp(dot(N, V), 0., 1.);
  float k = pow(NoV, 3.) * (.6 + .9 * uVoice) + pow(NoV, 12.) * 1.5;
  gl_FragColor = outc(uCore * k * uCoreI * (1. - uCold * .5));
}` });
}

/** Escenario propio (solo sin transparencia): halo, anillos de proyección tenues y haz del proyector. */
export function backMat(k: Kit): THREE.ShaderMaterial {
  return lightMat(k, {
    uniforms: { ...k.U, uSpin: { value: 0 }, uHalo: { value: 0.5 } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`,
    fragmentShader: /* glsl */ `
uniform float uSpin, uHalo;
varying vec2 vUv;
${COMMON}
float ln(float d, float w){ float a = fwidth(d) * 1.2; return 1. - smoothstep(w, w + a, abs(d)); }
void main(){
  vec2 p = vUv * 2. - 1.; vec2 hp = p - vec2(0., .22); float r = length(hp), a = atan(hp.y, hp.x) / 6.2832;
  float glow = exp(-r * r * 4.) * .1 * uHalo;
  float rings = ln(r - .62, .0015) * (.4 + .6 * step(.5, fract(a * 3. + uSpin * .1))) + ln(r - .66, .001) * step(.75, fract(a * 24. - uSpin * .2)) * .8;
  float beam = smoothstep(.55, 0., abs(p.x) - (1. - vUv.y) * .25) * smoothstep(.55, -1., p.y) * .08;
  float rays = aline(p.x * 22. / (1.2 - vUv.y * .5), .02) * smoothstep(-.2, -1., p.y) * .1;
  gl_FragColor = outc(uCol * (glow + rings * .09 * (.5 + uHalo) + beam + rays));
}` });
}

/** Motas de datos. */
export function motesMat(k: Kit): THREE.ShaderMaterial {
  return lightMat(k, {
    uniforms: { ...k.U, uScale: { value: 300 } },
    vertexShader: /* glsl */ `
attribute float aLife, aSize, aSeed, aTint; uniform float uScale;
varying float vLife, vSeed, vTint;
void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.); gl_Position = projectionMatrix * mv; gl_PointSize = aLife > 0. ? aSize * uScale / -mv.z : 0.; vLife = aLife; vSeed = aSeed; vTint = aTint; }`,
    fragmentShader: /* glsl */ `
varying float vLife, vSeed, vTint;
${COMMON}
void main(){
  vec2 c = gl_PointCoord - .5; float d = length(c), core = smoothstep(.5, 0., d); core *= core;
  float sq = step(.5, fract(vSeed * 7.)) * (1. - smoothstep(.18, .22, max(abs(c.x), abs(c.y))));
  float a = max(core, sq * .8) * smoothstep(0., .2, vLife) * smoothstep(1., .85, vLife);
  gl_FragColor = outc(mix(uCol, uCore, vTint) * (1. + core) * a);
}` });
}

/** Hilos de luz por detrás del busto. */
export function threadsMat(k: Kit): THREE.ShaderMaterial {
  return lightMat(k, {
    uniforms: { ...k.U },
    vertexShader: /* glsl */ `
attribute vec3 aT;
uniform float uTime, uFlow, uVoice;
varying float vA, vU;
void main(){
  float id = aT.x, u = aT.y, sd = aT.z;
  float ang = sd * 6.2832;
  float r = 1.05 + .55 * sd + .25 * sin(id * 1.7);
  float y = -2.4 + u * (2.4 + 1.4 * fract(sd * 7.3));
  float tw = uTime * (.15 + .1 * fract(sd * 3.1)) * uFlow;
  float a = ang + u * (1.2 + sd) + tw;
  vec3 p = vec3(cos(a) * r * (1. - u * .35), y, -.35 - abs(sin(a)) * r * .6);
  p.x += sin(u * 6. + uTime * .7 + id) * .06;
  vA = smoothstep(0., .15, u) * smoothstep(1., .55, u) * (.35 + .65 * fract(sd * 13.1));
  vU = u * 4. - uTime * (.6 + sd) * uFlow;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.);
}`,
    fragmentShader: /* glsl */ `
varying float vA, vU;
${COMMON}
void main(){
  float pulse = .25 + .75 * smoothstep(.75, 1., fract(vU));
  gl_FragColor = outc(uCol * vA * pulse * .55 * (1. + uVoice * .6));
}` });
}
