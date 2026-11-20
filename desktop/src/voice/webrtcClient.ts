/**
 * Cliente WebRTC de la voz v2 (V-01, V-02, V-33). Captura con getUserMedia (AEC3, NS,
 * AGC) y habla con `voice/` por loopback, sin STUN ni TURN. La señalización va por
 * `window.api.voice.offer`; el renderer no tiene red propia.
 */
import { getPreferences, subscribePreferences } from '@/stores/preferences'
import { registerVoiceClient, type VoiceClient } from './contract'

const AUDIO_CONSTRAINTS: MediaTrackConstraints = {
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
  channelCount: 1
}
/** Pipecat da la conexión por muerta si no recibe un mensaje `ping…` en 3 s. */
const PING_MS = 2000
const GATHER_TIMEOUT_MS = 3000
const RETRY_MIN_MS = 1000
const RETRY_MAX_MS = 15_000

type Listener = () => void

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** `connected` de un evento `voice.state`, o `null` si el evento es otro. */
function voiceConnectedFrom(event: unknown): boolean | null {
  if (!isRecord(event) || event['type'] !== 'voice.state' || !isRecord(event['payload'])) return null
  const connected = event['payload']['connected']
  return typeof connected === 'boolean' ? connected : null
}

/** Sin trickle: la oferta sale con todos los candidatos (127.0.0.1 incluido). */
function waitForGathering(pc: RTCPeerConnection): Promise<void> {
  return new Promise((resolve) => {
    if (pc.iceGatheringState === 'complete') return resolve()
    const timer = setTimeout(done, GATHER_TIMEOUT_MS)
    function done(): void {
      clearTimeout(timer)
      pc.removeEventListener('icegatheringstatechange', check)
      resolve()
    }
    function check(): void {
      if (pc.iceGatheringState === 'complete') done()
    }
    pc.addEventListener('icegatheringstatechange', check)
  })
}

function listen(target: EventTarget, type: string, handler: () => void): () => void {
  target.addEventListener(type, handler)
  return () => target.removeEventListener(type, handler)
}

function sameDevice(a: MediaStreamTrack, b: MediaStreamTrack): boolean {
  const sa = a.getSettings()
  const sb = b.getSettings()
  return sa.deviceId === sb.deviceId && sa.groupId === sb.groupId
}

class WebRtcVoiceClient implements VoiceClient {
  private pc: RTCPeerConnection | null = null
  private sender: RTCRtpSender | null = null
  private track: MediaStreamTrack | null = null
  private audio: HTMLAudioElement | null = null
  /** Lo devuelve la voz; en modo SINGLE hay que reofertar con él (`restart_pc`). */
  private pcId: string | null = null
  private running = false
  private linkUp = false
  /** Lo que pidió el usuario: la reconexión respeta un micrófono cerrado. */
  private wantMic = true
  private generation = 0
  private retryTimer: ReturnType<typeof setTimeout> | null = null
  private retryDelay = RETRY_MIN_MS
  private pingTimer: ReturnType<typeof setInterval> | null = null
  private readonly listeners = new Set<Listener>()
  private unsubscribers: Array<() => void> = []
  /** Último estado del micrófono enviado a main (etiqueta de la bandeja). */
  private reportedMic: boolean | null = null

  async start(): Promise<void> {
    if (this.running) return
    this.running = true
    this.unsubscribers = [
      window.api.subscribe('events', (event) => this.onServerEvent(event)),
      window.api.voice.onMicToggle(() => void this.setMicOpen(!this.micOpen())),
      subscribePreferences(() => this.onMicPreference()),
      listen(navigator.mediaDevices, 'devicechange', () => void this.refreshMic())
    ]
    await this.connect()
  }

  stop(): void {
    if (!this.running) return
    this.running = false
    this.generation++
    for (const unsubscribe of this.unsubscribers) unsubscribe()
    this.unsubscribers = []
    this.cancelRetry()
    this.closePeer()
    this.releaseTrack()
    this.audio?.remove()
    this.audio = null
    this.notify()
  }

  micOpen(): boolean {
    return this.track !== null && this.track.readyState === 'live'
  }

  connected(): boolean {
    return this.linkUp
  }

  onChange(cb: Listener): () => void {
    this.listeners.add(cb)
    return () => {
      this.listeners.delete(cb)
    }
  }

  /** Cerrar: `replaceTrack(null)` + `stop()`, sin renegociar. Abrir: pista nueva y `replaceTrack`. */
  async setMicOpen(open: boolean): Promise<void> {
    this.wantMic = open
    if (!open) {
      await this.sender?.replaceTrack(null).catch(() => undefined)
      this.releaseTrack()
      this.notify()
      return
    }
    if (this.micOpen()) return
    const track = await this.captureMic()
    if (track === null) return
    if (!this.wantMic) {
      track.stop()
      return
    }
    this.releaseTrack()
    this.track = track
    await this.sender?.replaceTrack(track).catch(() => undefined)
    this.notify()
  }

  private lastMicDeviceId = getPreferences().micDeviceId

  private onMicPreference(): void {
    const id = getPreferences().micDeviceId
    if (id === this.lastMicDeviceId) return
    this.lastMicDeviceId = id
    void this.refreshMic()
  }

  /**
   * Cambió la lista de dispositivos o la elección: se captura de nuevo (la elegida, o la
   * predeterminada si no hay elegida o desapareció) y, si es otro dispositivo, `replaceTrack`
   * sin renegociar. Si es el mismo, se descarta la pista nueva.
   */
  private async refreshMic(): Promise<void> {
    if (!this.running || !this.wantMic || !this.micOpen()) return
    const generation = ++this.micGeneration
    const track = await this.captureMic()
    if (track === null) return
    const stale = generation !== this.micGeneration || !this.wantMic || !this.running
    const old = this.track
    if (stale || (old !== null && sameDevice(old, track))) {
      track.stop()
      return
    }
    this.track = track
    await this.sender?.replaceTrack(track).catch(() => undefined)
    old?.stop()
    this.notify()
  }

