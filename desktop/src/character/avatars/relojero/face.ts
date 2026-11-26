// Deformación de la cara (mandíbula, comisuras, pómulos, morro) en GLSL y su gemela en JS.
// Todo lo que vive en la cara —esmalte, labios, cavidad y láminas— se deforma con la MISMA función
// evaluada en su posición de reposo: la boca se abre sin costuras y las comisuras siguen unidas.
import { MOUTH_Y, LIP_W } from './geo';

export const JAW_MAX = 0.11; // radianes de giro de la mandíbula con uJaw = 1
const H = [0, -0.08, -0.25] as const; // bisagra (bajo las orejas, hacia atrás)

export const FACE_GLSL = /* glsl */ `
uniform float uJaw, uSmL, uSmR, uLipW, uRound;
float jawW(vec2 q) { return smoothstep(${(MOUTH_Y + 0.005).toFixed(3)}, ${(MOUTH_Y - 0.07).toFixed(3)}, q.y) * (1.0 - smoothstep(0.3, 0.56, abs(q.x))); }
void faceDeform(inout vec3 p, inout vec3 n) {
  vec2 q = p.xy; float sm = q.x < 0.0 ? uSmL : uSmR, sx = q.x < 0.0 ? -1.0 : 1.0;
  vec2 dc = vec2((abs(q.x) - ${(LIP_W * 0.92).toFixed(3)}) / 0.09, (q.y - ${MOUTH_Y.toFixed(3)}) / 0.085); float gc = exp(-dot(dc, dc));
  p.y += sm * 0.075 * gc; p.x += sx * (sm * 0.012 + uLipW * 0.05 - uRound * 0.035) * gc; p.z -= abs(sm) * 0.01 * gc;
  vec2 dk = vec2((abs(q.x) - 0.3) / 0.11, (q.y + 0.27) / 0.1); float gk = exp(-dot(dk, dk)) * max(sm, 0.0);
  p.y += 0.016 * gk; p.z += 0.014 * gk;
  vec2 dp = vec2(q.x / 0.13, (q.y - ${MOUTH_Y.toFixed(3)}) / 0.07); float gp = exp(-dot(dp, dp));
  p.z += uRound * 0.024 * gp; p.x *= 1.0 - uRound * 0.16 * gp;
  float a = uJaw * ${JAW_MAX.toFixed(3)} * jawW(q), c = cos(a), s = sin(a);
  vec3 o = p - vec3(${H.join(', ')});
  p = vec3(${H.join(', ')}) + vec3(o.x, o.y * c - o.z * s, o.y * s + o.z * c);
  n = vec3(n.x, n.y * c - n.z * s, n.y * s + n.z * c);
}`;

export interface FaceU { jaw: number; smL: number; smR: number; lipW: number; round: number }

const ss = (a: number, b: number, v: number): number => { const t = Math.min(1, Math.max(0, (v - a) / (b - a))); return t * t * (3 - 2 * t); };

/** Gemela en JS de faceDeform (para las láminas, calculadas en CPU). Escribe en out. */
export function faceDeformJS(x: number, y: number, z: number, f: FaceU, out: [number, number, number]): [number, number, number] {
  const sm = x < 0 ? f.smL : f.smR, sx = x < 0 ? -1 : 1;
  const dcx = (Math.abs(x) - LIP_W * 0.92) / 0.09, dcy = (y - MOUTH_Y) / 0.085, gc = Math.exp(-(dcx * dcx + dcy * dcy));
  let px = x, py = y, pz = z;
  py += sm * 0.075 * gc; px += sx * (sm * 0.012 + f.lipW * 0.05 - f.round * 0.035) * gc; pz -= Math.abs(sm) * 0.01 * gc;
  const dkx = (Math.abs(x) - 0.3) / 0.11, dky = (y + 0.27) / 0.1, gk = Math.exp(-(dkx * dkx + dky * dky)) * Math.max(sm, 0);
  py += 0.016 * gk; pz += 0.014 * gk;
  const dpx = x / 0.13, dpy = (y - MOUTH_Y) / 0.07, gp = Math.exp(-(dpx * dpx + dpy * dpy));
  pz += f.round * 0.024 * gp; px *= 1 - f.round * 0.16 * gp;
  const w = ss(MOUTH_Y + 0.005, MOUTH_Y - 0.07, y) * (1 - ss(0.3, 0.56, Math.abs(x)));
  const a = f.jaw * JAW_MAX * w, c = Math.cos(a), s = Math.sin(a);
  const oy = py - H[1], oz = pz - H[2];
  out[0] = px; out[1] = H[1] + oy * c - oz * s; out[2] = H[2] + oy * s + oz * c;
  return out;
}
