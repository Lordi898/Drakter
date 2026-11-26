// GLSL del Visor (prototipo drakter-99, jarvis-hud/visor/src/scene.ts). Brillo solo en shader: sin postprocesado.

export const PLATE_VS = /* glsl */ `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`

export const PLATE_FS = /* glsl */ `
precision highp float;
uniform vec2 uSize; uniform float uTime, uHover, uFlash, uReveal, uSeed, uAlpha, uFov, uDim, uSheen; uniform vec3 uCol, uWarn;
varying vec2 vUv;
float h1(float n){ return fract(sin(n)*43758.5453); }
void main(){
  vec2 p = vUv * uSize; vec2 e = min(p, uSize - p); float d = min(e.x, e.y);
  float rx = abs(vUv.x - 0.5) * 2.0;
  float on = smoothstep(uReveal + 0.002, uReveal - 0.002, rx);
  float lead = exp(-abs(rx - uReveal) * 60.0) * step(0.001, uReveal) * step(uReveal, 0.995);
  float fill = mix(0.50, 0.62, vUv.y);
  vec2 g = fract(p / 16.0) - 0.5; float dots = smoothstep(0.10, 0.0, length(g)) * 0.07;
  float scanY = fract(uTime * 0.06 + uSeed); float scan = exp(-pow((vUv.y - scanY) * 18.0, 2.0)) * 0.07;
  float edge = exp(-d / 0.9) * 0.55 + exp(-d / 10.0) * 0.08;
  float L = 30.0 + uHover * 20.0;
  float corner = max(step(e.x, L) * step(e.y, 2.2), step(e.y, L) * step(e.x, 2.2));
  // regla superior con marcas cada 24 px
  float ticks = step(uSize.y - p.y, 7.0) * step(p.y, uSize.y - 3.0) * step(fract(p.x / 24.0), 0.06) * 0.35;
  float flick = 0.96 + 0.04 * sin(uTime * 37.0 + uSeed * 10.0);
  vec3 line = uCol * (edge * (0.65 + uHover * 0.9) + corner * (0.9 + uHover) + dots * (0.6 + uHover) + scan + ticks) * flick;
  line += uCol * uFlash * (0.35 * exp(-d / 40.0) + 0.12);
  float sh = vUv.x * 0.8 + vUv.y * 0.55 - uSheen; float sheen = exp(-pow(sh * 7.0, 2.0)) * 0.10 + exp(-pow((sh - 0.12) * 30.0, 2.0)) * 0.05;
  line += vec3(0.75, 0.93, 1.0) * sheen * (0.6 + uHover * 0.6);
  float topGlow = exp(-(uSize.y - p.y) / 60.0) * 0.06; line += uCol * topGlow;
  line *= uDim;
  vec3 col = vec3(0.006, 0.028, 0.055) * fill + line + uCol * lead * 2.4;
  float a = fill * uAlpha;
  gl_FragColor = vec4(col * on + uCol * lead * 2.0, a * on);
}`

export const DUST_VS = /* glsl */ `
attribute float aSize; attribute float aPh; uniform float uTime, uPR, uWarp; varying float vA;
void main(){
  vec3 p = position; p.y += sin(uTime * 0.05 + aPh * 6.28) * 20.0;
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  float tw = 0.55 + 0.45 * sin(uTime * (0.6 + aPh) + aPh * 40.0);
  vA = tw * smoothstep(9000.0, 1500.0, -mv.z);
  gl_PointSize = aSize * uPR * (1500.0 / -mv.z) * (1.0 + uWarp * 1.5);
  gl_Position = projectionMatrix * mv;
}`

export const DUST_FS = /* glsl */ `varying float vA; uniform vec3 uCol; void main(){ vec2 c = gl_PointCoord - 0.5; float r = length(c); float a = (exp(-r * r * 22.0) + exp(-r * r * 90.0) * 0.8) * vA * 1.35; gl_FragColor = vec4(uCol * a, 0.0); }`

export const FLOOR_FS = /* glsl */ `
precision highp float; varying vec3 vW; uniform float uTime, uBoot; uniform vec3 uCol;
void main(){
  float r = length(vW.xz); float ang = atan(vW.z, vW.x);
  float ring = abs(fract(r / 220.0) - 0.5); float fw = fwidth(r / 220.0);
  float lr = smoothstep(fw * 1.5, 0.0, ring - 0.0) ;
  ring = 1.0 - smoothstep(0.0, fw * 1.2, abs(fract(r / 220.0 + 0.5) - 0.5));
  float sp = ang / 6.2831853 * 72.0; float sw = fwidth(sp);
  float spoke = 1.0 - smoothstep(0.0, sw * 1.2, abs(fract(sp) - 0.5) - 0.0 + 0.0) ;
  spoke = 1.0 - smoothstep(0.0, sw * 1.2, abs(fract(sp + 0.5) - 0.5));
  float fade = smoothstep(7500.0, 900.0, r) * smoothstep(250.0, 900.0, r);
  float sweep = pow(max(0.0, cos(ang - uTime * 0.35)), 40.0) * 0.6;
  float boot = smoothstep(uBoot * 7000.0, uBoot * 7000.0 - 600.0, r);
  float v = (ring * 0.35 + spoke * 0.12 + sweep * 0.25) * fade * boot;
  gl_FragColor = vec4(uCol * v, 0.0);
}`

export const FLOOR_VS = /* glsl */ `varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position,1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`

