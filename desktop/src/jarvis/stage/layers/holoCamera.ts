/** Cámara compartida por las capas de prueba: misma fórmula de parallax, misma vista. */
import * as THREE from 'three'
import type { StageFrame } from '../types'

export interface HoloCamera {
  readonly camera: THREE.PerspectiveCamera
  update(frame: StageFrame): void
}

export function createHoloCamera(): HoloCamera {
  const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 120)
  const target = new THREE.Vector3(0, 1.2, -10)
  let ox = 0, oy = 0
  return {
    camera,
    update(frame) {
      const aspect = frame.width / Math.max(1, frame.height)
      if (camera.aspect !== aspect) {
        camera.aspect = aspect
        camera.updateProjectionMatrix()
      }
      // Cine: parallax pleno; Equilibrado: suave; Ahorro o reducir movimiento: quieta.
      const amp = frame.reducedMotion || !frame.quality.parallax ? 0 : frame.quality.tier === 'cine' ? 0.6 : 0.3
      const tx = frame.pointer.active ? frame.pointer.x * amp : 0
      const ty = frame.pointer.active ? frame.pointer.y * amp * 0.5 : 0
      const k = 1 - Math.exp(-frame.dt * 3)
      ox += (tx - ox) * k
      oy += (ty - oy) * k
      camera.position.set(ox, 1.8 + oy, 4)
      camera.lookAt(target)
    }
  }
}
