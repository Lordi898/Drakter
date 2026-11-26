// Deformación de la piel (mandíbula, comisuras, pómulos, frente con las cejas, morro) en GLSL y en JS.
// Contornos (GPU) y trazos (CPU) usan la MISMA función sobre su posición de reposo: una sola piel.
import { MOUTH_Y, MOUTH_W, HINGE } from './sculpt';

export interface DeformU { jaw: number; smL: number; smR: number; lipW: number; round: number; liftL: number; liftR: number }
export const JAW_MAX = 0.17;
const f3 = (v: number): string => v.toFixed(4);

export const DEFORM_GLSL = /* glsl */ `
uniform float uJaw, uSmL, uSmR, uLipW, uRound, uLiftL, uLiftR;
void deform(inout vec3 p, inout vec3 n) {
  vec3 q = p; float sx = q.x < 0.0 ? -1.0 : 1.0, side = smoothstep(-0.14, 0.14, q.x), sm = mix(uSmL, uSmR, side), lf = mix(uLiftL, uLiftR, side), ax = abs(q.x); // mezcla suave: sin costura en el centro
  float front = smoothstep(0.2, 0.6, q.z);
  // Comisuras y pómulos.
  vec2 dc = vec2((ax - ${f3(MOUTH_W)}) / 0.09, (q.y - ${f3(MOUTH_Y)}) / 0.09); float gc = exp(-dot(dc, dc)) * front;
  p.y += sm * 0.058 * gc; p.x += sx * (sm * 0.016 + uLipW * 0.035 - uRound * 0.05) * gc; p.z -= abs(sm) * 0.012 * gc;
  vec2 dk = vec2((ax - 0.3) / 0.13, (q.y + 0.3) / 0.12); float gk = exp(-dot(dk, dk)) * max(sm, 0.0) * front;
  p.y += 0.02 * gk; p.z += 0.016 * gk;
  // Morro (O/U).
  vec2 dp = vec2(q.x / 0.15, (q.y - ${f3(MOUTH_Y)}) / 0.08); float gp = exp(-dot(dp, dp)) * front;
  p.z += uRound * 0.03 * gp; p.x *= 1.0 - uRound * 0.14 * gp;
  // Piel de la frente: acompaña a las cejas.
  float gb = smoothstep(0.08, 0.2, q.y) * (1.0 - smoothstep(0.3, 0.7, q.y)) * (1.0 - smoothstep(0.35, 0.55, ax)) * front;
  p.y += lf * 0.55 * gb;
  // Mandíbula: bisagra bajo las orejas.
  float w = smoothstep(${f3(MOUTH_Y + 0.004)}, ${f3(MOUTH_Y - 0.06)}, q.y) * (1.0 - smoothstep(0.42, 0.7, ax)) * smoothstep(-1.5, -1.12, q.y) * smoothstep(-0.45, -0.1, q.z);
  float a = uJaw * ${f3(JAW_MAX)} * w, c = cos(a), s = sin(a);
  vec3 o = p - vec3(${HINGE.map(f3).join(', ')});
  p = vec3(${HINGE.map(f3).join(', ')}) + vec3(o.x, o.y * c - o.z * s, o.y * s + o.z * c);
  n = vec3(n.x, n.y * c - n.z * s, n.y * s + n.z * c);
}`;

const ss = (a: number, b: number, x: number): number => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

export function deformJS(x: number, y: number, z: number, u: DeformU, out: [number, number, number]): [number, number, number] {
  const sx = x < 0 ? -1 : 1, side = ss(-0.14, 0.14, x), sm = u.smL + (u.smR - u.smL) * side, lf = u.liftL + (u.liftR - u.liftL) * side, ax = Math.abs(x), front = ss(0.2, 0.6, z);
  let px = x, py = y, pz = z;
  const dcx = (ax - MOUTH_W) / 0.09, dcy = (y - MOUTH_Y) / 0.09, gc = Math.exp(-(dcx * dcx + dcy * dcy)) * front;
  py += sm * 0.058 * gc; px += sx * (sm * 0.016 + u.lipW * 0.035 - u.round * 0.05) * gc; pz -= Math.abs(sm) * 0.012 * gc;
  const dkx = (ax - 0.3) / 0.13, dky = (y + 0.3) / 0.12, gk = Math.exp(-(dkx * dkx + dky * dky)) * Math.max(sm, 0) * front;
  py += 0.02 * gk; pz += 0.016 * gk;
  const dpx = x / 0.15, dpy = (y - MOUTH_Y) / 0.08, gp = Math.exp(-(dpx * dpx + dpy * dpy)) * front;
  pz += u.round * 0.03 * gp; px *= 1 - u.round * 0.14 * gp;
  const gb = ss(0.08, 0.2, y) * (1 - ss(0.3, 0.7, y)) * (1 - ss(0.35, 0.55, ax)) * front;
  py += lf * 0.55 * gb;
  const w = ss(MOUTH_Y + 0.004, MOUTH_Y - 0.06, y) * (1 - ss(0.42, 0.7, ax)) * ss(-1.5, -1.12, y) * ss(-0.45, -0.1, z);
  const a = u.jaw * JAW_MAX * w, c = Math.cos(a), s = Math.sin(a), oy = py - HINGE[1], oz = pz - HINGE[2];
  out[0] = px; out[1] = HINGE[1] + oy * c - oz * s; out[2] = HINGE[2] + oy * s + oz * c;
  return out;
}
