// Geometrías del rig. En producción vienen horneadas (baked.ts, generado por tools/bake.mjs) para arrancar sin bloquear;
// si no existe el horneado, se esculpen en caliente.
import * as THREE from 'three';
import type { Geos } from './scene';

type Packed = { n: number; pos: string; nor: string; mat: string; aux: string; uv: string; idx: string; big: boolean; lo: number[]; hi: number[] };
const b64 = (s: string): Uint8Array => { const bin = atob(s), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u; };

function unpack(p: Packed): THREE.BufferGeometry {
  const g = new THREE.BufferGeometry(), n = p.n;
  const q = new Uint16Array(b64(p.pos).buffer), pos = new Float32Array(n * 3);
  for (let i = 0; i < n * 3; i++) { const k = i % 3; pos[i] = p.lo[k]! + (q[i]! / 65535) * (p.hi[k]! - p.lo[k]!); }
  const nb = new Int8Array(b64(p.nor).buffer), nor = new Float32Array(n * 3); for (let i = 0; i < n * 3; i++) nor[i] = nb[i]! / 127;
  const mb = b64(p.mat), mat = new Float32Array(n); for (let i = 0; i < n; i++) mat[i] = mb[i]!;
  const ab = b64(p.aux), aux = new Float32Array(n * 3); for (let i = 0; i < n * 3; i++) aux[i] = ab[i]! / 255;
  const ub = new Uint16Array(b64(p.uv).buffer), uv = new Float32Array(n * 2); for (let i = 0; i < n * 2; i++) uv[i] = ub[i]! / 65535;
  const ib = b64(p.idx), idx = p.big ? new Uint32Array(ib.buffer) : new Uint16Array(ib.buffer);
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
  g.setAttribute('aMat', new THREE.BufferAttribute(mat, 1)); g.setAttribute('aAux', new THREE.BufferAttribute(aux, 3)); g.setAttribute('aUv', new THREE.BufferAttribute(uv, 2));
  g.setIndex(new THREE.BufferAttribute(idx, 1)); g.computeBoundingSphere();
  return g;
}

/** Desempaqueta por trozos entre fotogramas para no bloquear el hilo principal. */
export async function loadGeos(url?: string): Promise<Geos> {
  // 1) Bloque <script type="application/json" id="ascuario-geo"> (HTML autocontenido); 2) URL (módulo ES); 3) esculpir en caliente.
  if (typeof document !== 'undefined' && document.readyState === 'loading') await new Promise((r) => document.addEventListener('DOMContentLoaded', r, { once: true }));
  const tag = typeof document !== 'undefined' ? document.getElementById('ascuario-geo') : null;
  let data: Record<string, Packed> | null = null;
  if (tag?.textContent) data = JSON.parse(tag.textContent) as Record<string, Packed>;
  else if (url) data = (await (await fetch(url)).json()) as Record<string, Packed>;
  await new Promise((r) => setTimeout(r, 0));
  if (!data) { const S = await import('./sculpt'); return { head: S.buildHead(), jaw: S.buildJaw(), body: S.buildBody(), eye: S.buildEye(), lidUp: S.buildLidUp(), lidLow: S.buildLidLow(), brow: S.buildBrow(), frill: S.buildFrill(), monocle: S.buildMonocle() }; }
  const out: Record<string, THREE.BufferGeometry> = {};
  for (const k of Object.keys(data)) { out[k] = unpack(data[k]!); await new Promise((r) => setTimeout(r, 0)); }
  return out as unknown as Geos;
}
