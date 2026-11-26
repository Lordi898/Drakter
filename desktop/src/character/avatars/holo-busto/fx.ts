// Partículas de Ascuario: ascuas y humo simulados en CPU (pocas, baratas) con búferes fijos. Una llamada de dibujo cada sistema.
import * as THREE from 'three';

export class Particles {
  readonly points: THREE.Points;
  private pos: Float32Array; private vel: Float32Array; private life: Float32Array; private max: Float32Array;
  private size: Float32Array; private base: Float32Array; private seed: Float32Array; private tint: Float32Array;
  private i = 0; private alive = 0;
  constructor(readonly n: number, mat: THREE.ShaderMaterial, private grow: number) {
    this.pos = new Float32Array(n * 3); this.vel = new Float32Array(n * 3); this.life = new Float32Array(n); this.max = new Float32Array(n).fill(1);
    this.size = new Float32Array(n); this.base = new Float32Array(n); this.seed = new Float32Array(n); this.tint = new Float32Array(n);
    for (let k = 0; k < n; k++) this.seed[k] = (k * 0.6180339) % 1;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aLife', new THREE.BufferAttribute(this.life, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aSize', new THREE.BufferAttribute(this.size, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aSeed', new THREE.BufferAttribute(this.seed, 1));
    g.setAttribute('aTint', new THREE.BufferAttribute(this.tint, 1).setUsage(THREE.DynamicDrawUsage));
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 20);
    this.points = new THREE.Points(g, mat); this.points.frustumCulled = false;
  }
  emit(x: number, y: number, z: number, vx: number, vy: number, vz: number, life: number, size: number, tint = 0): void {
    const k = this.i; this.i = (this.i + 1) % this.n;
    this.pos[k * 3] = x; this.pos[k * 3 + 1] = y; this.pos[k * 3 + 2] = z;
    this.vel[k * 3] = vx; this.vel[k * 3 + 1] = vy; this.vel[k * 3 + 2] = vz;
    this.life[k] = 1; this.max[k] = life; this.base[k] = size; this.tint[k] = tint;
    (this.points.geometry.attributes.aTint as THREE.BufferAttribute).needsUpdate = true;
  }
  /** Extingue rápido lo que haya (el humo "ahogado" al interrumpir). */
  choke(k = 4): void { for (let j = 0; j < this.n; j++) this.max[j] = Math.min(this.max[j]!, 1 / k); }
  update(dt: number, t: number, buoy: number, drag: number, turb: number): void {
    if (this.alive === 0 && this.life.every((l) => l <= 0)) return;
    let alive = 0;
    const p = this.pos, v = this.vel, dr = Math.exp(-drag * dt);
    for (let k = 0; k < this.n; k++) {
      if (this.life[k]! <= 0) continue;
      const l = (this.life[k] = this.life[k]! - dt / this.max[k]!);
      if (l <= 0) { this.life[k] = 0; this.size[k] = 0; continue; }
      alive++;
      const s = this.seed[k]!, j = k * 3;
      v[j] = (v[j]! + Math.sin(t * 1.7 + s * 31) * turb * dt) * dr;
      v[j + 1] = (v[j + 1]! + buoy * dt) * dr;
      v[j + 2] = (v[j + 2]! + Math.cos(t * 1.3 + s * 17) * turb * 0.6 * dt) * dr;
      p[j] = p[j]! + v[j]! * dt; p[j + 1] = p[j + 1]! + v[j + 1]! * dt; p[j + 2] = p[j + 2]! + v[j + 2]! * dt;
      this.size[k] = this.base[k]! * (1 + (1 - l) * this.grow);
    }
    this.alive = alive;
    const a = this.points.geometry.attributes;
    a.position!.needsUpdate = true; a.aLife!.needsUpdate = true; a.aSize!.needsUpdate = true;
  }
}
