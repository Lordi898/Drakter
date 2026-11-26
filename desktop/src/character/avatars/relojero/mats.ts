// Materiales del Relojero. Todo procedural: los acabados de alta relojería (guilloché, côtes de Genève,
// minutería pintada) se calculan en el shader a partir de la posición del objeto; el relieve se finge
// con derivadas de pantalla. Sin texturas, sin pasadas extra.
import * as THREE from 'three';
import { FX, FY, FYC } from './geo';

const PERTURB = /* glsl */ `
varying vec3 vObj;
vec3 rlPerturb(vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDirection) {
  vec3 vSigmaX = normalize(dFdx(surf_pos)); vec3 vSigmaY = normalize(dFdy(surf_pos));
  vec3 R1 = cross(vSigmaY, surf_norm); vec3 R2 = cross(surf_norm, vSigmaX);
  float fDet = dot(vSigmaX, R1) * faceDirection;
  vec3 vGrad = sign(fDet) * (dHdxy.x * R1 + dHdxy.y * R2);
  return normalize(abs(fDet) * surf_norm - vGrad);
}`;

const PATTERNS: Record<string, string> = {
  // Olas de guilloché bajo esmalte translúcido (flinqué).
  guilloche: /* glsl */ `float pat(vec3 p){ float w = (p.y + 0.012*sin(p.x*24.0 + p.z*11.0) + 0.004*sin(p.x*61.0)) * 210.0; return 0.5+0.5*sin(w); }`,
  // Côtes de Genève: bandas diagonales con perfil de arco.
  cotes: /* glsl */ `float pat(vec3 p){ float u = fract((p.x*0.8 + p.y*0.6) * 13.0); return 1.0 - pow(abs(u*2.0-1.0), 2.0); }`,
  // Satinado soleil: rayos finos desde el centro de la cara.
  soleil: /* glsl */ `float pat(vec3 p){ float a = atan(p.y+0.04, p.x); return 0.5+0.5*sin(a*260.0 + sin(a*7.0)*3.0); }`,
};

/** MeshStandard con dibujo de relieve procedural (onBeforeCompile). */
export function patterned(params: THREE.MeshStandardMaterialParameters, kind: keyof typeof PATTERNS, bump: number, tint: number, rough: number): THREE.MeshStandardMaterial {
  const m = new THREE.MeshStandardMaterial(params);
  m.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vObj;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvObj = position;');
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', `#include <common>\n${PERTURB}\n${PATTERNS[kind]}`)
      .replace('#include <color_fragment>', `#include <color_fragment>\nfloat hP = pat(vObj); float fw = clamp(fwidth(hP)*0.9, 0.0, 1.0); float hS = mix(hP, 0.5, fw);\ndiffuseColor.rgb *= ${(1 - tint).toFixed(3)} + ${(2 * tint).toFixed(3)} * hS;`)
      .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>\nroughnessFactor = clamp(roughnessFactor + ${rough.toFixed(3)} * (hS - 0.5), 0.04, 1.0);`)
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>\nnormal = rlPerturb(-vViewPosition, normal, vec2(dFdx(hS), dFdy(hS)) * ${bump.toFixed(4)} * (1.0 - fw), faceDirection);`);
  };
  m.customProgramCacheKey = () => 'pat-' + kind;
  return m;
}

