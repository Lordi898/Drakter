/**
 * Materiales holográficos de la Holomesa (port del prototipo de drakter-98). Todo es luz aditiva sin
 * escritura de profundidad: el orden no importa y el brillo sale del propio shader (aristas, fresnel y
 * halos), sin postprocesado. Los uniformes globales (`tiempo`, `aviso`…) son de cada instancia de la
 * escena, no del módulo: montar y desmontar la interfaz no arrastra estado.
 */
import * as THREE from 'three'

export interface SharedUniforms {
  readonly uTime: { value: number }
  /** 0..1: tiñe la escena de rojo-ámbar (estado de error). */
  readonly uWarn: { value: number }
  /** 0..1: apaga la escena (sin conexión). */
  readonly uOffline: { value: number }
  /** 0..1: hay una sección abierta y la mesa cede protagonismo. */
  readonly uFocusG: { value: number }
}

export function createSharedUniforms(): SharedUniforms {
  return { uTime: { value: 0 }, uWarn: { value: 0 }, uOffline: { value: 0 }, uFocusG: { value: 0 } }
}

const NOISE = /* glsl */ `
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
`

const TINT = /* glsl */ `
uniform float uWarn; uniform float uOffline;
vec3 tint(vec3 c){ vec3 w = vec3(1.0, 0.3, 0.37) * dot(c, vec3(0.45, 0.45, 0.35)); c = mix(c, w, uWarn * 0.6); return c * (1.0 - uOffline * 0.82); }
`

export interface HoloOpts {
  readonly color?: number
  readonly fill?: number
  readonly edge?: number
  readonly base?: number
  readonly height?: number
  readonly fresnel?: number
  readonly scan?: number
}

const ADDITIVE = { transparent: true, depthWrite: false, blending: THREE.AdditiveBlending } as const

export type Materials = ReturnType<typeof createMaterials>

