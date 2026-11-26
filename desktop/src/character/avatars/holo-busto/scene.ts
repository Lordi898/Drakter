// Escena de Holo-busto: rig, materiales, partículas y traducción de la pose a uniformes. Sin bucle, eventos ni
// estado del renderer: no llama a setSize/setPixelRatio (los fija el anfitrión) y render() dibuja en el viewport vigente.
import * as THREE from 'three';
import type { Pose, Zone } from './brain';
import * as S from './sculpt';
import { makeKit, holo, rigUniforms, eyeMat, lidMat, coreMat, backMat, motesMat, threadsMat, hairMat, setThemeBlending } from './mat';
import { Particles } from './fx';

export interface Geos { head: THREE.BufferGeometry; body: THREE.BufferGeometry; eye: THREE.BufferGeometry; lidUp: THREE.BufferGeometry; lidLow: THREE.BufferGeometry; hair: THREE.BufferGeometry }
export interface View { zoom?: number; tx?: number; ty?: number; hide?: string[] }

const FOV = 16.5, CAM_Z = 11.5, LOOK_Y = -0.28, LOOK_X = 0;

export function buildScene(gl: THREE.WebGLRenderer, geos: Geos, view: View = {}, look: { transparent?: boolean; theme?: 'dark' | 'light' } = {}) {
  const scene = new THREE.Scene();
  const kit = makeKit(), U = kit.U;
  const cam = new THREE.PerspectiveCamera(FOV, 1, 6, 20);
  const tx = view.tx ?? LOOK_X, ty = view.ty ?? LOOK_Y;
  cam.position.set(tx, ty + 0.25, CAM_Z); cam.lookAt(tx, ty, 0);

  const rHead = rigUniforms(0), rBody = rigUniforms(1);
  rHead.uHinge.value.set(...S.HINGE); rBody.uPivot.value.set(...S.PIVOT);
  const mHead = holo(kit, rHead), mBody = holo(kit, rBody), mUp = lidMat(kit, true), mLow = lidMat(kit, false);
  const mEye = [eyeMat(kit), eyeMat(kit)], mCore = coreMat(kit), mBack = backMat(kit), mMotes = motesMat(kit);
  const pair = (g: THREE.BufferGeometry, m: { pre: THREE.Material; light: THREE.Material; back?: THREE.Material }, parent: THREE.Object3D): THREE.Mesh => {
    const a = new THREE.Mesh(g, m.pre), b = new THREE.Mesh(g, m.light); a.renderOrder = 0; b.renderOrder = 2; parent.add(a, b);
    if (m.back) { const c = new THREE.Mesh(g, m.back); c.renderOrder = 1; c.name = 'back'; parent.add(c); }
    return b;
  };

  const back = new THREE.Mesh(new THREE.PlaneGeometry(8.5, 8.5), mBack); back.position.set(0, -0.4, -3.4); back.renderOrder = -1; scene.add(back);
  back.visible = !look.transparent;
  setThemeBlending(kit, look.theme === 'light');
  const bust = new THREE.Group(); scene.add(bust);
  pair(geos.body, mBody, bust);
  const core = new THREE.Mesh(new THREE.SphereGeometry(0.2, 24, 16), mCore); core.position.copy(U.uCorePos.value); core.renderOrder = 5; bust.add(core);
  const pivot = new THREE.Group(); pivot.position.set(...S.PIVOT); bust.add(pivot);
  const headBase = new THREE.Group(); headBase.position.set(S.HEAD[0] - S.PIVOT[0], S.HEAD[1] - S.PIVOT[1], S.HEAD[2] - S.PIVOT[2]); pivot.add(headBase);
  const head = pair(geos.head, mHead, headBase);
  const hair = new THREE.LineSegments(geos.hair, hairMat(kit)); hair.renderOrder = 3; hair.name = 'hair'; headBase.add(hair);

  const Z = new THREE.Vector3(0, 0, 1);
  const eyes: { s: number; socket: THREE.Group; eye: THREE.Mesh; up: THREE.Group; low: THREE.Group }[] = [];
  for (const s of [1, -1]) {
    const socket = new THREE.Group(); socket.position.set(s * S.EYE[0], S.EYE[1], S.EYE[2]);
    socket.quaternion.setFromUnitVectors(Z, new THREE.Vector3(s * 0.06, 0, 1).normalize()); headBase.add(socket);
    const eye = new THREE.Mesh(geos.eye, mEye[s > 0 ? 0 : 1]!); eye.renderOrder = 1; socket.add(eye);
    const up = new THREE.Group(), low = new THREE.Group(); socket.add(up, low);
    pair(geos.lidUp, mUp, up); pair(geos.lidLow, mLow, low);
    eyes.push({ s, socket, eye, up, low });
  }
  { // hilos de luz por detrás del busto
    const NT = 46, SEG = 28, P = new Float32Array(NT * SEG * 2 * 3), T = new Float32Array(NT * SEG * 2 * 3);
    let k = 0;
    for (let i = 0; i < NT; i++) { const sd = (i * 0.61803) % 1; for (let j = 0; j < SEG; j++) for (const u of [j / SEG, (j + 1) / SEG]) { T[k * 3] = i; T[k * 3 + 1] = u; T[k * 3 + 2] = sd; k++; } }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(P, 3)); g.setAttribute('aT', new THREE.BufferAttribute(T, 3));
    const th = new THREE.LineSegments(g, threadsMat(kit)); th.frustumCulled = false; th.renderOrder = -0.5; th.name = 'threads'; bust.add(th);
  }
  const motes = new Particles(150, mMotes, 0.2); motes.points.renderOrder = 6; motes.points.name = 'motes'; scene.add(motes.points);
  back.name = 'stagebg';

  const v1 = new THREE.Vector3(), v2 = new THREE.Vector3(), fwd = new THREE.Vector3(), mouthP = new THREE.Vector3(), m4 = new THREE.Matrix4();
  let W = 1, H = 1, last = { puff: 0, soot: 0, sparks: 0, sniff: 0, ring: 0 }, moteAcc = 0, shimmer = 0, glitch = 0;
  const rnd = (() => { let a = 0x9e3779b9; return () => { a ^= a << 13; a ^= a >>> 17; a ^= a << 5; return ((a >>> 0) % 10000) / 10000; }; })();
  const cA = new THREE.Color(), cF = new THREE.Color();
  const toLin = (c: THREE.Color, rgb: [number, number, number]): void => { c.setRGB(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, THREE.SRGBColorSpace); };
  const px = (p: THREE.Vector3): [number, number] => { p.project(cam); return [(p.x * 0.5 + 0.5) * W, (-p.y * 0.5 + 0.5) * H]; };
  const at = (x: number, y: number, z: number): THREE.Vector3 => head.localToWorld(v1.set(x, y, z));
  const zones: [Zone, () => THREE.Vector3, number][] = [
    ['eye', () => eyes[0]!.socket.getWorldPosition(v1), 0.15], ['eye', () => eyes[1]!.socket.getWorldPosition(v1), 0.15],
    ['brow', () => at(0.3, 0.25, 0.86), 0.13], ['brow', () => at(-0.3, 0.25, 0.86), 0.13],
    ['nose', () => at(0, -0.22, 1.12), 0.13], ['mouth', () => at(0, -0.62, 0.98), 0.17],
    ['ear', () => at(0.76, 0, -0.05), 0.2], ['ear', () => at(-0.76, 0, -0.05), 0.2],
    ['core', () => core.getWorldPosition(v1), 0.32], ['head', () => at(0, 0.2, 0.2), 1.0],
  ];

  if (view.hide?.length) scene.traverse((o) => { if (view.hide!.includes(o.name)) o.visible = false; });
  return {
    scene, cam,
    compile: () => gl.compileAsync(scene, cam),
    resize(w: number, h: number, dpr: number): void {
      W = w; H = h; cam.aspect = w / h;
      cam.fov = (w / h < 0.82 ? FOV * (0.82 / (w / h)) ** 0.75 : FOV) / (view.zoom ?? 1); cam.updateProjectionMatrix();
      mMotes.uniforms.uScale!.value = (h * dpr) / (2 * Math.tan((cam.fov * Math.PI) / 360));
    },
    face(): { x: number; y: number } { const [x, y] = px(at(0, 0, 0.8)); return { x, y }; },
    hit(x: number, y: number): Zone | null {
      const ppu = H / (2 * Math.tan((cam.fov * Math.PI) / 360) * CAM_Z);
      for (const [z, f, r] of zones) { const [sx, sy] = px(f()); if (Math.hypot(sx - x, sy - y) < r * ppu) return z; }
      return null;
    },
    anchors(): Record<string, [number, number]> {
      const o: Record<string, [number, number]> = {};
      const put = (k: string, p: THREE.Vector3): void => { const [x, y] = px(p); o[k] = [Math.round(x), Math.round(y)]; };
      put('eye', eyes[1]!.socket.getWorldPosition(v1)); put('brow', at(0.3, 0.25, 0.86)); put('nose', at(0, -0.22, 1.12)); put('mouth', at(0, -0.62, 0.98));
      put('ear', at(0.76, 0, -0.05)); put('core', core.getWorldPosition(v1)); put('head', at(0, 0.75, 0.4));
      return o;
    },
    render(p: Pose, dt: number): void {
      const t = p.t, st = p.state;
      toLin(cA, p.accent); toLin(cF, p.fire3);
      const lum = 0.2126 * cA.r + 0.7152 * cA.g + 0.0722 * cA.b; // luminancia normalizada: ningún estado se quema
      U.uTime.value = t; U.uCol.value.copy(cA).multiplyScalar(Math.min(1.4, 0.52 / Math.max(lum, 0.05))); U.uCore.value.copy(cF);
      U.uGlow.value = st === 'offline' ? 0.75 : Math.min(p.glow, 1.12); U.uVoice.value = p.level; U.uCold.value = p.cold; U.uMouthOpen.value = p.jaw;
      U.uCoreI.value = (0.45 + p.throat * 0.7 + p.fire * 0.25) * (st === 'offline' ? 0.25 : 1);
      const scanSpeed = st === 'executing' ? 0.55 : st === 'thinking' ? 0.28 : 0.1;
      U.uScanY.value = 1.6 - ((t * scanSpeed) % 1) * 4.6; U.uScanK.value = st === 'executing' ? 0.9 : st === 'offline' ? 0 : 0.35;
      U.uFlow.value = 1 + p.heat * 2.2 + (st === 'executing' ? 1.5 : 0); U.uListen.value = st === 'listening' ? 0.3 + p.level : 0;
      U.uRipple.value = p.ripple;
      glitch = st === 'error' ? Math.max(glitch - dt * 0.9, 0) : 0; if (st === 'error' && p.soot !== last.soot) glitch = 1;
      U.uGlitch.value = p.reduced ? 0 : glitch * glitch;
      if (p.ring !== last.ring) shimmer = 1; shimmer = Math.max(0, shimmer - dt * 0.8);
      U.uShimmer.value = p.reduced ? 0 : Math.sin(shimmer * Math.PI) * 0.6;
      mBack.uniforms.uSpin!.value = p.haloSpin; mBack.uniforms.uHalo!.value = p.halo;

      bust.position.set(0, p.breath * 0.012, p.lean * 0.2); bust.rotation.x = -p.lean * 0.03;
      pivot.rotation.set(p.pitch, p.yaw, p.roll, 'YXZ'); pivot.position.y = S.PIVOT[1] + p.breath * 0.008;
      rBody.uBendR.value.setFromMatrix4(m4.makeRotationFromEuler(pivot.rotation));
      rHead.uBrow.value.set(p.browL, p.browR, p.browTilt, 0);
      U.uFace.value.set((p.browL + p.browR) * 0.5, p.cornerL, p.cornerR, 0);
      rHead.uMouth.value.set(p.jaw, p.wide, p.round, 0);
      rHead.uLips.value.set(p.cornerL, p.cornerR, p.lipL, p.lipR);
      core.scale.setScalar(0.85 + p.level * 0.35 + Math.sin(t * 2.4) * 0.03);

      for (const e of eyes) {
        const L = e.s > 0, lid = L ? p.lidL : p.lidR, low = L ? p.lowL : p.lowR;
        e.eye.rotation.set(p.gy * 0.3, p.gx * 0.45, 0);
        e.up.rotation.set(-Math.asin(Math.max(-1, Math.min(1, -1.1 + 1.58 * lid))) + p.gy * 0.18, 0, -e.s * p.browTilt * 0.18);
        e.low.rotation.set(-Math.asin(Math.max(-1, Math.min(1, -0.5 + 0.78 * low))) - Math.max(0, p.gy) * 0.1, 0, e.s * p.browTilt * 0.06);
        const em = mEye[L ? 0 : 1]!; em.uniforms.uPupil!.value = p.pupil; em.uniforms.uEye!.value = 0.6 + 0.5 * p.eye;
      }

      bust.updateMatrixWorld(true);
      head.localToWorld(v2.set(0, 0, 0)); head.localToWorld(fwd.set(0, 0, 1)).sub(v2).normalize();
      head.localToWorld(mouthP.set(0, -0.62 - p.jaw * 0.1, 1.0));
      const r = rnd;
      const burst = (n: number, o: THREE.Vector3, sp: number, life: number, tint: number, spread = 0.2): void => {
        for (let k = 0; k < n; k++) motes.emit(o.x + (r() - 0.5) * spread, o.y + (r() - 0.5) * spread, o.z, (r() - 0.5) * sp + fwd.x * sp * 0.5, r() * sp + 0.1, fwd.z * sp * 0.5 + (r() - 0.5) * sp * 0.3, life * (0.7 + r() * 0.6), 0.03 + r() * 0.03, tint);
      };
      if (p.puff !== last.puff) burst(5, mouthP, 0.4, 1.2, 0.3, 0.1);
      if (p.sparks !== last.sparks) burst(40, v1.set(0, -1.55, 0.3), 1.6, 2.2, 1, 0.6);
      if (p.soot !== last.soot) burst(24, at(0, 0.2, 0.6), 1.2, 1.4, 0.5, 1.2);
      if (p.ring !== last.ring) burst(30, at(0, 0.3, 0.3), 0.9, 2, 0.2, 1.6);
      last = { puff: p.puff, soot: p.soot, sparks: p.sparks, sniff: p.sniff, ring: p.ring };
      // Motas de datos que suben alrededor del busto; más al hablar, ejecutar o pensar.
      moteAcc += dt * (st === 'offline' ? 0.6 : 3 + p.embers * 5 + p.level * 6);
      while (moteAcc > 1) {
        moteAcc -= 1;
        const a = r() * 6.28, rr = 1.2 + r() * 1.1;
        if (st === 'speaking' && p.jaw > 0.12 && r() < 0.5) motes.emit(mouthP.x + (r() - 0.5) * 0.2, mouthP.y, mouthP.z, (r() - 0.5) * 0.3, 0.25 + r() * 0.3, 0.2, 1.4, 0.025 + r() * 0.02, 0.6);
        else motes.emit(Math.cos(a) * rr, -2.6 + r() * 3.5, Math.sin(a) * rr * 0.5 - 0.2, (r() - 0.5) * 0.05, 0.12 + r() * 0.2, 0, 3 + r() * 3, 0.02 + r() * 0.03, r() < 0.15 ? 1 : 0);
      }
      motes.update(dt, t, 0.02, 0.3, p.reduced ? 0.02 : 0.08);
      gl.render(scene, cam);
    },
    setTheme(light: boolean, transparent: boolean): void { setThemeBlending(kit, light); back.visible = !transparent; },
    dispose(): void {
      const mats = new Set<THREE.Material>(), gs = new Set<THREE.BufferGeometry>();
      scene.traverse((o) => { const m = o as THREE.Mesh; if (m.geometry) gs.add(m.geometry); if (m.material) (Array.isArray(m.material) ? m.material : [m.material]).forEach((x) => mats.add(x)); });
      gs.forEach((g) => g.dispose()); mats.forEach((m) => m.dispose()); kit.lights.clear();
    },
  };
}
export type AvatarScene = ReturnType<typeof buildScene>;
