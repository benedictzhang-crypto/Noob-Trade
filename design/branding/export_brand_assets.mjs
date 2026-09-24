import { createRequire } from 'node:module'
import { mkdir, readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(fileURLToPath(import.meta.url))
const require = createRequire(resolve(root, '../../frontend/package.json'))
const { chromium } = require('playwright')
const exportsDirectory = resolve(root, 'exports')
const assets = [
  {
    source: 'noobtrade-app-icon',
    output: 'noobtrade-app-icon',
    width: 1024,
    height: 1024,
    background: 'transparent',
  },
]

await mkdir(exportsDirectory, { recursive: true })

const browser = await chromium.launch({ headless: true })
try {
  for (const asset of assets) {
    const svg = await readFile(resolve(exportsDirectory, `${asset.source}.svg`), 'utf8')
    const page = await browser.newPage({
      viewport: { width: asset.width, height: asset.height },
      deviceScaleFactor: 1,
    })
    await page.setContent(`<!doctype html><html><body>${svg}</body></html>`)
    await page.addStyleTag({
      content: `html, body { margin: 0; width: 100%; height: 100%; overflow: hidden; background: ${asset.background}; } svg { display: block; width: 100%; height: 100%; }`,
    })
    await page.screenshot({
      path: resolve(exportsDirectory, `${asset.output}.png`),
      omitBackground: asset.background === 'transparent',
    })
    await page.close()
  }
} finally {
  await browser.close()
}

await import('./extract_concept_wordmarks.mjs')