/** Fábrica de materiales ligados a unos uniformes compartidos. */
export function createMaterials(U: SharedUniforms) {
  /** Volumen holográfico. Por estación: uBuild (se imprime de abajo arriba), uDim, uHover, uPick (instancia resaltada). */
  function holoMat(o: HoloOpts = {}): THREE.ShaderMaterial {
    return new THREE.ShaderMaterial({
      uniforms: {
        ...U,
        uColor: { value: new THREE.Color(o.color ?? 0x6fd6ff) },
        uFill: { value: o.fill ?? 0.18 },
        uEdge: { value: o.edge ?? 1.0 },
        uFres: { value: o.fresnel ?? 0.7 },
        uScan: { value: o.scan ?? 1 },
        uBase: { value: o.base ?? 0 },
        uHeight: { value: o.height ?? 3 },
        uBuild: { value: 1 },
        uDim: { value: 0 },
        uHover: { value: 0 },
        uPick: { value: -1 },
        uGain: { value: 1 }
      },
      vertexShader: /* glsl */ `
        uniform float uPick;
        varying vec3 vWorld; varying vec3 vN; varying vec2 vUv; varying vec3 vCol; varying float vPick;
        uniform vec3 uColor;
        void main(){
          vec4 p = vec4(position, 1.0); vec3 n = normal;
          #ifdef USE_INSTANCING
            p = instanceMatrix * p; n = mat3(instanceMatrix) * n;
            vPick = float(gl_InstanceID) == uPick ? 1.0 : 0.0;
          #else
            vPick = 0.0;
          #endif
          vCol = uColor;
          #ifdef USE_INSTANCING_COLOR
            vCol = instanceColor;
          #endif
          vec4 w = modelMatrix * p; vWorld = w.xyz; vN = normalize(mat3(modelMatrix) * n); vUv = uv;
          gl_Position = projectionMatrix * viewMatrix * w;
        }`,
      fragmentShader: /* glsl */ `
        uniform float uTime, uFill, uEdge, uFres, uScan, uBase, uHeight, uBuild, uDim, uHover, uGain;
        varying vec3 vWorld; varying vec3 vN; varying vec2 vUv; varying vec3 vCol; varying float vPick;
        ${NOISE}${TINT}
        void main(){
          float h = (vWorld.y - uBase) / uHeight;
          if (h > uBuild * 1.08 - 0.04) discard;
          float front = smoothstep(uBuild * 1.08 - 0.12, uBuild * 1.08 - 0.04, h) * step(uBuild, 0.999);
          float e = min(min(vUv.x, 1.0 - vUv.x), min(vUv.y, 1.0 - vUv.y));
          float fw = fwidth(e) * 1.6;
          float line = 1.0 - smoothstep(fw * 0.4, fw * 1.6, e);
          float halo = exp(-e * 22.0) * 0.35;
          vec3 V = normalize(cameraPosition - vWorld);
          float fr = pow(1.0 - abs(dot(V, normalize(vN))), 2.2);
          float band = pow(0.5 + 0.5 * sin(vWorld.y * 26.0 - uTime * 3.0), 18.0) * uScan;
          float flick = 0.94 + 0.06 * hash(vec2(floor(uTime * 24.0), vWorld.y));
          float pick = max(vPick, 0.0);
          vec3 c = vCol * (uFill + pow(fr, 1.4) * uFres + band * 0.18 + halo * uEdge * 0.8) + mix(vCol, vec3(1.0), 0.4) * line * uEdge * 1.05;
          c += vec3(0.85, 0.97, 1.0) * front * 1.6;
          c *= flick * (1.0 + uHover * 0.45 + pick * 1.6) * (1.0 - uDim * 0.93) * uGain;
          c = min(c, vec3(0.62, 0.9, 1.0) * (1.0 + pick));
          gl_FragColor = vec4(tint(c), 1.0);
        }`,
      ...ADDITIVE,
      side: THREE.DoubleSide
    })
  }

  /** Líneas aditivas. Con `aT` (0..1 a lo largo de la arista) dibuja pulsos que viajan. */
  function lineMat(color = 0x6fd6ff, opacity = 0.6, pulses = false): THREE.ShaderMaterial {
    return new THREE.ShaderMaterial({
      uniforms: {
        ...U,
        uColor: { value: new THREE.Color(color) },
        uOpacity: { value: opacity },
        uDim: { value: 0 },
        uBuild: { value: 1 },
        uBase: { value: 0 },
        uHeight: { value: 4 },
        uHover: { value: 0 }
      },
      vertexShader: /* glsl */ `
        attribute float aT; attribute float aSeed; varying float vT; varying float vSeed; varying vec3 vWorld;
        void main(){ vT = aT; vSeed = aSeed; vec4 w = modelMatrix * vec4(position, 1.0); vWorld = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
      fragmentShader: /* glsl */ `
        uniform vec3 uColor; uniform float uOpacity, uDim, uBuild, uBase, uHeight, uTime, uHover; varying float vT; varying float vSeed; varying vec3 vWorld;
        ${TINT}
        void main(){
          float h = (vWorld.y - uBase) / uHeight; if (h > uBuild * 1.08 - 0.04) discard;
          float a = uOpacity;
          ${pulses ? 'float p = fract(vT - uTime * (0.25 + vSeed * 0.35) + vSeed * 7.0); a += smoothstep(0.86, 1.0, p) * 2.2;' : ''}
          vec3 c = uColor * a * (1.0 - uDim * 0.8) * (1.0 + uHover * 0.6);
          gl_FragColor = vec4(tint(c), 1.0);
        }`,
      ...ADDITIVE
    })
  }

  /** Puntos con halo suave (partículas, nodos). `aSize` por punto, `aSeed` para parpadeo, `aCol` opcional. */
  function pointMat(color = 0x9fe6ff, size = 6, rise = 0): THREE.ShaderMaterial {
    return new THREE.ShaderMaterial({
      uniforms: {
        ...U,
        uColor: { value: new THREE.Color(color) },
        uSize: { value: size },
        uRise: { value: rise },
        uDim: { value: 0 },
        uPx: { value: 1 },
        uBuild: { value: 1 },
        uAlpha: { value: 1 },
        uPick: { value: -1 }
      },
      vertexShader: /* glsl */ `
        attribute float aSize; attribute float aSeed; attribute vec3 aCol; uniform vec3 uColor; uniform float uTime, uSize, uRise, uPx, uPick; varying float vA; varying float vPick; varying vec3 vCol;
        void main(){
          vec3 p = position;
          if (uRise > 0.0) { float t = fract(aSeed * 13.7 + uTime * uRise * (0.4 + aSeed)); p.y += t * 9.0; p.x += sin(uTime * 0.3 + aSeed * 40.0) * 0.4; vA = smoothstep(0.0, 0.15, t) * (1.0 - t); }
          else vA = 0.75 + 0.25 * sin(uTime * (1.0 + aSeed * 3.0) + aSeed * 30.0);
          vPick = float(gl_VertexID) == uPick ? 1.0 : 0.0; vCol = dot(aCol, aCol) > 0.0 ? aCol : uColor;
          vec4 mv = modelViewMatrix * vec4(p, 1.0);
          gl_PointSize = uSize * aSize * uPx * (1.0 + vPick * 0.8) * (10.0 / -mv.z);
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: /* glsl */ `
        uniform float uDim, uAlpha; varying float vA; varying float vPick; varying vec3 vCol;
        ${TINT}
        void main(){ vec2 d = gl_PointCoord - 0.5; float r = length(d) * 2.0; if (r > 1.0) discard;
          float core = exp(-r * r * 9.0) * 1.4 + exp(-r * 3.2) * 0.45;
          vec3 c = mix(vCol, vec3(1.0), core * 0.35 + vPick * 0.5) * core * vA * uAlpha * (1.0 - uDim * 0.8) * (1.0 + vPick * 1.5);
          gl_FragColor = vec4(tint(c), 1.0); }`,
      ...ADDITIVE
    })
  }

  /** Cono de proyección de cada emisor de la mesa hacia su holograma. */
  function beamMat(color = 0x4fc8ff): THREE.ShaderMaterial {
    return new THREE.ShaderMaterial({
      uniforms: { ...U, uColor: { value: new THREE.Color(color) }, uDim: { value: 0 }, uHover: { value: 0 }, uBuild: { value: 1 }, uGain: { value: 1 } },
      vertexShader: /* glsl */ `varying vec2 vUv; varying vec3 vN; varying vec3 vWorld;
        void main(){ vUv = uv; vec4 w = modelMatrix * vec4(position, 1.0); vWorld = w.xyz; vN = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * w; }`,
      fragmentShader: /* glsl */ `uniform vec3 uColor; uniform float uTime, uDim, uHover, uBuild, uGain; varying vec2 vUv; varying vec3 vN; varying vec3 vWorld;
        ${TINT}
        void main(){ vec3 V = normalize(cameraPosition - vWorld); float side = pow(abs(dot(V, normalize(vN))), 1.6);
          float up = 1.0 - vUv.y; float a = up * up * side * 0.32 * uBuild;
          a *= 0.8 + 0.2 * sin(vUv.x * 60.0 + uTime * 2.0) * sin(vUv.y * 9.0 - uTime * 4.0);
          vec3 c = uColor * a * (1.0 + uHover * 0.9) * (1.0 - uDim * 0.7) * uGain; gl_FragColor = vec4(tint(c), 1.0); }`,
      ...ADDITIVE,
      side: THREE.DoubleSide
    })
  }

  /** Plano con halo (núcleos de luz y emisores). */
  function glowMat(color = 0x7fdcff, strength = 1): THREE.ShaderMaterial {
    return new THREE.ShaderMaterial({
      uniforms: { ...U, uColor: { value: new THREE.Color(color) }, uStrength: { value: strength }, uDim: { value: 0 } },
      vertexShader: /* glsl */ `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
      fragmentShader: /* glsl */ `uniform vec3 uColor; uniform float uStrength, uDim; varying vec2 vUv; ${TINT}
        void main(){ float r = length(vUv - 0.5) * 2.0; float g = exp(-r * r * 5.0) * 0.8 + exp(-r * 10.0) * 0.6; g *= smoothstep(1.0, 0.7, r);
          gl_FragColor = vec4(tint(mix(uColor, vec3(1.0), exp(-r * 14.0)) * g * uStrength * (1.0 - uDim * 0.7)), 1.0); }`,
      ...ADDITIVE
    })
  }

  return { U, holoMat, lineMat, pointMat, beamMat, glowMat }
}

/** Libera geometrías y materiales de un subárbol (nunca texturas compartidas ni el renderer). */
export function disposeTree(o: THREE.Object3D): void {
  o.traverse((c) => {
    const m = c as THREE.Mesh
    m.geometry?.dispose()
    const mat = m.material as THREE.Material | THREE.Material[] | undefined
    if (Array.isArray(mat)) for (const x of mat) x.dispose()
    else mat?.dispose()
  })
}
