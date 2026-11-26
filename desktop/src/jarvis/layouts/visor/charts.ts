/**
 * Gráficos 2D del Visor (canvas), funciones puras sobre datos ya derivados de las instantáneas.
 * Brillo falso: trazo ancho tenue + trazo fino brillante con composición 'lighter' (sin postprocesado).
 * `boot` (0-1) anima la entrada; con 1, el dibujo es estático (no hay nada que cambie por fotograma).
 * Adaptado de `research/jarvis-hud/visor/src/charts.ts` (allí con datos de ejemplo; aquí, reales).
 */
export const ICE = '139,233,255', CORE = '233,252,255', BLUE = '47,140,255', AMBER = '255,181,71', RED = '255,75,92'
const TAU = Math.PI * 2
const FONT = '"Recursive Variable", ui-sans-serif, system-ui, sans-serif'
const mono = (px: number, w = 300): string => `${w} ${px}px ${FONT}`
const sans = (px: number, w = 400): string => `${w} ${px}px ${FONT}`
const easeOut = (t: number): number => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3)

function glow(x: CanvasRenderingContext2D, rgb: string, a: number, wd: number): void {
  x.strokeStyle = `rgba(${rgb},${a * 0.18})`; x.lineWidth = wd * 4; x.stroke()
  x.strokeStyle = `rgba(${rgb},${a})`; x.lineWidth = wd; x.stroke()
}
/** Texto acotado al ancho (con «…»). */
function fit(x: CanvasRenderingContext2D, s: string, max: number): string {
  if (x.measureText(s).width <= max) return s
  let t = s
  while (t.length > 1 && x.measureText(`${t}…`).width > max) t = t.slice(0, -1)
  return `${t}…`
}
export const hhmm = (h: number): string => `${Math.floor(h)}:${String(Math.floor((h % 1) * 60)).padStart(2, '0')}`

// ── Hoy: esfera de 24 h. Eventos como arcos, tareas con hora como puntos, el ahora como barrido.
export interface DialData {
  readonly events: readonly { readonly start: number; readonly end: number; readonly accent: boolean }[]
  readonly tasks: readonly { readonly hour: number; readonly urgent: boolean }[]
  /** Fracción del día con algo en la agenda (anillo interior). */
  readonly load: number
  readonly caption: string
  readonly next: string
}
export function drawDial(x: CanvasRenderingContext2D, w: number, h: number, d: DialData, now: number, boot: number): void {
  const cx = w / 2, cy = h / 2, R = Math.min(w, h) * 0.44, b = easeOut(boot)
  const ang = (hr: number): number => (hr / 24) * TAU - Math.PI / 2
  x.clearRect(0, 0, w, h); x.globalCompositeOperation = 'lighter'
  for (let i = 0; i < 96 && i / 96 <= b; i++) {
    const a = (i / 96) * TAU - Math.PI / 2, major = i % 4 === 0, r0 = R * (major ? 0.9 : 0.94)
    x.beginPath(); x.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0); x.lineTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R)
    x.strokeStyle = `rgba(${ICE},${major ? 0.7 : 0.25})`; x.lineWidth = major ? 1.5 : 1; x.stroke()
  }
  x.font = mono(10); x.fillStyle = `rgba(${ICE},0.65)`; x.textAlign = 'center'; x.textBaseline = 'middle'
  for (let hr = 0; hr < 24; hr += 3) { const a = ang(hr); x.fillText(String(hr).padStart(2, '0'), cx + Math.cos(a) * R * 1.07, cy + Math.sin(a) * R * 1.07) }
  d.events.forEach((e, i) => {
    const a0 = ang(e.start), a1 = ang(e.start + (e.end - e.start) * easeOut(boot * 1.6 - i * 0.08))
    if (a1 <= a0) return
    const rr = R * (e.accent ? 0.74 : 0.8), past = e.end < now, act = e.start <= now && now < e.end
    x.beginPath(); x.arc(cx, cy, rr, a0, a1); glow(x, e.accent ? BLUE : ICE, past ? 0.35 : act ? 1 : 0.8, e.accent ? 7 : 4)
  })
  for (const t of d.tasks) {
    const a = ang(t.hour), r = R * 0.62
    x.beginPath(); x.arc(cx + Math.cos(a) * r, cy + Math.sin(a) * r, t.urgent ? 2.8 : 2, 0, TAU); x.fillStyle = t.urgent ? `rgba(${AMBER},0.95)` : `rgba(${CORE},0.8)`; x.fill()
  }
  const an = ang(now)
  const grd = x.createConicGradient(an - 0.6, cx, cy)
  grd.addColorStop(0, 'rgba(0,0,0,0)'); grd.addColorStop(0.6 / TAU, `rgba(${ICE},0.16)`); grd.addColorStop(0.6 / TAU + 0.001, 'rgba(0,0,0,0)')
  x.beginPath(); x.moveTo(cx, cy); x.arc(cx, cy, R * 0.98, an - 0.6, an); x.closePath(); x.fillStyle = grd; x.fill()
  x.beginPath(); x.moveTo(cx + Math.cos(an) * R * 0.3, cy + Math.sin(an) * R * 0.3); x.lineTo(cx + Math.cos(an) * R * 1.02, cy + Math.sin(an) * R * 1.02); glow(x, CORE, 0.95, 1.5)
  x.beginPath(); x.arc(cx + Math.cos(an) * R * 1.02, cy + Math.sin(an) * R * 1.02, 4, 0, TAU); x.fillStyle = `rgba(${CORE},1)`; x.fill()
  x.beginPath(); x.arc(cx, cy, R * 0.44, -Math.PI / 2, -Math.PI / 2 + TAU * Math.min(1, d.load) * b); glow(x, ICE, 0.9, 3)
  x.globalCompositeOperation = 'source-over'
  x.fillStyle = `rgba(${CORE},0.95)`; x.font = sans(52, 300); x.textAlign = 'center'; x.fillText(hhmm(now), cx, cy - 8)
  x.font = mono(10); x.fillStyle = `rgba(${ICE},0.7)`; x.fillText(d.caption, cx, cy + 30)
  x.fillStyle = `rgba(${ICE},0.55)`; x.fillText(fit(x, d.next, R * 1.3), cx, cy + 48)
}