  private micGeneration = 0

  private notify(): void {
    const open = this.micOpen()
    if (open !== this.reportedMic) {
      this.reportedMic = open
      void window.api.voice.reportMicState(open).catch(() => undefined)
    }
    for (const listener of [...this.listeners]) {
      try {
        listener()
      } catch (error) {
        console.warn('Un oyente del cliente de voz ha fallado.', error)
      }
    }
  }

  private async captureMic(): Promise<MediaStreamTrack | null> {
    try {
      const stream = await this.openStream()
      const track = stream.getAudioTracks()[0] ?? null
      track?.addEventListener('ended', () => {
        if (this.track === track) {
          this.track = null
          this.notify()
        }
      })
      return track
    } catch (error) {
      console.warn('No se pudo abrir el micrófono.', error)
      return null
    }
  }

  /** El micrófono elegido; si ya no está (`OverconstrainedError`), el predeterminado. */
  private async openStream(): Promise<MediaStream> {
    const deviceId = getPreferences().micDeviceId
    if (deviceId !== '') {
      try {
        return await navigator.mediaDevices.getUserMedia({
          audio: { ...AUDIO_CONSTRAINTS, deviceId: { exact: deviceId } }
        })
      } catch (error) {
        if (!(error instanceof DOMException) || error.name !== 'OverconstrainedError') throw error
      }
    }
    return navigator.mediaDevices.getUserMedia({ audio: AUDIO_CONSTRAINTS })
  }

  private releaseTrack(): void {
    const track = this.track
    this.track = null
    track?.stop()
  }

  private ensureAudioElement(): HTMLAudioElement {
    if (this.audio === null) {
      const audio = document.createElement('audio')
      audio.autoplay = true
      audio.hidden = true
      document.body.appendChild(audio)
      this.audio = audio
    }
    return this.audio
  }

  private closePeer(): void {
    if (this.pingTimer !== null) clearInterval(this.pingTimer)
    this.pingTimer = null
    const pc = this.pc
    this.pc = null
    this.sender = null
    if (pc !== null) {
      pc.onconnectionstatechange = null
      pc.ontrack = null
      pc.close()
    }
    if (this.linkUp) {
      this.linkUp = false
      this.notify()
    }
  }

  private cancelRetry(): void {
    if (this.retryTimer !== null) clearTimeout(this.retryTimer)
    this.retryTimer = null
  }

  private scheduleReconnect(): void {
    if (!this.running || this.retryTimer !== null) return
    this.closePeer()
    const delay = this.retryDelay
    this.retryDelay = Math.min(this.retryDelay * 2, RETRY_MAX_MS)
    this.retryTimer = setTimeout(() => {
      this.retryTimer = null
      void this.connect()
    }, delay)
  }

  /** La voz se cayó o reinició: nuestra conexión ya no lleva a ningún pipeline. */
  private onServerEvent(event: unknown): void {
    const connected = voiceConnectedFrom(event)
    if (connected === false && this.linkUp) this.scheduleReconnect()
  }

  private async connect(): Promise<void> {
    if (!this.running) return
    const generation = ++this.generation
    this.closePeer()
    try {
      if (this.wantMic && !this.micOpen()) this.track = await this.captureMic()
      if (generation !== this.generation) return

      const pc = new RTCPeerConnection({ iceServers: [] })
      this.pc = pc
      const transceiver = pc.addTransceiver(this.track ?? 'audio', { direction: 'sendrecv' })
      this.sender = transceiver.sender
      const channel = pc.createDataChannel('ping')
      channel.onopen = () => {
        channel.send('ping')
        this.pingTimer = setInterval(() => {
          if (channel.readyState === 'open') channel.send('ping')
        }, PING_MS)
      }
      pc.ontrack = (event) => {
        this.ensureAudioElement().srcObject = event.streams[0] ?? new MediaStream([event.track])
      }
      pc.onconnectionstatechange = () => {
        if (this.pc !== pc) return
        const state = pc.connectionState
        if (state === 'connected') {
          this.retryDelay = RETRY_MIN_MS
          this.linkUp = true
          this.notify()
        } else if (state === 'failed' || state === 'disconnected') {
          this.scheduleReconnect()
        }
      }

      await pc.setLocalDescription(await pc.createOffer())
      await waitForGathering(pc)
      if (generation !== this.generation) return
      const local = pc.localDescription
      if (local === null) throw new Error('Sin descripción local')

      const reply = await window.api.voice.offer({
        sdp: local.sdp,
        type: 'offer',
        ...(this.pcId !== null ? { pc_id: this.pcId, restart_pc: true } : {})
      })
      if (generation !== this.generation) return
      if (!reply.ok) {
        // Sin `pc_id` la voz siempre acepta la oferta (sustituye la conexión): tras un rechazo
        // (p. ej. 409 invalid_request o 503 porque la voz se reinició) se reoferta sin él.
        this.pcId = null
        throw new Error(`Oferta rechazada (${reply.status} ${reply.code})`)
      }
      this.pcId = reply.data.pc_id
      await pc.setRemoteDescription({ type: 'answer', sdp: reply.data.sdp })
    } catch (error) {
      if (generation !== this.generation) return
      console.warn('No se pudo conectar la voz; se reintentará.', error)
      this.scheduleReconnect()
    }
  }
}

export const voiceClient: VoiceClient = new WebRtcVoiceClient()
registerVoiceClient(voiceClient)
