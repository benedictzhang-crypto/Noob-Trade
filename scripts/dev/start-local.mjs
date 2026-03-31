import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import net from 'node:net'

const projectRoot = '/Users/benedict/Desktop/NoobTrade'
const backendDir = path.join(projectRoot, 'backend')
const frontendDir = path.join(projectRoot, 'frontend')
const runtimeDir = path.join(projectRoot, '.runtime', 'local-dev')
const backendCandidates = [5010, 5011, 5012, 5013]
const frontendCandidates = [4173, 4174, 4175, 4176]
const backendPython = path.join(backendDir, '.venv', 'bin', 'python')

fs.mkdirSync(runtimeDir, { recursive: true })

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function isPortOpen(port, host = '127.0.0.1') {
  return new Promise((resolve) => {
    const socket = new net.Socket()
    let settled = false

    const finish = (value) => {
      if (settled) {
        return
      }
      settled = true
      socket.destroy()
      resolve(value)
    }

    socket.setTimeout(400)
    socket.once('connect', () => finish(true))
    socket.once('timeout', () => finish(false))
    socket.once('error', () => finish(false))
    socket.connect(port, host)
  })
}

async function fetchJson(url, options = {}) {
  try {
    const response = await fetch(url, options)
    const contentType = response.headers.get('content-type') || ''
    if (!contentType.includes('application/json')) {
      return { ok: false, status: response.status, contentType }
    }

    const json = await response.json()
    return { ok: response.ok, status: response.status, json, contentType }
  } catch {
    return { ok: false, status: 0, contentType: '' }
  }
}

async function isHealthyBackendPort(port) {
  const health = await fetchJson(`http://127.0.0.1:${port}/api/health`)
  if (!health.ok || health.json?.status !== 'ok') {
    return false
  }

  const csrf = await fetchJson(`http://127.0.0.1:${port}/api/auth/csrf-token`)
  return csrf.ok && typeof csrf.json?.csrfToken === 'string' && csrf.json.csrfToken.length > 0
}

async function isHealthyFrontendPort(port) {
  const health = await fetchJson(`http://127.0.0.1:${port}/api/health`)
  if (!health.ok || health.json?.status !== 'ok') {
    return false
  }

  const csrf = await fetchJson(`http://127.0.0.1:${port}/api/auth/csrf-token`)
  return csrf.ok && typeof csrf.json?.csrfToken === 'string' && csrf.json.csrfToken.length > 0
}

async function findHealthyFrontend() {
  for (const port of frontendCandidates) {
    if (await isHealthyFrontendPort(port)) {
      return port
    }
  }

  return null
}

async function findHealthyBackend() {
  for (const port of backendCandidates) {
    if (await isHealthyBackendPort(port)) {
      return port
    }
  }

  return null
}

async function findFreePort(candidates) {
  for (const port of candidates) {
    if (!(await isPortOpen(port))) {
      return port
    }
  }

  throw new Error(`No free ports found in candidates: ${candidates.join(', ')}`)
}

function pipeLogs(child, logPath, label) {
  const stream = fs.createWriteStream(logPath, { flags: 'a' })
  stream.write(`\n[${new Date().toISOString()}] ${label} started\n`)
  child.stdout.on('data', (chunk) => stream.write(chunk))
  child.stderr.on('data', (chunk) => stream.write(chunk))
  child.on('exit', (code, signal) => {
    stream.write(`\n[${new Date().toISOString()}] ${label} exited code=${code} signal=${signal}\n`)
    stream.end()
  })
}

async function waitFor(checkFn, timeoutMs) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    if (await checkFn()) {
      return true
    }
    await wait(500)
  }
  return false
}

function spawnBackend(port, frontendPort) {
  const child = spawn(backendPython, ['app.py'], {
    cwd: backendDir,
    env: {
      ...process.env,
      PORT: String(port),
      HOST: '127.0.0.1',
      FLASK_USE_RELOADER: 'false',
      APP_BASE_URL: `http://127.0.0.1:${frontendPort}`,
      CORS_ORIGINS: `http://127.0.0.1:${frontendPort},http://localhost:${frontendPort}`,
      SESSION_COOKIE_SECURE: 'false'
    },
    stdio: ['ignore', 'pipe', 'pipe']
  })

  pipeLogs(child, path.join(runtimeDir, 'backend.log'), 'backend')
  return child
}

function spawnFrontend(frontendPort, backendPort) {
  const child = spawn('npm', ['run', 'dev'], {
    cwd: frontendDir,
    env: {
      ...process.env,
      VITE_API_PROXY_TARGET: `http://127.0.0.1:${backendPort}`,
      VITE_DEV_HOST: '127.0.0.1',
      VITE_DEV_PORT: String(frontendPort)
    },
    stdio: ['ignore', 'pipe', 'pipe']
  })

  pipeLogs(child, path.join(runtimeDir, 'frontend.log'), 'frontend')
  return child
}

function openBrowser(url) {
  const child = spawn('open', [url], {
    detached: true,
    stdio: 'ignore'
  })
  child.unref()
}

let backendChild = null
let frontendChild = null

function shutdown(code = 0) {
  for (const child of [frontendChild, backendChild]) {
    if (child && !child.killed) {
      child.kill('SIGTERM')
    }
  }
  process.exit(code)
}

process.on('SIGINT', () => shutdown(0))
process.on('SIGTERM', () => shutdown(0))

async function main() {
  const existingFrontendPort = await findHealthyFrontend()
  if (existingFrontendPort) {
    const url = `http://127.0.0.1:${existingFrontendPort}`
    console.log(`NoobTrade is already running at ${url}`)
    openBrowser(url)
    return
  }

  const frontendPort = await findFreePort(frontendCandidates)
  const backendPort = (await findHealthyBackend()) || (await findFreePort(backendCandidates))

  if (!(await findHealthyBackend())) {
    backendChild = spawnBackend(backendPort, frontendPort)
    const backendReady = await waitFor(() => isHealthyBackendPort(backendPort), 30000)
    if (!backendReady) {
      throw new Error(`Backend did not become healthy on port ${backendPort}. See ${path.join(runtimeDir, 'backend.log')}`)
    }
  }

  frontendChild = spawnFrontend(frontendPort, backendPort)
  const frontendReady = await waitFor(() => isHealthyFrontendPort(frontendPort), 30000)
  if (!frontendReady) {
    throw new Error(`Frontend proxy did not become healthy on port ${frontendPort}. See ${path.join(runtimeDir, 'frontend.log')}`)
  }

  const appUrl = `http://127.0.0.1:${frontendPort}`
  console.log(`NoobTrade frontend: ${appUrl}`)
  console.log(`NoobTrade backend: http://127.0.0.1:${backendPort}`)
  console.log(`Logs: ${runtimeDir}`)
  openBrowser(appUrl)

  if (frontendChild) {
    frontendChild.on('exit', (code) => shutdown(code ?? 0))
  }
  if (backendChild) {
    backendChild.on('exit', (code) => shutdown(code ?? 0))
  }
}

main().catch((error) => {
  console.error(error.message || error)
  shutdown(1)
})
