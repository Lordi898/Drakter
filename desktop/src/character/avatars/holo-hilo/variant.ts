// Holo-Hilo: el rig de Holo-Contorno (escultura, cara, pelo, barba, cerebro) con una trama de filamentos
// encima. Las curvas de nivel quedan como eco tenue y cada estado mueve la trama a su manera.
import type { HoloVariant } from '../holo-contorno/layer';
import { threadSet, threadUniforms } from './threads';

const ease = (v: number, target: number, rate: number, dt: number): number => v + (target - v) * (1 - Math.exp(-dt * rate));

export const holoHilo: HoloVariant = {
  lineK: 0.16,
  vol: [0.03, 0.07],
  extend({ U, head, body, brain }) {
    const TU = threadUniforms();
    const thH = threadSet(U, TU, true, 2700, 220), thB = threadSet(U, TU, false, 1100); // cabeza (con el rig de la piel) y busto
    const th = { cond: 0, think: 0, sag: 0, shut: 0, loose: 1, spin: 0, flashY: 0, flashK: 0, lastT: 0, prev: '' };
    return {
      blended: [thH.mat, thB.mat],
      steps: [
        () => { const done = thH.step(9); if (done) head.add(thH.mesh); return done; },
        () => { const done = thB.step(9); if (done) body.add(thB.mesh); return done; },
      ],
      update(p) {
        const dt = Math.min(0.05, Math.max(0, p.t - th.lastT)); th.lastT = p.t; const s = p.state, R = brain.reduced;
        if (s !== th.prev) { if (s === 'success') { th.flashY = -2.6; th.flashK = R ? 0.3 : 1; } th.prev = s; }
        th.cond = ease(th.cond, s === 'offline' ? 0.1 : 1, s === 'offline' ? 0.8 : 1.5, dt);           // deshilachado / se teje
        th.think = ease(th.think, s === 'thinking' && p.st > 0.3 ? 1 : 0, 2.4, dt);                   // ovillo
        th.sag = ease(th.sag, s === 'error' ? (R ? 0.3 : 1) : 0, 3, dt);                               // perder el hilo
        th.shut = ease(th.shut, s === 'executing' ? 1 : 0, 3, dt);                                    // lanzadera
        th.loose = ease(th.loose, (s === 'speaking' ? 0.5 : s === 'executing' ? 0.3 : s === 'interrupted' ? 0.08 : s === 'error' ? 1.8 : s === 'listening' ? 0.4 : 1) * (R ? 0.3 : 1), 3, dt);
        th.spin += dt * (s === 'thinking' ? 1.7 : 0.3) * (R ? 0.3 : 1); th.flashY += dt * 4.2; th.flashK = Math.max(0, th.flashK - dt * 0.75);
        const ph = p.t * 0.9, pass = Math.floor(ph), u = ph - pass, e = u * u * (3 - 2 * u);
        TU.uCond.value = th.cond; TU.uThink.value = th.think; TU.uSag.value = th.sag; TU.uShutK.value = th.shut; TU.uLoose.value = th.loose; TU.uSpin.value = th.spin; TU.uLevel.value = p.level;
        TU.uFlash.value.set(th.flashY, th.flashK); TU.uShut.value.set((pass % 2 ? 1 - e * 2 : e * 2 - 1) * 1.25, -2.12 - ((pass % 5) + e) * 0.11);
        U.uGlow.value *= 0.42 + 0.58 * Math.min(1, th.cond); // el holograma nace (y se apaga) con la trama
      },
      dispose() { thH.mesh.geometry.dispose(); thB.mesh.geometry.dispose(); thH.mat.dispose(); thB.mat.dispose(); },
    };
  },
};
