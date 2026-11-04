import { spawn, type ChildProcess } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { existsSync } from 'node:fs'
import { request } from 'node:http'
import { homedir } from 'node:os'
import { join, resolve } from 'node:path'
import { app } from 'electron'
import type { BackendConnection, BackendState } from '../shared/bridge'
import { describeError, logError } from './log'
import type { BackendEndpoint, BackendHost } from './host-types'

// Holgado: la línea de puerto sale tras migrar, y matar una migración en curso sería peor que esperar.
const HANDSHAKE_TIMEOUT_MS = 120_000
const MAX_LINE = 4096
const MAX_STDERR_LINE = 2000
const HEALTH_WINDOW_MS = 5000
const FAIL_WINDOW_MS = 60_000
const MAX_FAILURES = 3
const STOP_GRACE_MS = 5000
const STOP_TERM_MS = 2000
const ENV_ALLOWLIST = [
  'PATH', 'HOME', 'USER', 'LANG', 'LC_ALL', 'TZ',
  'XDG_DATA_HOME', 'XDG_CONFIG_HOME', 'XDG_RUNTIME_DIR', 'DRAKTER_DATA_DIR'
] as const

/** Un intento de arranque. Cada manejador compara con `current` para ignorar procesos viejos. */
interface Attempt {
  readonly child: ChildProcess
  readonly ui: string
  readonly approver: string
  readonly exited: Promise<void>
  markExited: () => void
  hasExited: boolean
  dead: boolean
  handshakeTimer: NodeJS.Timeout | null
  stdoutBuf: string
  gotPort: boolean
}

interface Command {
  readonly file: string
  readonly args: string[]
  readonly cwd: string
}

function resolveCommand(): Command {
  if (app.isPackaged) {
    // Ruta provisional: la fija P10 (empaquetado).
    const dataDir = process.env.DRAKTER_DATA_DIR ?? join(homedir(), '.local', 'share', 'drakter')
    const cwd = join(dataDir, 'runtime', 'backend')
    return { file: join(cwd, '.venv', 'bin', 'python'), args: ['-m', 'app'], cwd }
  }
  const cwd = resolve(app.getAppPath(), '../backend')
  const venvPython = join(cwd, '.venv', 'bin', 'python')
  if (existsSync(venvPython)) return { file: venvPython, args: ['-m', 'app'], cwd }
  return { file: process.env.DRAKTER_UV ?? 'uv', args: ['run', '--frozen', 'python', '-m', 'app'], cwd }
}

function buildEnv(): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = {}
  for (const key of ENV_ALLOWLIST) {
    const value = process.env[key]
    if (value !== undefined) env[key] = value
  }
  env.PYTHONUNBUFFERED = '1'
  return env
}

function parsePort(line: string): number | null {
  try {
    const data: unknown = JSON.parse(line)
    if (typeof data !== 'object' || data === null) return null
    const { v, port } = data as { v?: unknown; port?: unknown }
    if (v !== 1 || typeof port !== 'number') return null
    if (!Number.isInteger(port) || port < 1024 || port > 65535) return null
    return port
  } catch {
    return null
  }
}

function healthOnce(port: number, ui: string): Promise<boolean> {
  return new Promise((done) => {
    const req = request(
      { host: '127.0.0.1', port, path: '/health', method: 'GET', headers: { Authorization: `Bearer ${ui}` }, timeout: 1000 },
      (res) => {
        res.resume()
        done(res.statusCode === 200)
      }
    )
    req.on('timeout', () => req.destroy())
    req.on('error', () => done(false))
    req.end()
  })
}

const sleep = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms))

