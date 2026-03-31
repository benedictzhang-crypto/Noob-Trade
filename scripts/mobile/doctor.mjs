import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { spawnSync } from 'node:child_process'

const projectRoot = resolve(process.cwd())
const frontendDir = resolve(projectRoot, 'frontend')
const frontendPackage = resolve(frontendDir, 'package.json')
const xcodeProject = resolve(projectRoot, 'ios', 'App', 'App.xcodeproj')

const checks = [
  {
    name: 'frontend package',
    ok: existsSync(frontendPackage),
    detail: frontendPackage,
  },
  {
    name: 'npm',
    ok: commandExists('npm'),
    detail: 'npm must be installed to build the Vue app.',
  },
  {
    name: 'xcodebuild',
    ok: commandExists('xcodebuild'),
    detail: 'Xcode is required to archive and submit the iOS app.',
  },
  {
    name: 'cocoapods',
    ok: commandExists('pod'),
    detail: 'Install CocoaPods before running capacitor sync/open.',
  },
  {
    name: 'ios project',
    ok: existsSync(xcodeProject),
    detail: existsSync(xcodeProject)
      ? 'iOS shell already exists.'
      : 'Run `npm run mobile:sync:ios` after installing dependencies to generate it.',
  },
]

let hasFailure = false

for (const check of checks) {
  const prefix = check.ok ? 'OK' : 'MISSING'
  console.log(`${prefix}: ${check.name} — ${check.detail}`)
  if (!check.ok) {
    hasFailure = true
  }
}

if (hasFailure) {
  process.exit(1)
}

function commandExists(command) {
  const result = spawnSync('which', [command], {
    stdio: 'ignore',
  })

  return result.status === 0
}
