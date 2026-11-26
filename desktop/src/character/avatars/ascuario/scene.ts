// Escena de Ascuario: rig, materiales, partículas y traducción de la pose a uniformes. Sin bucle ni eventos (eso vive en index.ts).
import * as THREE from 'three';
import type { Pose, Zone } from './brain';
import * as S from './sculpt';
import { U, skin, eyeMat, glassMat, gemMat, haloMat, pointsMat } from './mat';
import { Particles } from './fx';

export interface Geos { head: THREE.BufferGeometry; jaw: THREE.BufferGeometry; body: THREE.BufferGeometry; eye: THREE.BufferGeometry; lidUp: THREE.BufferGeometry; lidLow: THREE.BufferGeometry; brow: THREE.BufferGeometry; frill: THREE.BufferGeometry; monocle: THREE.BufferGeometry }
export interface View { zoom?: number; tx?: number; ty?: number }

const FOV = 20.5, CAM_Z = 11.5, LOOK_Y = -0.74, LOOK_X = 0.14;
const BASE_YAW = 0.5, BASE_PITCH = 0.14;

/** `transparent`: sin fondo propio (el halo es el fondo), para flotar sobre la interfaz. */
export function buildScene(gl: THREE.WebGLRenderer, geos: Geos, view: View = {}, transparent = false) {
  const scene = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(FOV, 1, 6, 20);
  const tx = view.tx ?? LOOK_X, ty = view.ty ?? LOOK_Y;
  cam.position.set(tx, ty + 0.15, CAM_Z); cam.lookAt(tx, ty, 0);

  const mHead = skin({ density: 13, gold: 1, soft: 1, mouth: new THREE.Vector3(), mouthKind: 1 });
  const mJaw = skin({ density: 13, gold: 1, soft: 1, mouth: new THREE.Vector3(...S.HINGE), mouthKind: 2 });
  const mBody = skin({ density: 10, gold: 0.9, soft: 2, bend: true });
  const mSmall = skin({ density: 30, gold: 0.25 });
  const mBrow = skin({ density: 22, gold: 1.6, side: THREE.DoubleSide });
  const mFrill = skin({ density: 10, gold: 1, side: THREE.DoubleSide });
  const mGold = skin({});
  const mEye = [eyeMat(), eyeMat()], mGlass = glassMat(), mGem = gemMat(), mHalo = haloMat();
  const mEmber = pointsMat('ember'), mSmoke = pointsMat('smoke');

  const halo = new THREE.Mesh(new THREE.PlaneGeometry(7.4, 7.4), mHalo); halo.position.set(0.3, -0.5, -3.2); halo.renderOrder = -1; halo.visible = !transparent; scene.add(halo);
  const bust = new THREE.Group(); scene.add(bust);
  const body = new THREE.Mesh(geos.body, mBody); bust.add(body);
  const gem = new THREE.Mesh(new THREE.IcosahedronGeometry(0.11, 1), mGem); gem.position.set(S.MEDAL[0], S.MEDAL[1], S.MEDAL[2] + 0.05); gem.scale.set(1, 1.25, 0.6); gem.rotation.x = -0.25; bust.add(gem);
  const pivot = new THREE.Group(); pivot.position.set(...S.PIVOT); bust.add(pivot);
  const headBase = new THREE.Group(); headBase.position.set(0, 0.36, 0.4); headBase.scale.setScalar(1.3); headBase.rotation.set(BASE_PITCH, BASE_YAW, 0, 'YXZ'); pivot.add(headBase);
  const head = new THREE.Mesh(geos.head, mHead); headBase.add(head);
  const jawPivot = new THREE.Group(); jawPivot.position.set(...S.HINGE); headBase.add(jawPivot);
  const jaw = new THREE.Mesh(geos.jaw, mJaw); jawPivot.add(jaw);

  const Z = new THREE.Vector3(0, 0, 1);
  const eyes: { s: number; socket: THREE.Group; eye: THREE.Mesh; up: THREE.Mesh; low: THREE.Mesh; brow: THREE.Group; plate: THREE.Mesh; frill: THREE.Group }[] = [];
  for (const s of [1, -1]) {
    const socket = new THREE.Group(); socket.position.set(s * S.EYE[0], S.EYE[1], S.EYE[2]);
    socket.quaternion.setFromUnitVectors(Z, new THREE.Vector3(s * 0.42, 0.02, 1).normalize()); headBase.add(socket);
    const eye = new THREE.Mesh(geos.eye, mEye[s > 0 ? 0 : 1]!); socket.add(eye);
    const up = new THREE.Mesh(geos.lidUp, mSmall); socket.add(up);
    const low = new THREE.Mesh(geos.lidLow, mSmall); socket.add(low);
    const brow = new THREE.Group(); brow.position.set(s * 0.13, 0.405, 0.71); brow.rotation.y = s > 0 ? 0.62 : Math.PI - 0.62; headBase.add(brow);
    const plate = new THREE.Mesh(geos.brow, mBrow); if (s < 0) plate.scale.z = -1; brow.add(plate);
    const frill = new THREE.Group(); frill.position.set(s * 0.55, 0.05, -0.38); headBase.add(frill);
    frill.add(new THREE.Mesh(geos.frill, mFrill));
    eyes.push({ s, socket, eye, up, low, brow, plate, frill });
  }
  const monocle = new THREE.Group(); scene.add(monocle);
  monocle.add(new THREE.Mesh(geos.monocle, mGold)); monocle.scale.setScalar(1.2);
  const lens = new THREE.Mesh(new THREE.CircleGeometry(0.157, 40), mGlass); lens.renderOrder = 2; monocle.add(lens);
  const chain = new S.Chain(); const chainMesh = new THREE.Mesh(chain.geo, mGold); chainMesh.frustumCulled = false; scene.add(chainMesh);
  const embers = new Particles(110, mEmber, -0.4), smoke = new Particles(72, mSmoke, 2.6);
  scene.add(smoke.points, embers.points); embers.points.renderOrder = 4; smoke.points.renderOrder = 3;

  const v1 = new THREE.Vector3(), v2 = new THREE.Vector3(), v3 = new THREE.Vector3(), fwd = new THREE.Vector3(), upW = new THREE.Vector3(), sideW = new THREE.Vector3();
  const nosL = new THREE.Vector3(), nosR = new THREE.Vector3(), mouthP = new THREE.Vector3(), lipsP = new THREE.Vector3(), wornP = new THREE.Vector3(), hangP = new THREE.Vector3(), anchorW = new THREE.Vector3();
  const qWorn = new THREE.Quaternion(), qHang = new THREE.Quaternion(), eul = new THREE.Euler(), m4 = new THREE.Matrix4();
  const MON_LOCAL = new THREE.Vector3(-S.EYE[0] - 0.06, S.EYE[1] + 0.004, S.EYE[2] + 0.15), MON_ATTACH = new THREE.Vector3(0.117, -0.117, 0).multiplyScalar(1.2);
  const qMonLocal = new THREE.Quaternion().setFromUnitVectors(Z, new THREE.Vector3(-0.42, 0.02, 1).normalize());
  let W = 1, H = 1, last = { puff: 0, soot: 0, sparks: 0, sniff: 0, ring: 0 }, smokeAcc = 0, emberAcc = 0, side = 0, wasInterrupted = false;
  const rnd = (() => { let a = 0x9e3779b9; return () => { a ^= a << 13; a ^= a >>> 17; a ^= a << 5; return ((a >>> 0) % 10000) / 10000; }; })();
  const accentC = new THREE.Color(), fireC = new THREE.Color();
  const toLin = (c: THREE.Color, rgb: [number, number, number]): void => { c.setRGB(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, THREE.SRGBColorSpace); };
  const nostrilBurst = (n: number, speed: number, life: number, size: number, tint: number, sm: Particles): void => {
    for (let k = 0; k < n; k++) {
      const p = k % 2 ? nosL : nosR, r = rnd;
      sm.emit(p.x, p.y, p.z, fwd.x * speed + (r() - 0.5) * 0.25, fwd.y * speed + 0.15 + r() * 0.2, fwd.z * speed + (r() - 0.5) * 0.25, life * (0.7 + r() * 0.6), size * (0.7 + r() * 0.6), tint);
    }
  };
  const px = (p: THREE.Vector3): [number, number] => { p.project(cam); return [(p.x * 0.5 + 0.5) * W, (-p.y * 0.5 + 0.5) * H]; };
  const zones: [Zone, () => THREE.Vector3, number][] = [
    ['monocle', () => monocle.getWorldPosition(v1), 0.24], ['eye', () => eyes[1]!.socket.getWorldPosition(v1), 0.2], ['eye', () => eyes[0]!.socket.getWorldPosition(v1), 0.2],
    ['gem', () => gem.getWorldPosition(v1), 0.26], ['snout', () => v1.copy(nosL).add(nosR).multiplyScalar(0.5), 0.32],
    ['frill', () => eyes[1]!.frill.localToWorld(v1.set(0.35, 0.1, 0)), 0.3], ['frill', () => eyes[0]!.frill.localToWorld(v1.set(0.35, 0.1, 0)), 0.3],
    ['horn', () => head.localToWorld(v1.set(0.64, 0.86, -1.2)), 0.36], ['horn', () => head.localToWorld(v1.set(-0.64, 0.86, -1.2)), 0.36],
    ['head', () => head.localToWorld(v1.set(0, 0.1, 0.3)), 0.95],
  ];

  return {
    scene, cam,
    /** Compila los programas sin bloquear (KHR_parallel_shader_compile cuando existe). */
    compile: () => gl.compileAsync(scene, cam),
    resize(w: number, h: number, dpr: number): void {
      W = w; H = h; gl.setPixelRatio(dpr); gl.setSize(w, h, false); cam.aspect = w / h;
      cam.fov = (w / h < 0.82 ? FOV * (0.82 / (w / h)) ** 0.75 : FOV) / (view.zoom ?? 1); cam.updateProjectionMatrix();
      const sc = (h * dpr) / (2 * Math.tan((cam.fov * Math.PI) / 360));
      mEmber.uniforms.uScale!.value = sc; mSmoke.uniforms.uScale!.value = sc;
    },
    face(): { x: number; y: number } { const [x, y] = px(head.localToWorld(v1.set(0, 0.15, 0.5))); return { x, y }; },
    hit(x: number, y: number): Zone | null {
      const pxPerUnit = H / (2 * Math.tan((cam.fov * Math.PI) / 360) * CAM_Z);
      for (const [z, f, r] of zones) { const [sx, sy] = px(f()); if (Math.hypot(sx - x, sy - y) < r * pxPerUnit) return z; }
      return null;
    },
    anchors(): Record<string, [number, number]> {
      const o: Record<string, [number, number]> = {};
      const put = (k: string, p: THREE.Vector3): void => { const [x, y] = px(p); o[k] = [Math.round(x), Math.round(y)]; };
      put('monocle', monocle.getWorldPosition(v1)); put('eye', eyes[0]!.socket.getWorldPosition(v1)); put('gem', gem.getWorldPosition(v1));
      put('snout', v1.copy(nosL).add(nosR).multiplyScalar(0.5)); put('frill', eyes[1]!.frill.localToWorld(v1.set(0.35, 0.1, 0))); put('horn', head.localToWorld(v1.set(0.64, 0.86, -1.2)));
      put('head', head.localToWorld(v1.set(0, 0.45, -0.2)));
      return o;
    },
    render(p: Pose, dt: number): void {
      const t = p.t;
      U.uTime.value = t; U.uGlow.value = p.glow; U.uFire.value = p.fire; U.uCold.value = p.cold; U.uThroat.value = p.throat; U.uMouthGlow.value = p.mouthGlow;
      toLin(accentC, p.accent); U.uRimCol.value.copy(accentC).multiplyScalar(0.55 + 0.45 * p.glow);
      toLin(fireC, p.fire3); U.uFireCol.value.copy(fireC);
      U.uGlint.value = p.glint; U.uRipple.value = p.ripple;
      mHalo.uniforms.uSpin!.value = p.haloSpin; mHalo.uniforms.uHalo!.value = p.halo;

      bust.position.set(0, p.breath * 0.012, p.lean * 0.22); bust.rotation.x = -p.lean * 0.035;
      body.scale.set(1 + p.breath * 0.006, 1, 1 + p.breath * 0.01);
      pivot.rotation.set(p.pitch, p.yaw, p.roll, 'YXZ'); pivot.position.y = S.PIVOT[1] + p.breath * 0.01;
      (mBody.uniforms.uBendR!.value as THREE.Matrix3).setFromMatrix4(m4.makeRotationFromEuler(pivot.rotation));
      (mBody.uniforms.uPivot!.value as THREE.Vector3).set(...S.PIVOT);
      jawPivot.rotation.x = p.jaw * 0.4;
      for (const m of [mHead, mJaw]) { (m.uniforms.uMouthDef!.value as THREE.Vector4).set(p.wide, p.round, p.cornerL, p.cornerR); const x = m.uniforms.uMouthX!.value as THREE.Vector3; x.y = p.lipL; x.z = p.lipR; }

      for (const e of eyes) {
        const L = e.s > 0;
        const lid = L ? p.lidL : p.lidR, low = L ? p.lowL : p.lowR, br = L ? p.browL : p.browR;
        e.eye.rotation.set(p.gy * 0.32, p.gx * 0.48 - e.s * 0.04 - 0.3, 0); // −0.3: le busca con los ojos aunque la cabeza esté de tres cuartos
        e.up.rotation.set(1.6 - 2.15 * lid + p.gy * 0.18, 0, -e.s * (p.browTilt * 0.24 + 0.1));
        e.low.rotation.set(0.6 - 0.8 * low - Math.max(0, p.gy) * 0.1, 0, e.s * (p.browTilt * 0.08 + 0.12));
        // Ceja: sube y baja con rango amplio; la inclinación separa enfado (+) de preocupación (−).
        e.brow.position.y = 0.405 + br * 0.085 - Math.max(0, p.browTilt) * 0.03 + Math.max(0, -p.browTilt) * 0.02;
        e.brow.position.z = 0.69 - Math.max(0, br) * 0.015 + Math.max(0, p.browTilt) * 0.02;
        e.plate.rotation.set(-0.18 - Math.max(0, br) * 0.14, 0, br * 0.22 + p.browTilt * 0.42);
        const fr = p.frill, fl = p.flick * 0.25;
        const fy = 1.15 - fr * 0.35 - fl; e.frill.rotation.set(0, L ? fy : Math.PI - fy, 0.12 + fr * 0.22 + fl * 0.5, 'YXZ');
        e.frill.scale.set(1, 0.85 + Math.max(fr, -0.5) * 0.18, 1);
        const em = mEye[L ? 0 : 1]!; em.uniforms.uPupil!.value = p.pupil; em.uniforms.uEye!.value = p.eye * (0.75 + 0.35 * p.glow);
      }

      bust.updateMatrixWorld(true);
      head.localToWorld(nosL.set(S.NOSTRIL[0], S.NOSTRIL[1], S.NOSTRIL[2] + 0.03)); head.localToWorld(nosR.set(-S.NOSTRIL[0], S.NOSTRIL[1], S.NOSTRIL[2] + 0.03));
      head.localToWorld(v2.set(0, 0, 0)); head.localToWorld(fwd.set(0, -0.05, 2)).sub(v2).normalize();
      head.localToWorld(upW.set(0, 1, 0)).sub(v2).normalize(); sideW.crossVectors(fwd, upW).normalize();
      jaw.localToWorld(mouthP.set(0, S.mouthY(0.8) - S.HINGE[1] + 0.03, 0.8 - S.HINGE[2]));
      head.localToWorld(lipsP.set(0, S.mouthY(1.2) - 0.01, 1.22));
      U.uRippleO.value.copy(nosL).add(nosR).multiplyScalar(0.5);

      headBase.localToWorld(wornP.copy(MON_LOCAL));
      headBase.getWorldQuaternion(qWorn).multiply(qMonLocal);
      body.localToWorld(anchorW.set(...S.ANCHOR));
      const sw = p.swing;
      hangP.set(anchorW.x + Math.sin(sw) * 0.42, anchorW.y - Math.cos(sw) * 0.42 + 0.02, anchorW.z + 0.12);
      eul.set(0.1, 0.25, sw * 0.8); qHang.setFromEuler(eul);
      const d = p.drop, de = d * d * (3 - 2 * d);
      monocle.position.lerpVectors(wornP, hangP, de);
      monocle.quaternion.slerpQuaternions(qWorn, qHang, de);
      monocle.position.y += (p.lowR * 0.025 + Math.max(0, p.cornerR) * 0.02) * (1 - de); // la mejilla empuja el monóculo
      monocle.updateMatrixWorld();
      monocle.localToWorld(v1.copy(MON_ATTACH));
      v3.copy(v1).add(anchorW).multiplyScalar(0.5); v3.y -= 0.3 * (1 - de) + 0.04; v3.z += 0.12 * (1 - de);
      chain.update(v1, v3, anchorW);

      const r = rnd;
      if (p.puff !== last.puff) { nostrilBurst(6, 0.55, 1.6, 0.28, 0, smoke); nostrilBurst(3, 0.7, 0.9, 0.05, 0, embers); }
      if (p.soot !== last.soot) { nostrilBurst(16, 0.5, 2.4, 0.42, 1, smoke); for (let k = 0; k < 8; k++) smoke.emit(mouthP.x, mouthP.y, mouthP.z, (r() - 0.5) * 0.5, 0.2 + r() * 0.3, 0.3, 2.2, 0.36, 1); }
      if (p.sparks !== last.sparks) for (let k = 0; k < 34; k++) { const pp = k % 2 ? nosL : nosR, a = r() * 6.28, sp = 0.6 + r() * 0.9; embers.emit(pp.x, pp.y, pp.z, Math.cos(a) * sp * 0.6 + fwd.x * 0.4, 0.5 + r() * 1.1, Math.sin(a) * sp * 0.5 + fwd.z * 0.4, 1.3 + r() * 0.8, 0.07 + r() * 0.05, 1); }
      if (p.sniff !== last.sniff) for (let k = 0; k < 6; k++) { const pp = k % 2 ? nosL : nosR; smoke.emit(pp.x + fwd.x * 0.6, pp.y - 0.05, pp.z + fwd.z * 0.6, -fwd.x * 0.6, 0.05, -fwd.z * 0.6, 0.7, 0.16, 0); }
      if (p.ring !== last.ring) { // anillo de humo: partículas en círculo que avanzan y se abren
        for (let k = 0; k < 18; k++) {
          const a = (k / 18) * Math.PI * 2, ca = Math.cos(a) * 0.07, sa = Math.sin(a) * 0.07;
          const ox = upW.x * ca + sideW.x * sa, oy = upW.y * ca + sideW.y * sa, oz = upW.z * ca + sideW.z * sa;
          smoke.emit(lipsP.x + ox, lipsP.y + oy, lipsP.z + oz, fwd.x * 0.42 + ox * 1.6, fwd.y * 0.42 + oy * 1.6 + 0.12, fwd.z * 0.42 + oz * 1.6, 2.8, 0.09, 0);
        }
      }
      last = { puff: p.puff, soot: p.soot, sparks: p.sparks, sniff: p.sniff, ring: p.ring };
      if (p.state === 'interrupted' && !wasInterrupted) { smoke.choke(5); embers.choke(6); }
      wasInterrupted = p.state === 'interrupted';

      smokeAcc += p.smoke * dt * 5;
      while (smokeAcc > 1) {
        smokeAcc -= 1; side++;
        const thinking = p.state === 'thinking', pp = thinking ? nosR : side % 2 ? nosL : nosR, sp = thinking ? 0.08 : 0.25;
        smoke.emit(pp.x, pp.y, pp.z, fwd.x * sp + (r() - 0.5) * 0.05, 0.12 + r() * 0.08, fwd.z * sp, thinking ? 3.4 : 2.2, thinking ? 0.15 : 0.18, 0);
      }
      emberAcc += p.embers * dt * 6;
      while (emberAcc > 1) {
        emberAcc -= 1;
        if (p.state === 'speaking' || p.state === 'idle') {
          const src = p.state === 'speaking' && p.jaw > 0.15 ? mouthP : r() < 0.5 ? nosL : nosR;
          embers.emit(src.x + (r() - 0.5) * 0.12, src.y, src.z, fwd.x * 0.3 + (r() - 0.5) * 0.3, 0.3 + r() * 0.5, fwd.z * 0.3, 1.1 + r(), 0.035 + r() * 0.03, 0);
        } else {
          const a = r() * 6.28, rr = 0.9 + r() * 0.6;
          embers.emit(Math.cos(a) * rr, -2.2 + r() * 0.4, Math.sin(a) * rr * 0.6 + 0.2, -Math.sin(a) * 0.35, 0.45 + r() * 0.5, Math.cos(a) * 0.2, 2 + r() * 1.5, 0.035 + r() * 0.03, p.state === 'success' ? 1 : 0);
        }
      }
      const turb = p.reduced ? 0.1 : 0.45;
      smoke.update(dt, t, 0.3, 0.55, turb * (p.state === 'thinking' ? 1.6 : 1));
      embers.update(dt, t, 0.18, 0.7, turb * 1.4);
      gl.render(scene, cam);
    },
    dispose(): void {
      const mats = new Set<THREE.Material>(), gs = new Set<THREE.BufferGeometry>();
      scene.traverse((o) => { const m = o as THREE.Mesh; if (m.geometry) gs.add(m.geometry); if (m.material) (Array.isArray(m.material) ? m.material : [m.material]).forEach((x) => mats.add(x)); });
      gs.forEach((g) => g.dispose()); mats.forEach((m) => m.dispose());
    },
  };
}
export type AvatarScene = ReturnType<typeof buildScene>;