export const HALO_FS = /* glsl */ `
precision highp float; varying vec2 vUv;
uniform float uTime, uSpeed, uDash, uPulse, uGlitch, uBright, uVoice, uProg, uFlash, uBoot, uListen; uniform vec3 uCol; uniform float uSpec[48];
float h1(float n){ return fract(sin(n) * 43758.5453); }
float band(float r, float c, float w){ return exp(-pow((r - c) / w, 2.0)); }
void main(){
  vec2 p = (vUv - 0.5) * 2.0; float r = length(p); float a = atan(p.y, p.x); float u = a / 6.2831853 + 0.5;
  float boot = smoothstep(0.0, 1.0, uBoot);
  float gl = uGlitch * step(0.82, h1(floor(uTime * 12.0) + floor(u * 24.0)));
  float rr = r + gl * 0.02;
  float breathe = 1.0 + 0.012 * sin(uTime * 1.6) * uPulse;
  float v = 0.0;
  // anillo exterior fino + marcas (72), cada 6ª más larga
  v += band(rr, 0.92 * breathe, 0.004) * 0.9;
  float tk = fract(u * 72.0); float major = step(fract(u * 12.0), 0.012 * 12.0 / 1.0);
  v += step(tk, 0.12) * step(0.86, rr) * step(rr, 0.895 + major * 0.025) * 0.55;
  // guiones en órbita
  float du = fract(u * uDash - uTime * uSpeed); v += band(rr, 0.80, 0.010) * step(du, 0.55) * 0.9;
  // contra-órbita fina
  v += band(rr, 0.75, 0.003) * step(fract(u * 90.0 + uTime * uSpeed * 0.5), 0.5) * 0.45;
  // cometa
  float cu = fract(u - uTime * uSpeed * 0.35); v += band(rr, 0.80, 0.02) * pow(cu, 18.0) * 1.6;
  // arco de progreso (ejecutando)
  float pu = fract(0.25 - u + 1.0); v += band(rr, 0.70, 0.008) * step(pu, uProg) * 1.3;
  // espectro de voz (48 barras)
  float bi = floor(u * 48.0); float bf = fract(u * 48.0);
  int ii = int(bi); float s = 0.0; for (int k = 0; k < 48; k++) { if (k == ii) s = uSpec[k]; }
  float bar = step(0.25, bf) * step(bf, 0.75);
  float base = 0.6; float out1 = base + s * 0.28 * (1.0 - uListen); float in1 = base - s * 0.2 * uListen;
  v += bar * step(min(base, in1), rr) * step(rr, max(base + 0.004, out1)) * (0.5 + s) * step(0.02, s);
  v += band(rr, 0.6, 0.002) * 0.5;
  // núcleo suave (no disco: se ve detrás del avatar)
  v += exp(-pow((rr - 0.5) / 0.12, 2.0)) * 0.05 * (1.0 + uVoice);
  v *= boot * smoothstep(0.0, 0.05, abs(u - 0.5 + 0.5) + 1.0);
  // revelado angular durante el arranque
  v *= step(u, boot);
  v += uFlash * band(rr, 0.92 + (1.0 - uFlash) * 0.25, 0.05) * 1.2;
  v += band(rr, 0.92, 0.03) * 0.18 + band(rr, 0.80, 0.05) * 0.10 * uPulse;
  vec3 col = uCol * v * uBright * 1.25;
  col += vec3(1.0) * pow(v, 3.0) * 0.35;
  gl_FragColor = vec4(col, 0.0);
}`

export const VAULT_FS = /* glsl */ `precision highp float; varying vec3 vW; uniform float uTime, uBoot; uniform vec3 uCol;
  void main(){ vec3 d = normalize(vW); float lon = atan(d.x, -d.z) / 6.2831853 * 48.0; float lat = asin(clamp(d.y, -1.0, 1.0)) / 1.5707963 * 9.0;
    float fl = fwidth(lon), fa = fwidth(lat);
    float m = 1.0 - smoothstep(0.0, fl * 1.3, abs(fract(lon + 0.5) - 0.5)); float pz = 1.0 - smoothstep(0.0, fa * 1.3, abs(fract(lat + 0.5) - 0.5));
    float eq = exp(-pow(d.y / 0.015, 2.0)) * 0.6;
    float band = smoothstep(0.75, 0.0, abs(d.y)) * smoothstep(-0.35, 0.05, d.y);
    float sweep = pow(max(0.0, cos(atan(d.x, -d.z) - uTime * 0.12)), 60.0) * band;
    float v = (m * 0.08 + pz * 0.09) * band + eq * 0.3 + sweep * 0.16;
    gl_FragColor = vec4(uCol * v * uBoot, 0.0); }`

export const GLOW_FS = /* glsl */ `precision highp float; varying vec2 vUv; uniform float uTime, uVoice, uBoot; uniform vec3 uCol;
  float h(float n){ return fract(sin(n) * 43758.5453); }
  void main(){ vec2 p = (vUv - 0.5) * 2.0; float r = length(p); float a = atan(p.y, p.x);
    float rays = 0.55 + 0.45 * sin(a * 9.0 + uTime * 0.2) * sin(a * 23.0 - uTime * 0.13);
    float g = exp(-r * r * 5.0) * (0.22 + uVoice * 0.35) * (0.7 + 0.3 * rays) + exp(-r * r * 40.0) * 0.12;
    gl_FragColor = vec4(uCol * g * uBoot, 0.0); }`