// ── Hábitos: anillos de la semana (uno por hábito) + mapa de 28 días (filas = hábitos)
export interface HabitsChartData {
  readonly rows: readonly {
    readonly name: string
    /** Fracción hecha de lo programado esta semana (0-1). */
    readonly week: number
    /** 28 días, del más antiguo a hoy: 1 hecho, 0.35 saltado, 0.08 fallado o pendiente, null no tocaba. */
    readonly days: readonly (number | null)[]
  }[]
}
export function drawHabits(x: CanvasRenderingContext2D, w: number, h: number, d: HabitsChartData, boot: number): void {
  const b = easeOut(boot)
  x.clearRect(0, 0, w, h); x.globalCompositeOperation = 'lighter'
  const cx = h * 0.5, cy = h * 0.5, R = h * 0.44
  const rings = d.rows.slice(0, 5)
  rings.forEach((r, i) => {
    const rr = R - i * 26
    x.beginPath(); x.arc(cx, cy, rr, 0, TAU); x.strokeStyle = `rgba(${ICE},0.08)`; x.lineWidth = 14; x.stroke()
    x.beginPath(); x.arc(cx, cy, rr, -Math.PI / 2, -Math.PI / 2 + r.week * b * TAU); glow(x, i === 0 ? CORE : ICE, 0.95, 10)
  })
  x.globalCompositeOperation = 'source-over'
  const ox = h + 30, cols = 28, cw = (w - ox - 10) / cols, rowsN = Math.max(1, Math.min(8, d.rows.length)), ch = Math.min(cw * 1.6, (h - 60) / rowsN)
  x.font = mono(9); x.fillStyle = `rgba(${ICE},0.6)`; x.textAlign = 'left'; x.textBaseline = 'middle'
  x.fillText('28 días', ox, 14); x.textAlign = 'right'; x.fillText('hoy', w - 10, 14)
  x.globalCompositeOperation = 'lighter'
  d.rows.slice(0, 8).forEach((r, ri) => {
    r.days.forEach((v, di) => {
      const appear = easeOut(b * 2.2 - di / cols)
      if (v === null || appear <= 0) return
      const px = ox + di * cw, py = 30 + ri * ch
      x.fillStyle = `rgba(${v > 0.9 ? CORE : ICE},${(0.06 + v * 0.75) * appear})`; x.fillRect(px + 1.5, py + 1.5, cw - 3, ch - 3)
    })
  })
  x.globalCompositeOperation = 'source-over'
}