/** Esmalte grand feu de la cara, con la minutería «pintada» siguiendo el contorno de la esfera. */
export function enamel(): THREE.MeshStandardMaterial {
  const m = new THREE.MeshStandardMaterial({ color: 0xf1e8d6, roughness: 0.24, metalness: 0, vertexColors: true });
  m.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vObj;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvObj = position;');
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vObj;')
      .replace('#include <color_fragment>', /* glsl */ `#include <color_fragment>
      {
        vec2 q = vec2(vObj.x / ${FX.toFixed(3)}, (vObj.y - ${FYC.toFixed(3)}) / ${FY.toFixed(3)});
        float e = length(q), a = atan(q.x, q.y) / 6.28318 + 0.5; // 0 arriba, sentido horario
        float aw = fwidth(a * 60.0), ew = fwidth(e);
        float m60 = abs(fract(a * 60.0 + 0.5) - 0.5), m12 = abs(fract(a * 12.0 + 0.5) - 0.5) * 5.0;
        float rail = (1.0 - smoothstep(0.0, ew * 1.5, abs(e - 0.905))) + (1.0 - smoothstep(0.0, ew * 1.5, abs(e - 0.955)));
        float tick = (1.0 - smoothstep(0.06, 0.06 + aw, m60)) * step(0.905, e) * step(e, 0.955);
        float hour = (1.0 - smoothstep(0.1, 0.1 + aw, m12)) * step(0.86, e) * step(e, 0.96);
        float ink = clamp(rail * 0.8 + tick + hour, 0.0, 1.0);
        diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.05, 0.07, 0.16), ink * 0.85);
        diffuseColor.rgb *= 0.94 + 0.06 * smoothstep(0.95, 0.4, e); // el esmalte se templa hacia el borde
      }`);
  };
  m.customProgramCacheKey = () => 'enamel';
  return m;
}

