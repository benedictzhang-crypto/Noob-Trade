import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { spawnSync } from 'node:child_process'

const projectRoot = resolve(process.cwd())
const iosProjectPath = resolve(projectRoot, 'ios', 'App', 'App.xcodeproj')

if (existsSync(iosProjectPath)) {
  console.log('iOS shell already exists.')
  process.exit(0)
}

console.log('Creating Capacitor iOS shell...')

const result = spawnSync('npx', ['cap', 'add', 'ios'], {
  cwd: projectRoot,
  stdio: 'inherit',
  shell: process.platform === 'win32',
})

if (result.status !== 0) {
  process.exit(result.status ?? 1)
}