// ── Calendario: siete días en columnas con bloques por tipo y línea del ahora (ligera curvatura)
export interface WeekData {
  readonly days: readonly string[]
  /** `day` 0-6 desde hoy; horas locales decimales. */
  readonly blocks: readonly { readonly day: number; readonly start: number; readonly end: number; readonly title: string; readonly tone: 'class' | 'event' | 'block' | 'exam'; readonly lane: number; readonly lanes: number }[]
  readonly from: number
  readonly to: number
}
const TONE: Record<WeekData['blocks'][number]['tone'], string> = { class: ICE, event: CORE, block: BLUE, exam: AMBER }
export function drawWeek(x: CanvasRenderingContext2D, w: number, h: number, d: WeekData, now: number, boot: number): void {
  const b = easeOut(boot), top = 34, bottom = h - 14, ox = 44, dayW = (w - 50) / 7
  const Y = (hr: number): number => top + ((Math.min(d.to, Math.max(d.from, hr)) - d.from) / (d.to - d.from)) * (bottom - top)
  const bow = (i: number): number => Math.pow((i - 3) / 3.5, 2) * 10
  x.clearRect(0, 0, w, h); x.font = mono(9); x.textBaseline = 'middle'
  for (let hr = Math.ceil(d.from / 2) * 2; hr <= d.to; hr += 2) {
    x.fillStyle = `rgba(${ICE},0.45)`; x.textAlign = 'right'; x.fillText(`${hr}`, ox - 8, Y(hr))
    x.strokeStyle = `rgba(${ICE},0.07)`; x.lineWidth = 1; x.beginPath(); x.moveTo(ox, Y(hr)); x.lineTo(w - 6, Y(hr)); x.stroke()
  }
  d.days.forEach((n, i) => {
    x.textAlign = 'center'; x.fillStyle = i === 0 ? `rgba(${CORE},1)` : `rgba(${ICE},0.6)`; x.font = i === 0 ? sans(12, 560) : sans(11)
    x.fillText(n, ox + dayW * (i + 0.5), 14 + bow(i))
    if (i === 0) { x.fillStyle = `rgba(${ICE},0.05)`; x.fillRect(ox, top - 6, dayW, bottom - top + 12) }
  })
  x.globalCompositeOperation = 'lighter'
  d.blocks.forEach((e, i) => {
    const ap = easeOut(b * 2 - i * 0.03)
    if (ap <= 0) return
    const lw = (dayW - 8) / Math.max(1, e.lanes), px = ox + dayW * e.day + 4 + lw * e.lane, py = Y(e.start) + bow(e.day), ph = Math.max(3, (Y(e.end) - Y(e.start)) * ap), pw = lw - (e.lanes > 1 ? 2 : 0), col = TONE[e.tone]
    x.fillStyle = `rgba(${col},${e.tone === 'exam' ? 0.32 : 0.14})`; x.fillRect(px, py, pw, ph); x.fillStyle = `rgba(${col},0.95)`; x.fillRect(px, py, 2, ph)
    if (ph > 16) {
      x.globalCompositeOperation = 'source-over'; x.fillStyle = `rgba(${CORE},${0.9 * ap})`; x.font = sans(10.5, 500); x.textAlign = 'left'
      x.fillText(fit(x, e.title, pw - 10), px + 7, py + 9); x.globalCompositeOperation = 'lighter'
    }
  })
  if (now > d.from && now < d.to) {
    const py = Y(now) + bow(0)
    x.beginPath(); x.moveTo(ox - 6, py); x.lineTo(ox + dayW + 6, py); glow(x, CORE, 1, 1.5)
    x.beginPath(); x.arc(ox - 6, py, 3.5, 0, TAU); x.fillStyle = `rgba(${CORE},1)`; x.fill()
  }
  x.globalCompositeOperation = 'source-over'
}