/** Cristal de zafiro: solo reflejo de Fresnel y una ráfaga de luz, aditivo. Sin transmisión (cara en esta GPU). */
export function crystal(): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor, // luz: alfa 0 = suma en lienzos opacos y transparentes
    uniforms: { uT: { value: 0 }, uFlash: { value: 0 }, uTint: { value: new THREE.Color(1, 0.9, 0.75) } },
    vertexShader: /* glsl */ `varying vec3 vN; varying vec3 vV; varying vec3 vP;
      void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0); vN = normalize(normalMatrix*normal); vV = -mv.xyz; vP = position; gl_Position = projectionMatrix*mv; }`,
    fragmentShader: /* glsl */ `uniform float uT, uFlash; uniform vec3 uTint; varying vec3 vN; varying vec3 vV; varying vec3 vP;
      void main(){ float f = pow(1.0 - max(dot(normalize(vN), normalize(vV)), 0.0), 2.6);
        float band = vP.x * 0.8 + vP.y - 1.6 + mod(uT * 0.11, 3.4);
        float streak = exp(-band*band*90.0) * (0.12 + uFlash * 0.6) + exp(-(band+0.12)*(band+0.12)*900.0) * 0.08;
        gl_FragColor = vec4(uTint * (0.02 + f * 0.55 + streak), 0.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

/** Fondo de la cuenca del ojo: laca de noche con un polvo de estrellas que gira con la órbita. */
export function nightSky(): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: { uT: { value: 0 }, uC: { value: new THREE.Color(1, 0.7, 0.4) }, uG: { value: 1 } },
    vertexShader: /* glsl */ `varying vec2 vU; attribute float aSide; varying float vS; void main(){ vU = position.xy; vS = aSide; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
    fragmentShader: /* glsl */ `uniform float uT, uG; uniform vec3 uC; varying vec2 vU; varying float vS;
      float h(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      void main(){ vec2 c = vU - vec2(vS * 0.25, 0.0); float r = length(c) / 0.115;
        float a = atan(c.y, c.x) + uT * 0.05; vec2 p = vec2(cos(a), sin(a)) * r * 9.0;
        vec2 id = floor(p); float s = h(id); vec2 f = fract(p) - 0.5;
        float star = step(0.86, s) * smoothstep(0.18, 0.0, length(f)) * (0.5 + 0.5 * sin(uT * 2.0 + s * 40.0));
        vec3 col = mix(vec3(0.03, 0.05, 0.13), vec3(0.008, 0.01, 0.03), r) + uC * 0.18 * (1.0 - r) * uG + vec3(0.9, 0.85, 0.7) * star * 0.7 * uG;
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

/** Brillo falso: puntos aditivos con color y tamaño por vértice (sustituye al bloom). */
export function glowPoints(n: number): { pts: THREE.Points; pos: Float32Array; col: Float32Array; size: Float32Array; mat: THREE.ShaderMaterial } {
  const geo = new THREE.BufferGeometry(), pos = new Float32Array(n * 3), col = new Float32Array(n * 3), size = new Float32Array(n);
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3).setUsage(THREE.DynamicDrawUsage));
  geo.setAttribute('aCol', new THREE.BufferAttribute(col, 3).setUsage(THREE.DynamicDrawUsage));
  geo.setAttribute('aSize', new THREE.BufferAttribute(size, 1).setUsage(THREE.DynamicDrawUsage));
  const mat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, depthTest: true, blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
    uniforms: { uPx: { value: 600 }, uGain: { value: 1 } },
    vertexShader: /* glsl */ `attribute vec3 aCol; attribute float aSize; uniform float uPx; varying vec3 vC;
      void main(){ vec4 mv = modelViewMatrix*vec4(position,1.0); vC = aCol; gl_PointSize = aSize * uPx / -mv.z; gl_Position = projectionMatrix*mv; gl_Position.z -= 0.02 * gl_Position.w; }`,
    fragmentShader: /* glsl */ `varying vec3 vC; uniform float uGain; void main(){ vec2 d = gl_PointCoord - 0.5; float r2 = dot(d,d) * 4.0;
      float a = exp(-r2 * 9.0) * 0.9 + exp(-r2 * 2.2) * 0.25; a *= 1.0 - smoothstep(0.7, 1.0, r2);
      gl_FragColor = vec4(vC * a * uGain, 0.0); }`,
  });
  const pts = new THREE.Points(geo, mat); pts.frustumCulled = false; pts.renderOrder = 10;
  return { pts, pos, col, size, mat };
}

/** Fondo: gradiente de noche con un sol de guilloché tenue detrás de la cabeza. Un triángulo a pantalla completa. */
export function backdrop(): THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial> {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3));
  const mat = new THREE.ShaderMaterial({
    depthWrite: false, depthTest: false,
    uniforms: { uC: { value: new THREE.Color(1, 0.7, 0.4) }, uG: { value: 1 }, uHead: { value: new THREE.Vector2(0.5, 0.62) }, uAsp: { value: 0.83 }, uCold: { value: 0 } },
    vertexShader: /* glsl */ `varying vec2 vU; void main(){ vU = position.xy*0.5+0.5; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
    fragmentShader: /* glsl */ `uniform vec3 uC; uniform float uG, uAsp, uCold; uniform vec2 uHead; varying vec2 vU;
      void main(){ vec2 d = (vU - uHead) * vec2(uAsp, 1.0); float r = length(d);
        vec3 deep = mix(vec3(0.0035, 0.005, 0.013), vec3(0.003, 0.005, 0.012), uCold);
        vec3 col = mix(vec3(0.016, 0.02, 0.045), deep, smoothstep(0.0, 0.8, r));
        float a = atan(d.y, d.x); float rays = 0.5 + 0.5 * sin(a * 72.0);
        col += uC * (0.022 * exp(-r * 3.0) * uG) * (0.6 + 0.4 * rays);
        col *= 1.0 - 0.45 * smoothstep(0.45, 1.1, length((vU - 0.5) * vec2(1.0, 1.15)));
        gl_FragColor = vec4(col, 1.0);
        #include <colorspace_fragment>
      }`,
  });
  const m = new THREE.Mesh(geo, mat); m.frustumCulled = false; m.renderOrder = -10;
  return m;
}

/** MeshStandard de vértices coloreados cuyo vertex shader hace girar cada pieza del mecanismo en su pivote. */
export function mechanism(): THREE.MeshStandardMaterial {
  const m = new THREE.MeshStandardMaterial({ vertexColors: true, metalness: 1, roughness: 0.26 });
  const u = { uRot: { value: new THREE.Vector3() } };
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uRot = u.uRot;
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nattribute vec2 aPiv; attribute vec3 aRate; uniform vec3 uRot;\nmat2 rlRot(float a){ float c = cos(a), s = sin(a); return mat2(c, s, -s, c); }')
      .replace('#include <beginnormal_vertex>', '#include <beginnormal_vertex>\nfloat rlA = dot(aRate, uRot); objectNormal.xy = rlRot(rlA) * objectNormal.xy;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\ntransformed.xy = rlRot(rlA) * (transformed.xy - aPiv) + aPiv;');
  };
  m.customProgramCacheKey = () => 'mech';
  m.userData.u = u;
  return m;
}