export function createBackendHost(): BackendHost {
  let state: BackendState = 'stopped'
  let current: Attempt | null = null
  let endpoint: BackendEndpoint | null = null
  let stopping = false
  let stopPromise: Promise<void> | null = null
  let retryTimer: NodeJS.Timeout | null = null
  let readySince = 0
  let failures: number[] = []
  const listeners = new Set<(connection: BackendConnection) => void>()

  function setState(next: BackendState): void {
    if (next === state) return
    state = next
    const connection: BackendConnection = { state }
    for (const listener of [...listeners]) {
      try {
        listener(connection)
      } catch (error) {
        logError('backend', 'connection listener failed', describeError(error))
      }
    }
  }

  function killNow(att: Attempt): void {
    if (att.hasExited) return
    try {
      att.child.kill('SIGKILL')
    } catch {
      /* ya ha salido */
    }
  }

  function fail(att: Attempt, reason: string): void {
    if (att !== current || att.dead) return
    att.dead = true
    if (att.handshakeTimer) clearTimeout(att.handshakeTimer)
    att.handshakeTimer = null
    endpoint = null
    killNow(att)
    if (stopping) return
    logError('backend', `backend attempt failed: ${reason}`)

    const now = Date.now()
    if (readySince && now - readySince > FAIL_WINDOW_MS) failures = []
    readySince = 0
    failures = failures.filter((t) => now - t < FAIL_WINDOW_MS)
    failures.push(now)
    if (failures.length > MAX_FAILURES) {
      setState('failed')
      return
    }
    setState('restarting')
    const delay = 1000 * 2 ** (failures.length - 1)
    retryTimer = setTimeout(() => {
      retryTimer = null
      launch()
    }, delay)
  }

  async function checkHealth(att: Attempt, port: number): Promise<void> {
    const deadline = Date.now() + HEALTH_WINDOW_MS
    while (att === current && !att.dead) {
      if (await healthOnce(port, att.ui)) break
      if (Date.now() >= deadline) {
        fail(att, 'health check timed out')
        return
      }
      await sleep(200)
    }
    if (att !== current || att.dead) return
    if (att.handshakeTimer) clearTimeout(att.handshakeTimer)
    att.handshakeTimer = null
    endpoint = { port, uiToken: att.ui, approverToken: att.approver }
    readySince = Date.now()
    setState('ready')
  }

  function onStdout(att: Attempt, chunk: string): void {
    if (att !== current || att.dead || att.gotPort) return // después del handshake se drena y se ignora
    att.stdoutBuf += chunk
    const nl = att.stdoutBuf.indexOf('\n')
    if (nl === -1) {
      if (att.stdoutBuf.length > MAX_LINE) fail(att, 'handshake line too long')
      return
    }
    const line = att.stdoutBuf.slice(0, nl).replace(/\r$/, '')
    att.stdoutBuf = ''
    att.gotPort = true
    const port = line.length > MAX_LINE ? null : parsePort(line)
    if (port === null) {
      fail(att, 'invalid handshake line')
      return
    }
    void checkHealth(att, port).catch((error) => fail(att, describeError(error)))
  }

  function launch(): void {
    const cmd = resolveCommand()
    const ui = randomBytes(32).toString('base64url')
    const approver = randomBytes(32).toString('base64url')

    let child: ChildProcess
    try {
      child = spawn(cmd.file, cmd.args, {
        cwd: cmd.cwd,
        env: buildEnv(),
        stdio: ['pipe', 'pipe', 'pipe'],
        shell: false,
        windowsHide: true
      })
    } catch (error) {
      // spawn síncrono fallido: se trata como un intento más
      let markExited = (): void => {}
      const exited = new Promise<void>((r) => (markExited = r))
      const stub = { child: null as unknown as ChildProcess, ui, approver, exited, markExited, hasExited: true, dead: false, handshakeTimer: null, stdoutBuf: '', gotPort: false } satisfies Attempt
      markExited()
      current = stub
      fail(stub, describeError(error))
      return
    }

    let markExited = (): void => {}
    const exited = new Promise<void>((r) => (markExited = r))
    const att: Attempt = { child, ui, approver, exited, markExited, hasExited: false, dead: false, handshakeTimer: null, stdoutBuf: '', gotPort: false }
    current = att
    endpoint = null
    const finish = (): void => {
      att.hasExited = true
      att.markExited()
    }

    att.handshakeTimer = setTimeout(() => fail(att, 'handshake timed out'), HANDSHAKE_TIMEOUT_MS)

    child.on('error', (error) => {
      if (child.pid === undefined) finish() // no llegó a arrancar: no habrá 'exit'
      fail(att, describeError(error))
    })
    child.on('exit', (code, signal) => {
      finish()
      fail(att, `unexpected exit (code=${code}, signal=${signal})`)
    })

    child.stdin?.on('error', (error) => logError('backend', 'stdin error', describeError(error)))
    child.stdin?.write(`${JSON.stringify({ v: 1, ui, approver })}\n`)

    child.stdout?.setEncoding('utf8')
    child.stdout?.on('data', (chunk: string) => onStdout(att, chunk))
    child.stdout?.on('error', () => {})

    let errBuf = ''
    child.stderr?.setEncoding('utf8')
    child.stderr?.on('data', (chunk: string) => {
      errBuf += chunk
      let nl = errBuf.indexOf('\n')
      while (nl !== -1) {
        const line = errBuf.slice(0, nl).replace(/\r$/, '')
        errBuf = errBuf.slice(nl + 1)
        if (line) logError('backend', line.slice(0, MAX_STDERR_LINE))
        nl = errBuf.indexOf('\n')
      }
      if (errBuf.length > MAX_STDERR_LINE) {
        logError('backend', errBuf.slice(0, MAX_STDERR_LINE))
        errBuf = ''
      }
    })
    child.stderr?.on('error', () => {})
  }

  // Último recurso: no dejar un backend huérfano si main muere.
  process.once('exit', () => {
    if (current && !current.hasExited) {
      try {
        current.child.kill('SIGKILL')
      } catch {
        /* nada más que hacer */
      }
    }
  })

  return {
    start(): void {
      if (state !== 'stopped' && state !== 'failed') return
      if (stopPromise && !current?.hasExited) return // una parada sigue en curso
      stopping = false
      stopPromise = null
      failures = []
      readySince = 0
      setState('starting')
      launch()
    },

    stop(): Promise<void> {
      if (stopPromise) return stopPromise
      stopping = true
      if (retryTimer) clearTimeout(retryTimer)
      retryTimer = null
      endpoint = null
      setState('stopped')
      const att = current
      if (!att || att.hasExited) {
        stopPromise = Promise.resolve()
        return stopPromise
      }
      att.dead = true
      if (att.handshakeTimer) clearTimeout(att.handshakeTimer)
      att.handshakeTimer = null
      stopPromise = new Promise<void>((done) => {
        let termTimer: NodeJS.Timeout | null = null
        const graceTimer = setTimeout(() => {
          try {
            att.child.kill('SIGTERM')
          } catch {
            /* ya ha salido */
          }
          termTimer = setTimeout(() => killNow(att), STOP_TERM_MS)
        }, STOP_GRACE_MS)
        void att.exited.then(() => {
          clearTimeout(graceTimer)
          if (termTimer) clearTimeout(termTimer)
          done()
        })
        try {
          att.child.stdin?.end()
        } catch {
          /* EPIPE: el proceso ya cerraba */
        }
      })
      return stopPromise
    },

    getConnection(): BackendConnection {
      return { state }
    },

    onConnection(listener): () => void {
      listeners.add(listener)
      return () => {
        listeners.delete(listener)
      }
    },

    getEndpoint(): BackendEndpoint | null {
      return state === 'ready' ? endpoint : null
    },

    waitUntilReady(timeoutMs: number): Promise<BackendEndpoint | null> {
      if (state === 'ready') return Promise.resolve(endpoint)
      if (state === 'failed') return Promise.resolve(null)
      return new Promise((resolveWait) => {
        let timer: NodeJS.Timeout | null = null
        let off: () => void = () => {}
        const settle = (value: BackendEndpoint | null): void => {
          if (timer) clearTimeout(timer)
          off()
          resolveWait(value)
        }
        const onChange = ({ state: s }: BackendConnection): void => {
          if (s === 'ready') settle(endpoint)
          else if (s === 'failed' || s === 'stopped') settle(null)
        }
        listeners.add(onChange)
        off = () => listeners.delete(onChange)
        timer = setTimeout(() => settle(null), timeoutMs)
      })
    }
  }
}