// ── Proyectos: anillo de progreso, nombre, recuento y carga de las 8 próximas semanas
export interface ProjectsChartData {
  readonly rows: readonly { readonly name: string; readonly percent: number; readonly open: number; readonly done: number; readonly weeks: readonly number[]; readonly color: string }[]
}
export function drawProjects(x: CanvasRenderingContext2D, w: number, h: number, d: ProjectsChartData, boot: number): void {
  const b = easeOut(boot), rowH = Math.min(76, h / Math.max(1, d.rows.length))
  x.clearRect(0, 0, w, h)
  d.rows.forEach((p, i) => {
    const cy = rowH * (i + 0.5), cx = 22, r = 13, f = (p.percent / 100) * easeOut(b * 1.5 - i * 0.1)
    x.globalCompositeOperation = 'lighter'
    x.beginPath(); x.arc(cx, cy, r, 0, TAU); x.strokeStyle = `rgba(${ICE},0.12)`; x.lineWidth = 3; x.stroke()
    x.beginPath(); x.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + f * TAU); glow(x, ICE, 0.95, 2.5)
    x.globalCompositeOperation = 'source-over'; x.textBaseline = 'middle'; x.textAlign = 'left'
    x.fillStyle = p.color; x.fillRect(46, cy - 12, 3, 10)
    x.fillStyle = `rgba(${CORE},0.95)`; x.font = sans(13, 500); x.fillText(fit(x, p.name, w - 190), 54, cy - 7)
    x.fillStyle = `rgba(${ICE},0.6)`; x.font = mono(9); x.fillText(`${p.open} abiertas  ${p.done} hechas`, 46, cy + 9)
    x.textAlign = 'right'; x.fillStyle = `rgba(${CORE},0.9)`; x.font = sans(18, 300); x.fillText(`${Math.round(f * 100)} %`, w - 70, cy)
    const max = Math.max(1, ...p.weeks)
    x.beginPath(); p.weeks.forEach((v, k) => { const px = w - 62 + k * 8, py = cy + 8 - (v / max) * 16; k ? x.lineTo(px, py) : x.moveTo(px, py) })
    x.globalCompositeOperation = 'lighter'; glow(x, ICE, 0.8, 1.2)
  })
  x.globalCompositeOperation = 'source-over'
}

// ── Almacén: barras por tipo de recurso
export interface StorageChartData { readonly rows: readonly { readonly label: string; readonly count: number; readonly tone: 'ice' | 'blue' | 'amber' }[] }
export function drawStorage(x: CanvasRenderingContext2D, w: number, h: number, d: StorageChartData, boot: number): void {
  const b = easeOut(boot), rowH = Math.min(34, h / Math.max(1, d.rows.length)), max = Math.max(1, ...d.rows.map((r) => r.count))
  x.clearRect(0, 0, w, h)
  d.rows.forEach((s, i) => {
    const cy = rowH * (i + 0.5), bw = (w - 130) * (s.count / max) * easeOut(b * 1.6 - i * 0.1), col = s.tone === 'amber' ? AMBER : s.tone === 'blue' ? BLUE : ICE
    x.textBaseline = 'middle'; x.textAlign = 'left'; x.fillStyle = `rgba(${CORE},0.9)`; x.font = sans(12, 500); x.fillText(fit(x, s.label, 76), 0, cy)
    x.fillStyle = `rgba(${ICE},0.08)`; x.fillRect(84, cy - 4, w - 130, 8)
    x.globalCompositeOperation = 'lighter'
    for (let k = 0; k < bw; k += 5) { x.fillStyle = `rgba(${col},${0.45 + 0.4 * ((k / 5) % 2)})`; x.fillRect(84 + k, cy - 4, 3, 8) }
    x.globalCompositeOperation = 'source-over'; x.textAlign = 'right'; x.fillStyle = `rgba(${ICE},0.7)`; x.font = mono(9); x.fillText(String(s.count), w, cy)
  })
}
