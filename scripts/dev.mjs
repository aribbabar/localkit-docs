import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const rootDir = dirname(dirname(fileURLToPath(import.meta.url)))
const backendDir = join(rootDir, 'backend')
const frontendDir = join(rootDir, 'frontend')

const args = new Set(process.argv.slice(2))
const skipInstall = args.has('--skip-install') || process.env.LOCALKIT_SKIP_INSTALL === '1'
const backendPort = Number(process.env.LOCALKIT_BACKEND_PORT ?? 8000)
const frontendPort = Number(process.env.LOCALKIT_FRONTEND_PORT ?? 5173)
const host = process.env.LOCALKIT_HOST ?? '127.0.0.1'
const healthUrl = `http://${host}:${backendPort}/health`

const children = new Set()
let shuttingDown = false

function log(message) {
  process.stdout.write(`${message}\n`)
}

function run(command, commandArgs, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, commandArgs, {
      cwd: options.cwd ?? rootDir,
      env: { ...process.env, ...options.env },
      shell: process.platform === 'win32',
      stdio: 'inherit',
    })

    child.on('error', reject)
    child.on('exit', (code) => {
      if (code === 0) {
        resolve()
      } else {
        reject(new Error(`${command} ${commandArgs.join(' ')} exited with code ${code}`))
      }
    })
  })
}

function start(name, command, commandArgs, options = {}) {
  const child = spawn(command, commandArgs, {
    cwd: options.cwd ?? rootDir,
    env: { ...process.env, ...options.env },
    shell: process.platform === 'win32',
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  children.add(child)

  child.stdout.on('data', (data) => prefixOutput(name, data, process.stdout))
  child.stderr.on('data', (data) => prefixOutput(name, data, process.stderr))
  child.on('exit', (code) => {
    children.delete(child)
    if (!shuttingDown) {
      shutdown(code === 0 ? 0 : 1)
    }
  })

  return child
}

function prefixOutput(name, data, stream) {
  for (const line of data.toString().split(/\r?\n/)) {
    if (line.trim().length > 0) {
      stream.write(`[${name}] ${line}\n`)
    }
  }
}

async function waitForBackend(timeoutMs = 45000) {
  const deadline = Date.now() + timeoutMs

  while (Date.now() < deadline) {
    try {
      const response = await fetch(healthUrl)
      if (response.ok) return
    } catch {
      // Keep polling until the backend is ready or the startup deadline passes.
    }

    await new Promise((resolve) => setTimeout(resolve, 500))
  }

  throw new Error(`Backend did not become ready at ${healthUrl}`)
}

function stopChild(child) {
  if (!child.pid || child.killed) return

  if (process.platform === 'win32') {
    spawn('taskkill', ['/pid', String(child.pid), '/t', '/f'], {
      stdio: 'ignore',
      shell: true,
    })
    return
  }

  child.kill('SIGTERM')
}

function shutdown(code = 0) {
  if (shuttingDown) return
  shuttingDown = true

  for (const child of children) {
    stopChild(child)
  }

  setTimeout(() => process.exit(code), 200)
}

process.on('SIGINT', () => shutdown(0))
process.on('SIGTERM', () => shutdown(0))

try {
  if (!skipInstall) {
    log('[setup] Syncing backend dependencies')
    await run('uv', ['sync'], { cwd: backendDir })

    if (!existsSync(join(frontendDir, 'node_modules'))) {
      log('[setup] Installing frontend dependencies')
      await run('npm', ['install'], { cwd: frontendDir })
    }
  }

  log(`[backend] http://${host}:${backendPort}`)
  const backend = start('backend', 'uv', ['run', 'localkit', 'serve', '--host', host, '--port', String(backendPort)], {
    cwd: backendDir,
  })

  await waitForBackend()
  log('[backend] ready')

  log(`[frontend] http://${host}:${frontendPort}`)
  start('frontend', 'npm', ['run', 'dev', '--', '--host', host, '--port', String(frontendPort), '--strictPort'], {
    cwd: frontendDir,
    env: {
      VITE_LOCALKIT_API_URL: `http://${host}:${backendPort}`,
    },
  })

  backend.on('error', (error) => {
    process.stderr.write(`[backend] ${error.message}\n`)
    shutdown(1)
  })
} catch (error) {
  process.stderr.write(`[dev] ${error.message}\n`)
  shutdown(1)
}
